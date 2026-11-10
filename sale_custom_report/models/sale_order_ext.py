import re
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError


class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    hubspot_reference = fields.Char(string="Hubspot Reference")

    project_name = fields.Char()

    delivery_code_calculation_id = fields.Many2one('delivery.code.calculation', copy=False)

    is_show_total_breakdown = fields.Boolean(default=True)

    quote_type = fields.Selection([
        ('sales_quote', 'Sales Quote'),
        ('project_quote', 'Project Quote'),
        ('delivery_stage', 'Delivery Stage'),
    ])
    buildertrend_po = fields.Char(copy=False)
    is_in_builder_trend = fields.Boolean('Is Builder Trend ?', default=False, copy=False)
    delivery_stage = fields.Char(copy=False)

    zone_type = fields.Selection(
        [
            ('zone1', 'Zone 1 [EASTCOAST METRO (BNE, SYD, CBR, MEL)]'),
            ('zone2', 'Zone 2 [SYD]'),
            ('zone3', 'Zone 3 [BNE/MEL]'),
        ], default="zone1"
    )
    location = fields.Selection([
        ('nsw', 'New South Wales'),
        ('act', 'Australian Capital Territory'),
        ('vic', 'Victoria'),
        ('qld', 'Queensland'),
        ('other', 'Other')
    ], string="Location")

    # Defining this field here so we can use it. It was originally created for defect group logic in sale order customisation module.
    defected_line_ids = fields.Many2many('sale.order.line')

    def action_confirm(self):
        if not self.quote_type:
            self.quote_type = 'project_quote'
        res = super(SaleOrderExt, self).action_confirm()
        return res

    def mark_project_with_builder_trend_check(self):
        for rec in self:
            if rec.quote_type == 'project_quote':
                rec.is_in_builder_trend = True

    @api.model_create_multi
    def create(self, vals_list):
        group_id = False
        section_id = False
        group_name = ""
        section_name = ""
        res = super(SaleOrderExt, self).create(vals_list)

        for record in res:
            if record.order_line:
                for line in record.order_line.sorted(lambda o: o.sequence):
                    if line.display_type == 'line_section':
                        group_name = line.name
                        group_id = line.id
                        section_name = ""
                        section_id = False
                    if line.display_type == 'line_note':
                        section_name = line.name
                        section_id = line.id
                        line.line_group_name = group_name
                        line.line_group_id_value = group_id
                    if not line.display_type:
                        line.line_group_name = group_name
                        line.line_group_id_value = group_id
                        line.line_section_name = section_name
                        line.line_section_id_value = section_id

        return res

    def write(self, values):
        group_id = False
        section_id = False
        group_name = ""
        section_name = ""
        res = super(SaleOrderExt, self).write(values)
        for record in self:
            if record.order_line:
                for line in record.order_line.sorted(lambda o: o.sequence):
                    if line.display_type == 'line_section':
                        group_name = line.name
                        group_id = line.id
                        section_name = ""
                        section_id = False
                    if line.display_type == 'line_note':
                        section_name = line.name
                        section_id = line.id
                        line.line_group_name = group_name
                        line.line_group_id_value = group_id
                    if not line.display_type:
                        line.line_group_name = group_name
                        line.line_group_id_value = group_id
                        line.line_section_name = section_name
                        line.line_section_id_value = section_id
        return res

    def action_show_delivery_code_calculation(self):
        self.ensure_one()
        return {
            'name': _('Delivery Code Calculation'),
            'type': 'ir.actions.act_window',
            'res_model': 'delivery.code.calculation',
            'res_id': self.delivery_code_calculation_id.id or False,
            'view_id': self.env.ref('sale_custom_report.delivery_code_calculation_view_form').id,
            'view_mode': 'form',
            'target': 'self',
            'context': {'active_id': self.id}
        }

    def action_preview_burgtec_pdf_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/pdf/sale_custom_report.burgtec_sale_quote_v2/{self.id}',
            'target': 'new',
        }
    
    def force_calculate_summary(self):
        for record in self:
            if record.delivery_code_calculation_id:
                record.delivery_code_calculation_id._compute_summary_lines()

    def force_calculate_summary(self):
        for record in self:
            if record.delivery_code_calculation_id:
                record.delivery_code_calculation_id._compute_summary_lines()
    
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    custom_product_code = fields.Char(
        string='Code',
    )

    custom_product_name = fields.Char(
        string="Product Name",
        compute="_compute_custom_product_name", store=True, readonly=False
    )

    image_128 = fields.Image(string="Image",compute="_compute_img_128", store=True, readonly=False)

    line_group_id_value = fields.Char()

    line_section_id_value = fields.Char()

    line_group_name = fields.Char()

    line_section_name = fields.Char()

    is_image_available = fields.Boolean(
        compute="_compute_is_image_available",
        store=True,
        string="Image Available"
    )

    @api.depends('product_id.image_1920')
    def _compute_is_image_available(self):
        for line in self:
            line.is_image_available = bool(line.product_id.image_1920)

    # Create method to mimic on delete feature

    @api.depends("product_template_id", "product_id")
    def _compute_custom_product_name(self):
        for record in self:
            if record.product_template_id:
                record.custom_product_name = record.product_template_id.name
            elif record.product_id:
                record.custom_product_name = record.product_id.name
            else:
                record.custom_product_name = False

    @api.model_create_multi
    def create(self, vals_list):
        res = super(SaleOrderLine, self).create(vals_list)
        for sol in res:
            if not sol.is_downpayment:
                if sol.order_id.delivery_code_calculation_id:
                    vals = {
                        'display_type': sol.display_type or False,
                        'name': sol.name if sol.display_type else False,
                        'product_id': sol.product_template_id.id if sol.product_id else False,
                        'quantity': sol.product_uom_qty if sol.product_template_id else 0,
                        'line_group_name': sol.line_group_name,
                        'line_section_name': sol.line_section_name,
                        'line_group_id_value': sol.line_group_id_value,
                        'line_section_id_value': sol.line_section_id_value,
                        'sale_order_line_id': sol.id,
                        'sequence': sol.sequence,
                    }
                    sol.order_id.delivery_code_calculation_id.delivery_code_calculation_line_ids = [Command.create(vals)]
        return res

    def format_product_description(self, text):
        headings = ['Dimensions:', 'Features:', 'Finishes:', 'Warranty:', 'Lead Time:']

        for heading in headings:
            # Use word boundary to ensure we match complete headings
            pattern = r'\b' + re.escape(heading)
            replacement = f'<strong>{heading}</strong>'
            text = re.sub(pattern, replacement, text)

        return text
    
    @api.depends('product_id','product_id.image_128','product_id.image_1920')
    def _compute_img_128(self):
        for record in self:
            if record.product_id:
                record.image_128 = record.product_id.image_128
            else:
                record.image_128 = False

