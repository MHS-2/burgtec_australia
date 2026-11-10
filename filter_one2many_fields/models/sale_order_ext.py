from odoo import models, fields, api, Command,_

Global = 0
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    group_sale_order_line_id = fields.Many2one('sale.order.line', copy=False)

    group_id_value = fields.Char(compute="_compute_group_id_value",store=True)

    @api.depends('group_sale_order_line_id')
    def _compute_group_domain(self):
        for record in self:
            if record.group_sale_order_line_id:
                return ['|',('line_group_id_value', '=', record.group_id_value),('id','=',record.group_sale_order_line_id.id)]
            else:
                return []
    
    filtered_order_line_ids = fields.One2many(
        comodel_name='sale.order.line',
        inverse_name='order_id',
        string="Filtered Order Lines",
        domain=lambda self: self._compute_group_domain(),
        auto_join=True)

    
    @api.depends('group_sale_order_line_id')
    def _compute_group_id_value(self):
        for record in self:
            if record.group_sale_order_line_id:
                record.group_id_value = str(record.group_sale_order_line_id.id)
            else:
                record.group_id_value = False
    
    @api.onchange('order_line')
    def _compute_multi_cost_per_unit(self):
        for order in self:
            if order.bom_component_id:
                # parent = False
                changed_order_lines = self.order_line.filtered(lambda l: l.product_id and ( l.product_uom_qty  != l._origin.product_uom_qty or l.price_unit != l._origin.price_unit or l.price_subtotal != l._origin.price_subtotal))
                if not changed_order_lines:
                    return
                # Need to call to update fields inside coressponding parent in bom components.
                order.bom_component_id.onchange_component_line_ids(changed_order_lines)
    



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    applied_margin = fields.Float(
        string="Margin"
    )
    





