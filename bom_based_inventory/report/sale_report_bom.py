# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
from io import BytesIO
from PIL import Image, features
from lxml import etree
import xlsxwriter
import xlwt
import base64
import pytz
from datetime import date, datetime, timedelta
import calendar
from markupsafe import Markup
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.sale.models.sale_order import SALE_ORDER_STATE


class SaleReportBom(models.Model):
    _name = "sale.report.bom"
    _description = "Sales Analysis Report"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    @api.model
    def _get_done_states(self):
        return ['sale']

    # sale.order fields
    name = fields.Char(string="Order Reference", readonly=True)
    date = fields.Datetime(string="Order Date", readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string="Customer", readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', readonly=True)
    pricelist_id = fields.Many2one(comodel_name='product.pricelist', readonly=True)
    team_id = fields.Many2one(comodel_name='crm.team', string="Sales Team", readonly=True)
    user_id = fields.Many2one(comodel_name='res.users', string="Salesperson", readonly=True)
    state = fields.Selection(selection=SALE_ORDER_STATE, string="Status", readonly=True)
    invoice_status = fields.Selection(
        selection=[
            ('upselling', "Upselling Opportunity"),
            ('invoiced', "Fully Invoiced"),
            ('to invoice', "To Invoice"),
            ('no', "Nothing to Invoice"),
        ], string="Order Invoice Status", readonly=True)

    campaign_id = fields.Many2one(comodel_name='utm.campaign', string="Campaign", readonly=True)
    medium_id = fields.Many2one(comodel_name='utm.medium', string="Medium", readonly=True)
    source_id = fields.Many2one(comodel_name='utm.source', string="Source", readonly=True)

    # res.partner fields
    commercial_partner_id = fields.Many2one(
        comodel_name='res.partner', string="Customer Entity", readonly=True)
    country_id = fields.Many2one(
        comodel_name='res.country', string="Customer Country", readonly=True)
    industry_id = fields.Many2one(
        comodel_name='res.partner.industry', string="Customer Industry", readonly=True)
    partner_zip = fields.Char(string="Customer ZIP", readonly=True)
    state_id = fields.Many2one(comodel_name='res.country.state', string="Customer State", readonly=True)

    # sale.order.line fields
    order_reference = fields.Reference(
        string='Order',
        selection=[('sale.order', 'Sales Order')],
        aggregator="count_distinct",
    )

    categ_id = fields.Many2one(
        comodel_name='product.category', string="Product Category", readonly=True)
    product_id = fields.Many2one(
        comodel_name='product.product', string="Product Variant", readonly=True)
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template', string="Product", readonly=True)
    product_uom = fields.Many2one(comodel_name='uom.uom', string="Unit of Measure", readonly=True)
    product_uom_qty = fields.Float(string="Qty Ordered", readonly=True)
    qty_to_deliver = fields.Float(string="Qty To Deliver", readonly=True)
    qty_delivered = fields.Float(string="Qty Delivered", readonly=True)
    qty_to_invoice = fields.Float(string="Qty To Invoice", readonly=True)
    qty_invoiced = fields.Float(string="Qty Invoiced", readonly=True)
    price_subtotal = fields.Monetary(string="Untaxed Total", readonly=True)
    price_total = fields.Monetary(string="Total", readonly=True)
    untaxed_amount_to_invoice = fields.Monetary(string="Untaxed Amount To Invoice", readonly=True)
    untaxed_amount_invoiced = fields.Monetary(string="Untaxed Amount Invoiced", readonly=True)
    line_invoice_status = fields.Selection(
        selection=[
            ('upselling', "Upselling Opportunity"),
            ('invoiced', "Fully Invoiced"),
            ('to invoice', "To Invoice"),
            ('no', "Nothing to Invoice"),
        ], string="Invoice Status", readonly=True)

    weight = fields.Float(string="Gross Weight", readonly=True)
    volume = fields.Float(string="Volume", readonly=True)
    price_unit = fields.Float(string="Unit Price", aggregator='avg', readonly=True)
    discount = fields.Float(string="Discount %", readonly=True, aggregator='avg')
    discount_amount = fields.Monetary(string="Discount Amount", readonly=True)

    # aggregates or computed fields
    nbr = fields.Integer(string="# of Lines", readonly=True)
    currency_id = fields.Many2one(comodel_name='res.currency', compute='_compute_currency_id')
    project_reference = fields.Many2one(string="Project Reference", comodel_name='project.project', readonly=True)
    system_cost_per_unit = fields.Monetary(string='System Cost per Unit', readonly=True, currency_field='currency_id')
    live_unit_cost = fields.Monetary(string='Live Unit Cost', readonly=True, currency_field='currency_id')
    quoted_cost_per_unit = fields.Monetary(string='Quoted Cost per Unit', readonly=True, currency_field='currency_id')
    pre_project_cost_per_unit = fields.Monetary(string='Pre-Project Cost per Unit', readonly=True,
                                                currency_field='currency_id')
    system_cost_total = fields.Monetary(string='Margin on System Cost', readonly=True, currency_field='currency_id')
    live_cost_total = fields.Monetary(string='Margin on Live Cost', readonly=True, currency_field='currency_id')
    quoted_cost_total = fields.Monetary(string='Margin on Quoted Cost', readonly=True, currency_field='currency_id')
    pre_project_total = fields.Monetary(string='Margin on Pre-Project Cost', readonly=True,
                                        currency_field='currency_id')
    components_report_id = fields.Many2one('components.on.report', default=False)
    delivery_date = fields.Datetime('PO Delivery Date')
    po_id = fields.Many2one('purchase.order', string='Purchase order')

    component_html = fields.Html(string="Componenets")
    component_visible = fields.Boolean(string="Component Visible", default=True)

    @api.depends_context('allowed_company_ids')
    def _compute_currency_id(self):
        self.currency_id = self.env.company.currency_id

    def _with_sale(self):
        return ""

    def _select_sale(self):
        select_ = f"""
            MIN(l.id) AS id,
            l.product_id AS product_id,
            l.invoice_status AS line_invoice_status,
            l.component_html AS component_html,
            l.component_visible AS component_visible,
            t.uom_id AS product_uom,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.product_uom_qty / u.factor * u2.factor) ELSE 0 END AS product_uom_qty,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_delivered / u.factor * u2.factor) ELSE 0 END AS qty_delivered,
            CASE WHEN l.product_id IS NOT NULL THEN SUM((l.product_uom_qty - l.qty_delivered) / u.factor * u2.factor) ELSE 0 END AS qty_to_deliver,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_invoiced / u.factor * u2.factor) ELSE 0 END AS qty_invoiced,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_to_invoice / u.factor * u2.factor) ELSE 0 END AS qty_to_invoice,
            CASE WHEN l.product_id IS NOT NULL THEN AVG(l.price_unit
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('account_currency_table.rate')}
                ) ELSE 0
            END AS price_unit,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_total
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('account_currency_table.rate')}
                ) ELSE 0
            END AS price_total,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_subtotal
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('account_currency_table.rate')}
                ) ELSE 0
            END AS price_subtotal,
            CASE WHEN l.product_id IS NOT NULL OR l.is_downpayment THEN SUM(l.untaxed_amount_to_invoice
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('account_currency_table.rate')}
                ) ELSE 0
            END AS untaxed_amount_to_invoice,
            CASE WHEN l.product_id IS NOT NULL OR l.is_downpayment THEN SUM(l.untaxed_amount_invoiced
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('account_currency_table.rate')}
                ) ELSE 0
            END AS untaxed_amount_invoiced,
            COUNT(*) AS nbr,
            s.name AS name,
            s.custom_project_id as project_reference,
            l.system_cost_bom_total as system_cost_per_unit,
            l.quoted_cost_bom_total as quoted_cost_per_unit,
            l.pre_project_cost_bom_total as pre_project_cost_per_unit,
            l.live_cost_bom_total as live_unit_cost,
            l.system_cost_per_unit as system_cost_total,
            l.quoted_cost_per_unit as quoted_cost_total,
            l.pre_project_cost_per_unit as pre_project_total,
            l.live_unit_cost as live_cost_total,
            s.date_order AS date,
            s.state AS state,
            s.invoice_status as invoice_status,
            s.partner_id AS partner_id,
            s.user_id AS user_id,
            s.company_id AS company_id,
            s.campaign_id AS campaign_id,
            s.medium_id AS medium_id,
            s.source_id AS source_id,
            t.categ_id AS categ_id,
            s.pricelist_id AS pricelist_id,
            s.team_id AS team_id,
            s.components_report_id AS components_report_id,
            s.purchase_order_id As po_id,
            po.date_planned As delivery_date,
            p.product_tmpl_id,
            partner.commercial_partner_id AS commercial_partner_id,
            partner.country_id AS country_id,
            partner.industry_id AS industry_id,
            partner.state_id AS state_id,
            partner.zip AS partner_zip,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(p.weight * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END AS weight,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(p.volume * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END AS volume,
            l.discount AS discount,
            CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_unit * l.product_uom_qty * l.discount / 100.0
                / {self._case_value_or_one('s.currency_rate')}
                * {self._case_value_or_one('account_currency_table.rate')}
                ) ELSE 0
            END AS discount_amount,
            concat('sale.order', ',', s.id) AS order_reference"""

        additional_fields_info = self._select_additional_fields()
        template = """,
            %s AS %s"""
        for fname, query_info in additional_fields_info.items():
            select_ += template % (query_info, fname)

        return select_

    def _case_value_or_one(self, value):
        return f"""CASE COALESCE({value}, 0) WHEN 0 THEN 1.0 ELSE {value} END"""

    def _select_additional_fields(self):
        """Hook to return additional fields SQL specification for select part of the table query.

        :returns: mapping field -> SQL computation of field, will be converted to '_ AS _field' in the final table definition
        :rtype: dict
        """
        return {}

    def _from_sale(self):
        currency_table = self.env['res.currency']._get_simple_currency_table(self.env.companies)
        currency_table = self.env.cr.mogrify(currency_table).decode(self.env.cr.connection.encoding)
        return f"""
            sale_order_line l
            LEFT JOIN sale_order s ON s.id=l.order_id
            JOIN res_partner partner ON s.partner_id = partner.id
            LEFT JOIN product_product p ON l.product_id=p.id
            LEFT JOIN product_template t ON p.product_tmpl_id=t.id
            LEFT JOIN uom_uom u ON u.id=l.product_uom
            LEFT JOIN uom_uom u2 ON u2.id=t.uom_id
            JOIN purchase_order po ON s.purchase_order_id = po.id
            JOIN {currency_table} ON account_currency_table.company_id = s.company_id
            """

    def _where_sale(self):
        return """
            l.display_type IS NULL"""

    def _group_by_sale(self):
        return """
            l.product_id,
            l.order_id,
            l.price_unit,
            l.invoice_status,
            l.component_html,
            l.component_visible,
            l.system_cost_bom_total,
            l.quoted_cost_bom_total,
            l.pre_project_cost_bom_total,
            l.live_cost_bom_total,
            l.system_cost_per_unit,
            l.quoted_cost_per_unit,
            l.pre_project_cost_per_unit,
            l.live_unit_cost,
            t.uom_id,
            t.categ_id,
            s.name,
            s.date_order,
            s.partner_id,
            s.user_id,
            s.state,
            s.invoice_status,
            s.company_id,
            s.campaign_id,
            s.medium_id,
            s.source_id,
            s.pricelist_id,
            s.team_id,
            p.product_tmpl_id,
            po.date_planned,
            partner.commercial_partner_id,
            partner.country_id,
            partner.industry_id,
            partner.state_id,
            partner.zip,
            l.is_downpayment,
            l.discount,
            s.id,
            account_currency_table.rate"""

    def _query(self):
        with_ = self._with_sale()
        return f"""
            {"WITH" + with_ + "(" if with_ else ""}
            SELECT {self._select_sale()}
            FROM {self._from_sale()}
            WHERE {self._where_sale()}
            GROUP BY {self._group_by_sale()}
            {")" if with_ else ""}
        """

    @property
    def _table_query(self):
        return self._query()

    def action_open_order(self):
        self.ensure_one()
        return {
            'res_model': self.order_reference._name,
            'type': 'ir.actions.act_window',
            'views': [[False, 'form']],
            'res_id': self.order_reference.id,
        }

    def action_open_order_components(self):
        view_id= self.env.ref('bom_based_inventory.view_components_on_report_form').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'components.on.report',
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'target': 'new',
            'context': {
                'sale_order': self.order_reference.id,
                'no_create': True,  # Disable record creation
                'no_open': True,  # Disable opening records
            }
        }

    # @api.model
    # def web_read_group(self, domain, fields, groupby, limit=None, offset=0, orderby=False, lazy=True):
    #     res = super().web_read_group(domain, fields, groupby, limit, offset, orderby, lazy)
    #     all_records = self.env['sale.report.bom'].search([])
    #     for rec in all_records:
    #         rec.update_component_html()
    #     return res  
    
    def update_component_html(self):
        """Update the component_html field with the HTML table of components."""
        for rec in self:
            sale_order_line_obj = self.env['sale.order.line'].browse(rec.id)
            sale_order_line_obj.fill_component_html()

    def show_bom_components_in_list(self):
        sale_order_line_obj = self.env['sale.order.line'].browse(self.id) #bom report id is same as its sale order line id.
        for rec in self:
            if rec.component_visible:
                sale_order_line_obj.component_visible = False
            else:
                sale_order_line_obj.fill_component_html()
                sale_order_line_obj.component_visible = True
        # if self.is_component_shown:
        #     sale_order_line_obj.is_component_shown = False
        # if not self.is_component_shown:
        #     # print('SELF--------->',self) self.id is same as its sale order line id.
        #     sale_order = self.order_reference
        #     purchase_order = self.po_id
        #     parent_po = sale_order.purchase_order_id
        #     child_purchase_order = self.env['purchase.order']
        #     if parent_po.picking_ids:
        #         picking_name = parent_po.picking_ids[0].display_name
        #         child_purchase_order = self.env['purchase.order'].search([('origin', '=', picking_name)])
        #     # print('Sale Order BOM ID', sale_order.bom_component_id)
        #     # print('Sale Order BOM ID Componenet Line IDS', sale_order.bom_component_id.component_line_ids)       
        #     # print('Sale Order',sale_order)
        #     # print('Purchase Order',purchase_order)
        #     # print('Parent PO', parent_po)
        #     # print('Component Lines', component_lines)
        #     # print('Self Product', self.product_id)
        #     # print('Self Product tEMPL', self.product_tmpl_id)

        #     table_code = Markup('''<table class="table table-bordered o_table" data-oe-version="1.2">
        #                                             <tbody>
        #                                                 <tr class="fw-bold">
        #                                                     <td><div>Product Reference</div></td>
        #                                                     <td><div>Product</div></td>
        #                                                     <td><div>Quantity</div></td>
        #                                                     <td><div>Live Unit Cost</div></td>
        #                                                     <td><div>System Cost Per Unit</div></td>
        #                                                     <td><div>Quoted Cost Per Unit</div></td>
        #                                                     <td><div>Pre Project Cost Per Unit</div></td>
        #                                                     <td><div>Supplier</div></td>
        #                                                     <td><div>Delivery Date</div></td>
        #                                                     <td><div>Purchase Order</div></td>
        #                                                 </tr>''')
        #     if sale_order.bom_component_id:
        #         for line in sale_order.bom_component_id.component_line_ids.filtered(lambda l: l.parent_product_id.id == self.product_tmpl_id.id):
        #             if not line.is_parent:
        #                 matching_po = child_purchase_order.filtered(lambda po: any(ol.product_id.id == line.product_id.id for ol in po.order_line) and po.partner_id.id == line.supplier_id.id)
        #                 matching_po = matching_po[0] if matching_po else False
        #                 delivery_date = matching_po.date_planned if matching_po else False
        #                 table_code += Markup('''<tr>
        #                                             <td><div>{product_reference}</div></td>
        #                                             <td><div>{product}</div></td>
        #                                             <td><div>{quantity}</div></td>
        #                                             <td><div>{live_unit_cost}</div></td>
        #                                             <td><div>{system_cost_per_unit}</div></td>
        #                                             <td><div>{quoted_cost_per_unit}</div></td>
        #                                             <td><div>{pre_project_cost_per_unit}</div></td>
        #                                             <td><div>{supplier}</div></td>
        #                                             <td><div>{delivery}</div></td>
        #                                             <td><div>{purchase_order}</div></td>
        #                                         </tr>
        #                                     ''').format(product_reference=line.product_reference if line.product_reference else 'N/A',
        #                                                 product=line.product_id.name if line.product_id else 'N/A',
        #                                                 quantity=line.product_qty if line.product_qty else 0,
        #                                                 live_unit_cost=line.live_unit_cost if line.live_unit_cost else 0,
        #                                                 system_cost_per_unit=line.system_cost_per_unit if line.system_cost_per_unit else 0,
        #                                                 quoted_cost_per_unit=line.quoted_cost_per_unit if line.quoted_cost_per_unit else 0,
        #                                                 pre_project_cost_per_unit=line.pre_project_cost_per_unit if line.pre_project_cost_per_unit else 0,
        #                                                 supplier=line.supplier_id.name if line.supplier_id else 'N/A',
        #                                                 delivery=delivery_date if delivery_date else 'N/A',
        #                                                 purchase_order=matching_po.name if matching_po else 'N/A')
        #         table_code += Markup('''</tbody></table><div><br></div>''')
        #         sale_order_line_obj.component_html = table_code



        # Excel Reoport ~~~~~~~~~~~~~~~~~~~~~~~``

    def action_xlwt_report(self):

        file_name = 'product_component_report.xls'
        workbook = xlwt.Workbook(encoding="UTF-8")
        sheet = workbook.add_sheet("Product Component Report", cell_overwrite_ok=True)

        purchase_order_status = {'draft': 'Draft', 'sent': 'RFQ Sent', 'to approve': 'To Approve',
                                 'purchase': 'Purchase Order', 'done': 'Locked', 'cancel': 'Cancelled'}
        # Headers and style
        header_style = xlwt.easyxf(
            'font: bold True;'
            'align: horiz left, vert center;'
            'borders: left thick, right thick, top thick, bottom thick;'
        )

        headers = [
            'Sale Order', 'Purchase Order', 'Purchase Delivery Date',
            'Product', 'Customer', 'Salesperson', 'Company',
            'Quantity', 'Unit Price', 'Total', 'System Cost Per Unit',
            'Live Unit Cost', 'Quoted Cost Per Unit', 'Pre-Project Cost Per Unit',
            'Margin On System Cost', 'Margin On Quoted Cost',
            'Margin On Pre-Project Cost', 'Margin On Live Cost',
        ]

                    # Set column widths
        column_widths = [25 for h in headers] 
        for idx, width in enumerate(column_widths):
            sheet.col(idx).width = 256 * width
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_style)
        row = 1

        user_timezone = pytz.timezone(self.env.context.get('tz') or self.env.user.tz)
        date_planned_user_timezone = False
        date_delivery_user_timezone = False
        for record in self:
            if record.po_id and record.po_id.date_planned:
                date_planned_user_timezone = pytz.utc.localize(record.po_id.date_planned).astimezone(user_timezone).strftime("%d/%m/%Y %H:%M:%S")

            planned_date = date_planned_user_timezone if record.po_id else 'N/A'
            sheet.write(row, 0, record.name or 'N/A')  # Sale Order
            sheet.write(row, 1, record.po_id.name or 'N/A')  # Purchase Order
            sheet.write(row, 2, str(planned_date) or 'N/A')  # Delivery Date
            sheet.write(row, 3, record.product_id.name or 'N/A')  # Product
            sheet.write(row, 4, record.partner_id.name or 'N/A')  # Customer
            sheet.write(row, 5, record.user_id.name or 'N/A')  # Salesperson
            sheet.write(row, 6, record.company_id.name or 'N/A')  # Company
            sheet.write(row, 7, record.product_uom_qty or 'N/A')  # Quantity
            sheet.write(row, 8, record.price_unit or 'N/A')  # Unit Price
            sheet.write(row, 9, record.price_total or 'N/A')  # Total
            sheet.write(row, 10, record.system_cost_per_unit or 'N/A')  # System Cost Per UNit
            sheet.write(row, 11, record.live_unit_cost or 'N/A')  # Live Unit Cost
            sheet.write(row, 12, record.quoted_cost_per_unit or 'N/A')  # Quoted Cost Per Unit
            sheet.write(row, 13, record.pre_project_cost_per_unit or 'N/A')  # Pre-Project Cost Per Unit
            sheet.write(row, 14, record.system_cost_total or 'N/A')  # Margin On System Cost
            sheet.write(row, 15, record.quoted_cost_total or 'N/A')  # Margin On Quoted Cost
            sheet.write(row, 16, record.pre_project_total or 'N/A')  # Margin On Pre-Project Cost
            sheet.write(row, 17, record.live_cost_total or 'N/A')  # Margin On Live Cost

            #Componenets Lines
            sale_order_line = self.env['sale.order.line'].browse(record.id)
            sale_order = sale_order_line.order_id
            purchase_order = sale_order.purchase_order_id
            parent_po = sale_order.purchase_order_id
            child_purchase_order = self.env['purchase.order']
            if parent_po.picking_ids:
                picking_name = parent_po.picking_ids[0].display_name
                child_purchase_order = self.env['purchase.order'].search([('origin', '=', picking_name)])
            components = sale_order_line.order_id.bom_component_id.component_line_ids.filtered(lambda l: l.parent_product_id.id == sale_order_line.product_template_id.id and l.order_line_id.id == sale_order_line.id)
            if components:

                component_headers = [
                'Product Reference', 'Product', 'Quantity',
                'Live Unit Cost', 'System Cost Per Unit', 'Quoted Cost Per Unit', 'Pre-Project Cost Per Unit',
                'Note', 'Supplier', 'Delivery Date', 'Purchase Order',
                'Purchase Order Status'
                ]

                start_col = 18  # Start from column 18 (Excel column 'S')

                # Set column widths
                for idx, _ in enumerate(component_headers):
                    sheet.col(start_col + idx).width = 256 * 25  # Width = 25 characters

                # Write headers starting from column 18
                for col, component_header in enumerate(component_headers):
                    sheet.write(0, start_col + col, component_header, header_style)

                for component in components:
                    if not component.is_parent:
                        matching_po = child_purchase_order.filtered(lambda po: any(ol.product_id.id == component.product_id.id for ol in po.order_line) and po.partner_id.id == component.supplier_id.id)
                        matching_po = matching_po[0] if matching_po else False
                        if matching_po and matching_po.date_planned:
                            date_delivery_user_timezone = pytz.utc.localize(matching_po.date_planned).astimezone(user_timezone).strftime("%d/%m/%Y %H:%M:%S")
                        delivery_date = date_delivery_user_timezone if matching_po else 'N/A'
                        # delivery_date = matching_po.date_planned if matching_po else False

                        sheet.write(row, 18, component.product_reference or 'N/A')  # Product Reference
                        sheet.write(row, 19, component.product_id.name if component.product_id else 'N/A')  # Product Name
                        sheet.write(row, 20, component.product_qty or 0)  # Product Quantity
                        sheet.write(row, 21, component.live_unit_cost or 0)  # Live Cost
                        sheet.write(row, 22, component.system_cost_per_unit or 0)  # System Cost
                        sheet.write(row, 23, component.quoted_cost_per_unit or 0)  # Quoted Cost
                        sheet.write(row, 24, component.pre_project_cost_per_unit or 0)  # Pre Project Cost
                        sheet.write(row, 25, component.note or 'N/A')  # Note
                        sheet.write(row, 26, component.supplier_id.name if component.supplier_id else 'N/A')  # Supplier Name

                        sheet.write(row, 27, str(delivery_date) or 'N/A')  # Delivery Date
                        sheet.write(row, 28, matching_po.name if matching_po else 'N/A')  # Matching PO Name
                        sheet.write(row, 29, purchase_order_status[matching_po.state] if matching_po else 'N/A')  # Matching PO Status

                        row +=1

            row +=1

        # Save to memory
        fp = BytesIO()
        workbook.save(fp)
        fp.seek(0)
        excel_file = base64.b64encode(fp.read())
        file_name = file_name
        fp.close()

        # Store the binary data in the model field
        sale_order_line_obj = self.env['sale.order.line'].browse(self[-1].id)
        sale_order_line_obj.excel_file = excel_file
        sale_order_line_obj.file_name = file_name


        # Return file download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/sale.order.line/{self[-1].id}/excel_file/{file_name}?download=true',
            'target': 'self'
        }
    

    def action_xlswriter_report(self):
        fp = BytesIO()

        file_name = 'Sales Bom Report.xls'
        workbook = xlsxwriter.Workbook(fp,{'in_memory': True})
        sheet = workbook.add_worksheet()

        purchase_order_status = {'draft': 'Draft', 'sent': 'RFQ Sent', 'to approve': 'To Approve',
                                 'purchase': 'Purchase Order', 'done': 'Locked', 'cancel': 'Cancelled'}
        
        fixed_size = (600, 570)
        
        # Headers and style
        header_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'border': 2,  # 2 = thick border in xlsxwriter
        })

        headers = [
            'Sale Order', 'Purchase Order', 'Purchase Delivery Date',
            'Product', 'Product Image', 'Customer', 'Salesperson', 'Company',
            'Quantity', 'Unit Price', 'Total', 'System Cost Per Unit',
            'Live Unit Cost', 'Quoted Cost Per Unit', 'Pre-Project Cost Per Unit',
            'Margin On System Cost', 'Margin On Quoted Cost',
            'Margin On Pre-Project Cost', 'Margin On Live Cost',
        ]

                    # Set column widths
# ...existing code...
        column_widths = [25 for h in headers]
        for idx, width in enumerate(column_widths):
            sheet.set_column(idx, idx, width)
# ...existing code...
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        row = 1

        user_timezone = pytz.timezone(self.env.context.get('tz') or self.env.user.tz)
        date_planned_user_timezone = False
        date_delivery_user_timezone = False
        for record in self:
            sale_order_line = self.env['sale.order.line'].browse(record.id)
            # print('Record ID',record.id)
            # sale_order_line.sudo().search([('id','=',1184)])
            # print(sale_order_line)
            # print(record.id,sale_order_line.id,sale_order_line.product_id.name)

            if record.po_id and record.po_id.date_planned:
                date_planned_user_timezone = pytz.utc.localize(record.po_id.date_planned).astimezone(user_timezone).strftime("%d/%m/%Y %H:%M:%S")

            planned_date = date_planned_user_timezone if record.po_id else 'N/A'
            sheet.write(row, 0, record.name or 'N/A')  # Sale Order
            sheet.write(row, 1, record.po_id.name or 'N/A')  # Purchase Order
            sheet.write(row, 2, str(planned_date) or 'N/A')  # Delivery Date
            sheet.set_column(3, 3,50)
            sheet.write(row, 3, record.product_id.name or 'N/A')  # Product    
            if sale_order_line and sale_order_line.image_128:
                try:
                    image_bytes = base64.b64decode(sale_order_line.image_128)
                    image_data = BytesIO(image_bytes)
                    try:
                        img = Image.open(image_data)
                        img = img.resize(fixed_size, Image.LANCZOS)
                    except Exception:
                        # Try converting to RGB and saving as PNG if format is not recognized
                        image_data.seek(0)
                        img = Image.open(image_data).convert("RGB")
                        img = img.resize(fixed_size, Image.LANCZOS)
                    # Always save as PNG for xlsxwriter compatibility
                    png_stream = BytesIO()
                    img.save(png_stream, format="PNG")
                    png_stream.seek(0)
                    sheet.set_row(row, 100)
                    sheet.insert_image(row, 4, 'product.png', {
                        'image_data': png_stream,
                        'x_scale': 0.25,
                        'y_scale': 0.22,
                        'x_offset': 29,
                        'y_offset': 1,
                        'object_position': 1,
                    })
                except Exception as e:
                    sheet.write(row, 4, 'N/A')  # Or log the error if needed
            elif sale_order_line and not sale_order_line.image_128:
                if record.product_id.image_1920:
                    try:
                        image_bytes = base64.b64decode(record.product_id.image_1920)
                        image_data = BytesIO(image_bytes)
                        try:
                            img = Image.open(image_data)
                            img = img.resize(fixed_size, Image.LANCZOS)
                        except Exception:
                            # Try converting to RGB and saving as PNG if format is not recognized
                            image_data.seek(0)
                            img = Image.open(image_data).convert("RGB")
                            img = img.resize(fixed_size, Image.LANCZOS)
                        # Always save as PNG for xlsxwriter compatibility
                        png_stream = BytesIO()
                        img.save(png_stream, format="PNG")
                        png_stream.seek(0)
                        sheet.set_row(row, 100)
                        sheet.insert_image(row, 4, 'product.png', {
                            'image_data': png_stream,
                            'x_scale': 0.25,
                            'y_scale': 0.22,
                            'x_offset': 29,
                            'y_offset': 1,
                            'object_position': 1,
                        })
                    except Exception as e:
                        sheet.write(row, 4, 'N/A')  # Or log the error if needed
                else:
                    sheet.write(row, 4, 'N/A')
            else:
                    sheet.write(row, 4, 'N/A')
            sheet.write(row, 5, record.partner_id.name or 'N/A')  # Customer
            sheet.write(row, 6, record.user_id.name or 'N/A')  # Salesperson
            sheet.write(row, 7, record.company_id.name or 'N/A')  # Company
            sheet.write(row, 8, record.product_uom_qty or 'N/A')  # Quantity
            sheet.write(row, 9, record.price_unit or 'N/A')  # Unit Price
            sheet.write(row, 10, record.price_total or 'N/A')  # Total
            sheet.write(row, 11, record.system_cost_per_unit or 'N/A')  # System Cost Per UNit
            sheet.write(row, 12, record.live_unit_cost or 'N/A')  # Live Unit Cost
            sheet.write(row, 13, record.quoted_cost_per_unit or 'N/A')  # Quoted Cost Per Unit
            sheet.write(row, 14, record.pre_project_cost_per_unit or 'N/A')  # Pre-Project Cost Per Unit
            sheet.write(row, 15, record.system_cost_total or 'N/A')  # Margin On System Cost
            sheet.write(row, 16, record.quoted_cost_total or 'N/A')  # Margin On Quoted Cost
            sheet.write(row, 17, record.pre_project_total or 'N/A')  # Margin On Pre-Project Cost
            sheet.write(row, 18, record.live_cost_total or 'N/A')  # Margin On Live Cost

            #Componenets Lines
            
            sale_order = sale_order_line.order_id
            purchase_order = sale_order.purchase_order_id
            parent_po = sale_order.purchase_order_id
            child_purchase_order = self.env['purchase.order']
            if parent_po.picking_ids:
                picking_name = parent_po.picking_ids[0].display_name
                child_purchase_order = self.env['purchase.order'].search([('origin', '=', picking_name)])
            components = sale_order_line.order_id.bom_component_id.component_line_ids.filtered(lambda l: l.parent_product_id.id == sale_order_line.product_template_id.id and l.order_line_id.id == sale_order_line.id)
            if components:

                component_headers = [
                'Product Reference', 'Product', 'Quantity',
                'Live Unit Cost', 'System Cost Per Unit', 'Quoted Cost Per Unit', 'Pre-Project Cost Per Unit',
                'Note', 'Supplier', 'Delivery Date', 'Purchase Order',
                'Purchase Order Status'
                ]

                start_col = 19  # Start from column 19 (Excel column 'T')

                # Set column widths
                for idx, _ in enumerate(component_headers):
                    sheet.set_column(start_col + idx, start_col + idx, 25)

                # Write headers starting from column 18
                for col, component_header in enumerate(component_headers):
                    sheet.write(0, start_col + col, component_header, header_format)

                for component in components:
                    if not component.is_parent:
                        matching_po = child_purchase_order.filtered(lambda po: any(ol.product_id.id == component.product_id.id for ol in po.order_line) and po.partner_id.id == component.supplier_id.id)
                        matching_po = matching_po[0] if matching_po else False
                        if matching_po and matching_po.date_planned:
                            date_delivery_user_timezone = pytz.utc.localize(matching_po.date_planned).astimezone(user_timezone).strftime("%d/%m/%Y %H:%M:%S")
                        delivery_date = date_delivery_user_timezone if matching_po else 'N/A'
                        # delivery_date = matching_po.date_planned if matching_po else False

                        sheet.write(row, 19, component.product_reference or 'N/A')  # Product Reference
                        sheet.set_column(20, 20,50)
                        sheet.write(row, 20, component.product_id.name if component.product_id else 'N/A')  # Product Name
                        sheet.write(row, 21, component.product_qty or 0)  # Product Quantity
                        sheet.write(row, 22, component.live_unit_cost or 0)  # Live Cost
                        sheet.write(row, 23, component.system_cost_per_unit or 0)  # System Cost
                        sheet.write(row, 24, component.quoted_cost_per_unit or 0)  # Quoted Cost
                        sheet.write(row, 25, component.pre_project_cost_per_unit or 0)  # Pre Project Cost
                        sheet.write(row, 26, component.note or 'N/A')  # Note
                        sheet.write(row, 27, component.supplier_id.name if component.supplier_id else 'N/A')  # Supplier Name

                        sheet.write(row, 28, str(delivery_date) or 'N/A')  # Delivery Date
                        sheet.write(row, 29, matching_po.name if matching_po else 'N/A')  # Matching PO Name
                        sheet.write(row, 30, purchase_order_status[matching_po.state] if matching_po else 'N/A')  # Matching PO Status

                        row +=1

            row +=1
  
        workbook.close() #saves the file
        excel_file = base64.b64encode(fp.getvalue())
        file_name = file_name
        fp.close()

        # Store the binary data in the model field
        sale_order_line_obj = self.env['sale.order.line'].browse(self[-1].id)
        sale_order_line_obj.excel_file = excel_file
        sale_order_line_obj.file_name = file_name


        # Return file download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/sale.order.line/{self[-1].id}/excel_file/{file_name}?download=true',
            'target': 'self'
        }

