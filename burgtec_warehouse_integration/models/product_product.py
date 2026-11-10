import logging
import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductTemplateExt(models.Model):
    _inherit = "product.template"

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ProductTemplateExt, self.with_context(after_create=True)).create(vals_list)
        return records

class ProductProductExt(models.Model):
    _inherit = "product.product"

    is_present_in_warehouse = fields.Boolean(string="Present in Burgtec Warehouse Instance", readonly=True, copy=False)

    warehouse_product_id = fields.Integer(string="Warehouse Variant ID", copy=False, readonly=True)
    warehouse_product_url = fields.Char(string="Warehouse Variant Link", copy=False, readonly=True)
    warehouse_bom_line_ids = fields.One2many(
        "warehouse.bom.data", "product_id", string="Warehouse BoMs", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ProductProductExt, self.with_context(after_variant_create=True)).create(vals_list)
        for rec in records:
            if (rec.default_code and rec.variant_bom_type == 'components'):
                rec.create_product_in_warehouse_instance()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'default_code' in vals or 'variant_bom_type' in vals:
            if self.env.context.get('after_create'):
                for rec in self:
                    if (rec.default_code and rec.variant_bom_type == 'components'):
                        rec.create_product_in_warehouse_instance()
        return result

    def create_product_in_warehouse_instance(self):
        """
        Create product of in warehouse instance when a product is created in Burgtec Instance
        """
        self.ensure_one()
        warehouse_url, db, api_token = self._get_burgtec_warehouse_config_parameter()
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
                "name": self.name,
                "default_code": self.default_code,
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
                            "burgtec_product_id": self.id,
                            "burgtec_product_url": f"{web_url}/odoo/product.product/{self.id}",
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

        self.sudo().write({
            "warehouse_product_id": product_id,
            "is_present_in_warehouse": True,
            "warehouse_product_url": f"{warehouse_url}/odoo/product.product/{product_id}",
        })
        return {
            "effect": {
                "fadeout": "slow",
                "message": _(
                    "Warehouse product created: variant=%s, default_code=%s",
                    self.name, self.default_code,
                ),
                "type": "rainbow_man",
            }
        }

    def action_open_warehouse_product(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.warehouse_product_url,
            "target": "new",
        }

    @api.model
    def _get_burgtec_warehouse_config_parameter(self):
        params = self.env["ir.config_parameter"].sudo()
        url = params.get_param("burgtec_warehouse_integration.burgtec_warehouse_url")
        db = params.get_param("burgtec_warehouse_integration.burgtec_warehouse_db")
        api_key = params.get_param("burgtec_warehouse_integration.burgtec_warehouse_api_key")

        if not url or not api_key or not db:
            raise UserError(_("Please set the Warehouse URL and API Key and Database name in Sales settings."))

        return url.rstrip("/"), db, api_key
    #
    # @api.model
    # def _cron_mark_all_burgtec_components_available_in_warehouse_as_products(self):
    #     """
    #     This Schedule action mark is_present_in_warehouse check true on Component of Burgtec instance if the
    #     same product is available as a Product in Warehouse Instance.
    #     Matching Criteria : Based on Internal Reference
    #     """
    #     warehouse_codes = self._get_warehouse_instance_product_codes()
    #     components = self.search([
    #         ("default_code", "!=", False),
    #         ("variant_bom_type", "=", "components"),
    #     ])
    #     for component in components:
    #         code = component.default_code.strip().lower()
    #         found = code in warehouse_codes
    #         if component.is_present_in_warehouse != found:
    #             component.is_present_in_warehouse = found
    #
    #     _logger.info("Warehouse check done for %s components", len(components))
    #
    #
    # @api.model
    # def _get_warehouse_instance_product_codes(self):
    #     products = self._burgtec_warehouse_instance_api_call("product.product", "search_read", {
    #         "domain": [["default_code", "!=", False], ["custom_variant_type", "=", "product"]],
    #         "fields": ["default_code"],
    #     })
    #     codes = set()
    #     for product in products:
    #         codes.add(product["default_code"].strip().lower())
    #     return codes
    #
    @api.model
    def _burgtec_warehouse_instance_api_call(self, model, method, data):
        url, db, api_key = self._get_burgtec_warehouse_config_parameter()

        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer " + api_key,
        }
        if db:
            headers["X-Odoo-Database"] = db

        try:
            response = requests.post(
                url + "/json/2/" + model + "/" + method,
                json=data,
                headers=headers,
                timeout=60,
            )
        except requests.exceptions.RequestException as e:
            raise UserError(_("Could not connect to Warehouse: %s", e))

        if response.status_code != 200:
            _logger.error("Warehouse API error: %s", response.text)
            raise UserError(_("Warehouse API error: %s", response.text[:500]))

        return response.json()

    @api.model
    def _cron_mark_all_burgtec_components_available_in_warehouse_as_products(self):
        """
        This Schedule action links Components of Burgtec instance with Products of Warehouse Instance.
        Matching Criteria : Based on Internal Reference
        Burgtec   : is_present_in_warehouse, warehouse_product_id, warehouse_product_url
        Warehouse : burgtec_product_id, burgtec_product_url
        IDs are kept only when product is Component in Burgtec and Product in Warehouse.
        """
        warehouse_url, db, api_key = self._get_burgtec_warehouse_config_parameter()
        web_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        warehouse_products = self._get_warehouse_instance_products()

        components = self.search([
            ("default_code", "!=", False),
            ("variant_bom_type", "=", "components"),
        ])
        linked_codes = []
        linked_warehouse_ids = []
        for component in components:
            code = component.default_code.strip().lower()
            warehouse_product = warehouse_products.get(code)

            # same internal reference on 2 Burgtec components -> link only the first one
            if warehouse_product and code in linked_codes:
                _logger.warning("Duplicate Internal Reference %s on Burgtec, %s not linked", code, component.display_name)
                warehouse_product = False

            if warehouse_product:
                linked_codes.append(code)
                linked_warehouse_ids.append(warehouse_product["id"])
                vals = {
                    "is_present_in_warehouse": True,
                    "warehouse_product_id": warehouse_product["id"],
                    "warehouse_product_url": f"{warehouse_url}/odoo/product.product/{warehouse_product['id']}",
                }
            else:
                vals = {
                    "is_present_in_warehouse": False,
                    "warehouse_product_id": 0,
                    "warehouse_product_url": False,
                }

            # Burgtec side
            if component.warehouse_product_id != vals["warehouse_product_id"] \
                    or component.is_present_in_warehouse != vals["is_present_in_warehouse"]:
                component.write(vals)

            # Warehouse side
            if warehouse_product and warehouse_product["burgtec_product_id"] != component.id:
                self._burgtec_warehouse_instance_api_call("product.product", "write", {
                    "ids": [warehouse_product["id"]],
                    "vals": {
                        "burgtec_product_id": component.id,
                        "burgtec_product_url": f"{web_url}/odoo/product.product/{component.id}",
                    },
                    "context": {"created_from_api": True},
                })

        # Burgtec products that are no longer Components -> remove link
        self.search([("warehouse_product_id", ">", 0), ("id", "not in", components.ids)]).write({
            "is_present_in_warehouse": False,
            "warehouse_product_id": 0,
            "warehouse_product_url": False,
        })

        # Warehouse products that are no longer linked -> remove link
        old_linked_products = self._burgtec_warehouse_instance_api_call("product.product", "search_read", {
            "domain": [["burgtec_product_id", ">", 0]],
            "fields": ["id"],
            "context": {"active_test": False},
        })
        unlink_ids = []
        for product in old_linked_products:
            if product["id"] not in linked_warehouse_ids:
                unlink_ids.append(product["id"])
        if unlink_ids:
            self._burgtec_warehouse_instance_api_call("product.product", "write", {
                "ids": unlink_ids,
                "vals": {"burgtec_product_id": 0, "burgtec_product_url": False},
                "context": {"created_from_api": True},
            })

        # # BoM lines: archive for unlinked products, refresh for linked products
        self.env["warehouse.bom.data"].search([("product_id.warehouse_product_id", "=", 0)]).write({"active": False})
        self.search([("warehouse_product_id", ">", 0)]).action_fetch_warehouse_boms()

        _logger.info("Warehouse link done for %s components, %s linked", len(components), len(linked_codes))

    @api.model
    def _get_warehouse_instance_products(self):
        products = self._burgtec_warehouse_instance_api_call("product.product", "search_read", {
            "domain": [["default_code", "!=", False], ["custom_variant_type", "=", "product"]],
            "fields": ["id", "default_code", "burgtec_product_id"],
        })
        warehouse_products = {}
        duplicate_codes = []
        for product in products:
            code = product["default_code"].strip().lower()
            if code in warehouse_products:
                duplicate_codes.append(code)
            warehouse_products[code] = product

        # same internal reference on 2 Warehouse products -> don't link
        for code in duplicate_codes:
            _logger.warning("Duplicate Internal Reference %s on Warehouse, not linked", code)
            warehouse_products.pop(code, None)
        return warehouse_products


    def action_fetch_warehouse_boms(self):
        """
        Fetch BoMs of the linked Warehouse product and store them in warehouse_bom_line_ids.
        BoM Criteria : BoM of the Warehouse variant OR BoM of its template without variant
        """
        products = self.filtered("warehouse_product_id")
        if not products:
            return
        WarehouseBom = self.env["warehouse.bom.data"]
        warehouse_variant_ids = products.mapped("warehouse_product_id")

        variants = self._burgtec_warehouse_instance_api_call("product.product", "search_read", {
            "domain": [["id", "in", warehouse_variant_ids]],
            "fields": ["id", "product_tmpl_id"],
        })
        template_by_variant = {}
        for variant in variants:
            template_by_variant[variant["id"]] = variant["product_tmpl_id"][0]

        boms = self._burgtec_warehouse_instance_api_call("mrp.bom", "search_read", {
            "domain": [
                "|",
                ["product_id", "in", warehouse_variant_ids],
                "&", ["product_id", "=", False], ["product_tmpl_id", "in", list(set(template_by_variant.values()))],
            ],
            "fields": ["id", "display_name", "code", "type", "sequence", "product_id", "product_tmpl_id"],
            "order": "sequence, id",
        })

        for product in products:
            warehouse_variant_id = product.warehouse_product_id
            template_id = template_by_variant.get(warehouse_variant_id)

            product_boms = []
            for bom in boms:
                if bom["product_id"]:
                    if bom["product_id"][0] == warehouse_variant_id:
                        product_boms.append(bom)
                elif bom["product_tmpl_id"][0] == template_id:
                    product_boms.append(bom)

            existing_lines = product.with_context(active_test=False).warehouse_bom_line_ids
            found_bom_ids = []
            for bom in product_boms:
                found_bom_ids.append(bom["id"])
                vals = {
                    "name": bom["display_name"],
                    "code": bom["code"] or False,
                    "is_kit": bom["type"] == "phantom",
                    "sequence": bom["sequence"],
                    "active": True,
                }
                line = existing_lines.filtered(lambda l: l.warehouse_bom_id == bom["id"])
                if line:
                    line.write(vals)
                else:
                    vals.update({"product_id": product.id, "warehouse_bom_id": bom["id"]})
                    WarehouseBom.create(vals)

            # BoM removed/archived in Warehouse -> archive here
            existing_lines.filtered(lambda l: l.active and l.warehouse_bom_id not in found_bom_ids).write({"active": False})