from odoo import models, fields, api, _

class PlanningScreen(models.Model):
    _name = 'planning.screen'
    _description = 'Planning Screen'


    order_id = fields.Many2one('sale.order', string='Sale Order', required=True, ondelete='cascade')
    line_ids = fields.One2many('planning.screen.line', 'planning_screen_id', string="Lines", domain=[('display_type', '=', False)])
    state = fields.Selection(related='order_id.state',store=True)


class PlanningScreenLine(models.Model):
    _name="planning.screen.line"
    _description = 'Planning Screen Line'


    planning_screen_id = fields.Many2one('planning.screen', ondelete='cascade')
    is_child_sale_order = fields.Boolean(related='planning_screen_id.order_id.is_child_sale_order',store=True)
    total_available_quantity = fields.Integer(string="Total Unscheduled Quantity",compute="_compute_total_available_qty",store=True)
    product_reference = fields.Char('Product Reference')
    product_id = fields.Many2one('product.template', string="Product Template")
    product_variant_id = fields.Many2one('product.product', related="order_line_id.product_id", string="Product Variant", store=True)    
    available_quantity = fields.Float(string="Available Quantity",related="order_line_id.product_uom_qty")
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note"),
        ('line_group', "Group"),
    ], string="Display Type")
    name = fields.Char('Product', compute="_compute_line_name", store=True)
    order_line_id = fields.Many2one('sale.order.line', ondelete='cascade')
    origin_order_line = fields.Char(store=True)
    sequence = fields.Integer(related='order_line_id.sequence')
    quantity = fields.Float(related="order_line_id.product_uom_qty")

    @api.depends("order_line_id.name")
    def _compute_line_name(self):
        for record in self:
            record.name = record.order_line_id.name






