from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleQuotePlanningScreen(models.Model):
    _name = 'sale.quote.planning.screen'
    _description = 'Sale Quote Planning Screen'
    _rec_name = 'order_id'
    _order = 'order_id'

    order_id = fields.Many2one('sale.order', string='Sale Order', ondelete='cascade')
    sale_quote_line_ids = fields.One2many('sale.quote.planning.screen.line', 'sale_quote_planning_screen_id',
                                          string="Sale Quote Planning Screen Lines")
    stage_count = fields.Integer(
        string="Number of Stages", required=True
    )


class SaleQuotePlanningScreenLine(models.Model):
    _name = "sale.quote.planning.screen.line"
    _description = 'Sale Quote Planning Screen Line'

    sale_quote_planning_screen_id = fields.Many2one('sale.quote.planning.screen', ondelete='cascade')

    line_group_name = fields.Char(related='order_line_id.line_group_name', store=True)
    line_section_name = fields.Char(related='order_line_id.line_section_name', store=True)
    line_group_id_value = fields.Char(related='order_line_id.line_group_id_value', store=True)
    line_section_id_value = fields.Char(related='order_line_id.line_section_id_value', store=True)
    code = fields.Char(related='order_line_id.line_section_name', string='code', store=True)
    product_name = fields.Char(related='order_line_id.custom_product_name', string='Product Name', store=True)

    item = fields.Integer(string="Item", readonly=True)
    order_line_id = fields.Many2one('sale.order.line', ondelete='cascade')
    product_id = fields.Many2one('product.template', string="Product Template")
    product_variant_id = fields.Many2one('product.product', related="order_line_id.product_id",
                                         string="Product Variant", store=True)
    lead_time = fields.Text(string="Lead Time", readonly=True)
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note"),
        ('line_group', "Group"),
    ], string="Display Type")
    requested_delivery_date = fields.Date(string="Requested Delivery Date")
    approval_required_by = fields.Date(string="Approval Required By")
    approval_method = fields.Selection([
        ('shop_drawing', 'Shop Drawing'),
        ('approved_quote', 'Approved Quote'),
        ('spec_sheet', 'Spec Sheet')
    ], string="Approval Method")
    approval_status = fields.Selection([
        ('awaiting_approval', 'Awaiting Approval'),
        ('awaiting_revision', 'Awaiting Revision'),
        ('approved_with_comment', 'Approved with Comment'),
        ('fully_approved', 'Fully Approved By Customer')
    ], string="Approval Status")
    line_item_status = fields.Selection([
        ('unschedule', 'Unschedule'),
        ('sales_sales_court', 'Sales-Sales Court'),
        ('sales_customer_court', 'Sales-Customer Court'),
        ('technical_initial_check', 'Technical-Initial Check'),
        ('technical_final_check', 'Technical-Final Check'),
        ('technical_purchasing', 'Technical-Purchasing'),
        ('projects_awaiting_delivery', 'Projects-Awaiting Delivery'),
        ('projects_delivered', 'Projects-Delivered'),
        ('projects_installed', 'Projects-Installed'),
    ], string="Line Item Status", default='unschedule')
    approval_comments = fields.Text(string="Approval Comments")
    quantity = fields.Float(related="order_line_id.product_uom_qty", store=True)
    total_available_quantity = fields.Float(string="Available Quantity",
                                            compute="_compute_total_available_qty", store=True)

    sales_comments = fields.Text(string="Sales Comments")
    technical_comments = fields.Text(string="Technical Comments")
    delivery_comments = fields.Text(string="Delivery Comments")

    do_stage_1 = fields.Integer("DO Stage 1")
    do_stage_2 = fields.Integer("DO Stage 2")
    do_stage_3 = fields.Integer("DO Stage 3")
    do_stage_4 = fields.Integer("DO Stage 4")
    do_stage_5 = fields.Integer("DO Stage 5")
    do_stage_6 = fields.Integer("DO Stage 6")
    do_stage_7 = fields.Integer("DO Stage 7")
    do_stage_8 = fields.Integer("DO Stage 8")
    do_stage_9 = fields.Integer("DO Stage 9")
    do_stage_10 = fields.Integer("DO Stage 10")
    do_stage_11 = fields.Integer("DO Stage 11")
    do_stage_12 = fields.Integer("DO Stage 12")
    do_stage_13 = fields.Integer("DO Stage 13")
    do_stage_14 = fields.Integer("DO Stage 14")
    do_stage_15 = fields.Integer("DO Stage 15")
    do_stage_16 = fields.Integer("DO Stage 16")
    do_stage_17 = fields.Integer("DO Stage 17")
    do_stage_18 = fields.Integer("DO Stage 18")
    do_stage_19 = fields.Integer("DO Stage 19")
    do_stage_20 = fields.Integer("DO Stage 20")
    do_stage_21 = fields.Integer("DO Stage 21")
    do_stage_22 = fields.Integer("DO Stage 22")
    do_stage_23 = fields.Integer("DO Stage 23")
    do_stage_24 = fields.Integer("DO Stage 24")
    do_stage_25 = fields.Integer("DO Stage 25")
    do_stage_26 = fields.Integer("DO Stage 26")
    do_stage_27 = fields.Integer("DO Stage 27")
    do_stage_28 = fields.Integer("DO Stage 28")
    do_stage_29 = fields.Integer("DO Stage 29")
    do_stage_30 = fields.Integer("DO Stage 30")
    do_stage_31 = fields.Integer("DO Stage 31")
    do_stage_32 = fields.Integer("DO Stage 32")
    do_stage_33 = fields.Integer("DO Stage 33")
    do_stage_34 = fields.Integer("DO Stage 34")
    do_stage_35 = fields.Integer("DO Stage 35")
    do_stage_36 = fields.Integer("DO Stage 36")
    do_stage_37 = fields.Integer("DO Stage 37")
    do_stage_38 = fields.Integer("DO Stage 38")
    do_stage_39 = fields.Integer("DO Stage 39")
    do_stage_40 = fields.Integer("DO Stage 40")
    do_stage_41 = fields.Integer("DO Stage 41")
    do_stage_42 = fields.Integer("DO Stage 42")
    do_stage_43 = fields.Integer("DO Stage 43")
    do_stage_44 = fields.Integer("DO Stage 44")
    do_stage_45 = fields.Integer("DO Stage 45")
    do_stage_46 = fields.Integer("DO Stage 46")
    do_stage_47 = fields.Integer("DO Stage 47")
    do_stage_48 = fields.Integer("DO Stage 48")
    do_stage_49 = fields.Integer("DO Stage 49")
    do_stage_50 = fields.Integer("DO Stage 50")


    sd_url = fields.Char('Approved SD Url')
    internal_sd_url = fields.Char('Internal SD Url')
    other_url = fields.Char('Other Url')
    has_indented_components = fields.Boolean(related='order_line_id.has_indented_components',string='Has Indented Components ?')

    @api.depends(*(f'do_stage_{i}' for i in range(1, 51)),
                 'quantity')
    def _compute_total_available_qty(self):
        for line in self:
            stage_fields = [f for f in line._fields if f.startswith("do_stage_")]
            total_stages = sum(getattr(line, f) or 0 for f in stage_fields)
            if line.quantity and total_stages:
                line.total_available_quantity = line.quantity - total_stages
                if line.total_available_quantity < 0:
                    raise ValidationError(
                        f"You cannot enter more quantities than the original quantity"
                    )

            else:
                line.total_available_quantity = line.quantity
    
    def action_view_product_line(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'View Sale Order Product Line',
            'res_model': 'sale.order.line',
            'res_id': self.order_line_id.id,
            'view_id': self.env.ref(
                'sale_quote_planning_screen.view_sale_order_line_from_sale_quote_planning_screen'
            ).id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
            }
        }
