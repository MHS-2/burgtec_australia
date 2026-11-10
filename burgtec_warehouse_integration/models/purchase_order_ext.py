from odoo import models, fields, api, _
from markupsafe import Markup
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrderExt(models.Model):
    _inherit = "purchase.order"

    warehouse_sale_order_id = fields.Integer(string="WH Quotation ID", readonly=True, copy=False)
    warehouse_sale_order_name = fields.Char(string="WH Quotation", readonly=True, copy=False)
    warehouse_sale_order_url = fields.Char(string="WH Quotation URL", readonly=True, copy=False)

# ============This section contains the code that update the dispatch date and arrival date on warehouse Quotation Upon Child Po fields changes=====

    @api.model
    def _get_burgtec_warehouse_config_parameter(self):
        params = self.env["ir.config_parameter"].sudo()
        url = params.get_param("burgtec_warehouse_integration.burgtec_warehouse_url")
        db = params.get_param("burgtec_warehouse_integration.burgtec_warehouse_db")
        api_key = params.get_param("burgtec_warehouse_integration.burgtec_warehouse_api_key")
        webhook_auth_token = params.get_param("burgtec_warehouse_integration.burgtec_webhook_authentication_token")
        if not url or not api_key or not db or not webhook_auth_token:
            raise UserError(_("Please set the Warehouse URL and API Key and Database name in Sales settings."))
        return url.rstrip("/"), db, api_key, webhook_auth_token

    def _write_multi(self, vals_list):
        res = super()._write_multi(vals_list)
        for po, vals in zip(self, vals_list):
            if po.warehouse_sale_order_id and ('hubspot_dispatch_date' in vals or 'date_planned' in vals):
                po._call_warehouse_controller_to_update_date_from_po_to_so(po.warehouse_sale_order_id)
        return res

    def _call_warehouse_controller_to_update_date_from_po_to_so(self, warehouse_quotation_id):
        self.ensure_one()
        try:
            url, db, api_token, webhook_auth_token = self._get_burgtec_warehouse_config_parameter()
            response = requests.post(
                f"{url}/warehouse/update_quotation_date",
                params={'webhook_auth_token': webhook_auth_token, 'db': db},
                json={
                    'sale_order_id': warehouse_quotation_id,
                    'hubspot_dispatch_date': fields.Datetime.to_string(self.hubspot_dispatch_date),
                    'date_planned': fields.Datetime.to_string(self.date_planned),
                },
                timeout=30,
            )
            response.raise_for_status()
        except Exception as e:
            _logger.warning("Burgtec sync failed for %s: %s", warehouse_quotation_id, e)

    def action_open_warehouse_instance_quotation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.warehouse_sale_order_url,
            'target': 'new',
        }

# ==============This Section have the code to create a warehouse quotation from child po button in burgtec instance=============

    def create_quotation_in_warehouse_instance(self):
        self.ensure_one()
        po_lines = self.order_line
        if not po_lines:
            raise UserError(_("This purchase order has no products."))
        self._check_products_in_warehouse(po_lines)
        warehouse_products = self._get_warehouse_products(po_lines)
        sale_order_id = self._create_warehouse_quotation(po_lines, warehouse_products)
        sale_order_name = self._save_warehouse_quotation(sale_order_id)
        return {
            "effect": {
                "fadeout": "slow",
                "message": _("Quotation %s Successfully Created in Warehouse!", sale_order_name),
                "type": "rainbow_man",
            }
        }

    def _check_products_in_warehouse(self, po_lines):
        missing_products = []
        for line in po_lines:
            if not line.is_present_in_warehouse:
                missing_products.append(line.product_id.display_name)
        if missing_products:
            raise UserError(_(
                "These products are not available in Warehouse:\n\n%s",
                "\n".join(missing_products),
            ))

    def _get_warehouse_products(self, po_lines):
        codes = []
        for line in po_lines:
            codes.append(line.product_id.default_code)

        products = self.env["product.product"]._burgtec_warehouse_instance_api_call("product.product", "search_read", {
            "domain": [["default_code", "in", codes], ["custom_variant_type", "=", "product"]],
            "fields": ["id", "default_code", "product_tmpl_id"],
        })

        warehouse_products = {}
        for product in products:
            code = product["default_code"].strip().lower()
            warehouse_products[code] = {
                "id": product["id"],
                "template_id": product["product_tmpl_id"][0],
            }
        return warehouse_products

    def _get_warehouse_bom_id(self, warehouse_product, product_name):
        boms = self.env["product.product"]._burgtec_warehouse_instance_api_call("mrp.bom", "search_read", {
            "domain": [
                "|",
                ["product_id", "=", warehouse_product["id"]],
                "&", ["product_id", "=", False], ["product_tmpl_id", "=", warehouse_product["template_id"]],
            ],
            "fields": ["id"],
            "order": "sequence, id",
            "limit": 1,
        })
        if not boms:
            raise UserError(_("Product %s does not have a BoM in Warehouse.", product_name))
        return boms[0]["id"]

    def _get_warehouse_partner_id(self):
        # need to work on this for now putting static name
        partners = self.env["product.product"]._burgtec_warehouse_instance_api_call("res.partner", "search_read", {
            "domain": [["name", "=", 'Burgtec Prod - C Job']],
            "fields": ["id"],
            "limit": 1,
        })
        if not partners:
            raise UserError(_("Customer '%s' not found in Warehouse.", self.company_id.name))
        return partners[0]["id"]

    def _create_warehouse_quotation(self, po_lines, warehouse_products):
        Product = self.env["product.product"]
        base_url = self.get_base_url()
        sale_order_ids = Product._burgtec_warehouse_instance_api_call("sale.order", "create", {
            "vals_list": [{
                "partner_id": self._get_warehouse_partner_id(),
                "customer_po_reference": self.burgtec_purchase_reference,
                "purchase_order_value": sum(po_lines.mapped("price_subtotal")),
                "is_created_from_child_po": True,
                "burgtec_po_id": self.id,
                "po_dispatch_date": fields.Datetime.to_string(self.hubspot_dispatch_date),
                "po_date_planned": fields.Datetime.to_string(self.date_planned),
                "burgtec_po_url": "%s/odoo/purchase.order/%s" % (base_url, self.id),
            }],
        })
        sale_order_id = sale_order_ids[0]

        for line in po_lines:
            code = line.product_id.default_code.strip().lower()
            if code not in warehouse_products:
                raise UserError(_(
                    "Product %s was not found in Warehouse. Run the presence check again.",
                    line.product_id.display_name,
                ))
            warehouse_product = warehouse_products[code]
            bom_id = self._get_warehouse_bom_id(warehouse_product, line.product_id.display_name)

            Product._burgtec_warehouse_instance_api_call("sale.order.line", "create", {
                "vals_list": [{
                    "order_id": sale_order_id,
                    "product_id": warehouse_product["id"],
                    "product_uom_qty": line.product_qty,
                    "price_unit": line.price_unit,
                    "kit_bom_id": bom_id,
                    "line_group_name": line.line_group_name_child,
                    "line_section_name": line.line_section_name_child,
                    "notes": line.note,
                }],
            })

        self._post_warehouse_chatter_message(sale_order_id)
        return sale_order_id

    def _post_warehouse_chatter_message(self, sale_order_id):
        body = Markup(
            "Quotation created from Child PO %s through API.") % self.burgtec_purchase_reference

        self.env["product.product"]._burgtec_warehouse_instance_api_call("sale.order", "message_post", {
            "ids": [sale_order_id],
            "body": str(body),
            "message_type": "comment",
            "subtype_xmlid": "mail.mt_note",
        })

    def _save_warehouse_quotation(self, sale_order_id):
        Product = self.env["product.product"]
        sale_orders = Product._burgtec_warehouse_instance_api_call("sale.order", "read", {
            "ids": [sale_order_id],
            "fields": ["name"],
        })
        sale_order_name = sale_orders[0]["name"]
        warehouse_url, db, api_key = Product._get_burgtec_warehouse_config_parameter()

        self.write({
            "warehouse_sale_order_id": sale_order_id,
            "warehouse_sale_order_name": sale_order_name,
            "warehouse_sale_order_url": "%s/odoo/sale.order/%s" % (warehouse_url, sale_order_id),
        })
        self.message_post(body=Markup("<b>Quotation %s created in Burgtec Warehouse Instance.</b>") % sale_order_name)
        return sale_order_name


class PurchaseOrderLineExt(models.Model):
    _inherit = "purchase.order.line"

    is_present_in_warehouse = fields.Boolean(related="product_id.is_present_in_warehouse", store=True)
    is_delivery_and_installation = fields.Boolean(related="product_id.is_delivery_and_installation", store=True)
    warehouse_status_html = fields.Html(
        string="WH",
        default='<i class="fa fa-flag fa-lg text-danger"></i>',
        sanitize=False,
        readonly=True,
    )
    warehouse_bom_id = fields.Many2one('warehouse.bom.data', ondelete='set null', string="Warehouse Bom ID")


    def create_product_in_warehouse_instance(self):
        """
        This method will Create a product of in Warehouse Instance from the child purchase order line button.
        """
        self.ensure_one()
        warehouse_url, db, api_token, webhook_auth_token = self.order_id._get_burgtec_warehouse_config_parameter()
        params = self.env['ir.config_parameter'].sudo()
        web_url = params.get_param('web.base.url')
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}",
        }
        if db:
            headers["X-Odoo-Database"] = db
        payload = {
            "vals_list": [{
                "name": self.product_id.name,
                "default_code": self.product_id.default_code,
                "type": "consu",
                "custom_product_type": "product",
            }],
            # added this context because on creation.create product method in warehouse call the controller /warehouse/product_sync and goes into infinite loop
            "context": {"created_from_api": True},
        }
        try:
            response = requests.post(
                warehouse_url + "/json/2/product.template/create",
                json=payload,
                headers=headers,
                timeout=60,
            )
            if response.ok:
                tmpl_id = response.json()[0]
                response = requests.post(
                    warehouse_url + "/json/2/product.template/read",
                    json={"ids": [tmpl_id], "fields": ["product_variant_id"]},
                    headers=headers,
                    timeout=60,
                )
            if response.ok:
                product_id = response.json()[0]["product_variant_id"][0]
                response = requests.post(
                    warehouse_url + "/json/2/product.product/write",
                    json={
                        "ids": [product_id],
                        "vals": {
                            "burgtec_product_id": self.product_id.id,
                            "burgtec_product_url": f"{web_url}/odoo/product.product/{self.product_id.id}",
                        },
                        "context": {"created_from_api": True},
                    },
                    headers=headers,
                    timeout=60,
                )
        except requests.exceptions.RequestException as e:
            raise UserError(_("Could not connect to Warehouse: %s", e)) from e

        if not response.ok:
            _logger.error("Warehouse API error (%s): %s", response.status_code, response.text)
            raise UserError(_("Warehouse API error: %s", response.text[:500]))

        self.product_id.sudo().write({
            "warehouse_product_id": product_id,
            "is_present_in_warehouse": True,
            "warehouse_product_url": f"{warehouse_url}/odoo/product.product/{product_id}",
        })
        return {
            "effect": {
                "fadeout": "slow",
                "message": _(
                    "Warehouse product created: variant=%s, default_code=%s",
                    self.product_id.name, self.product_id.default_code,
                ),
                "type": "rainbow_man",
            }
        }