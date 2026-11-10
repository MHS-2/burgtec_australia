from odoo import fields, models, api


class SaleOrderBomComponentExt(models.Model):
    _inherit = 'sale.order.bom.component'


class SaleOrderBomComponentLinesExt(models.Model):
    _inherit = 'sale.order.bom.component.line'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    unit_margin = fields.Monetary(
        string="Unit Margin($)",
        currency_field='currency_id',
        compute='_compute_unit_margin',
    )

    @api.depends('margin_live_cost', 'product_qty', 'is_parent')
    def _compute_unit_margin(self):
        for line in self:
            if line.is_parent and line.product_qty:
                line.unit_margin = line.margin_live_cost / line.product_qty
            else:
                line.unit_margin = 0.0