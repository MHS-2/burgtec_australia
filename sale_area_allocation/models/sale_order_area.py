from odoo import api, fields, models


class SaleOrderArea(models.Model):
    _name = 'sale.order.area'
    _description = 'Sale Order Area'
    _order = 'sequence, id'

    order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(
        string='Area Name',
        required=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    allocation_ids = fields.One2many(
        'sale.order.area.allocation',
        'area_id',
        string='Allocations'
    )

    parent_area = fields.Char()
