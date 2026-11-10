from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderAreaAllocation(models.Model):
    _name = 'sale.order.area.allocation'
    _description = 'Sale Order Area Allocation'
    _rec_name = 'product_id'

    order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    area_id = fields.Many2one(
        'sale.order.area',
        string='Area',
        required=True,
        ondelete='cascade',
        index=True,
    )
    product_template_id = fields.Many2one(
        'product.template',
        string='Product Template',
        ondelete='cascade',
        index=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        ondelete='cascade',
        index=True,
    )
    allocated_qty = fields.Float(
        string='Allocated Quantity',
        default=0.0,
        digits='Product Unit of Measure'
    )

    order_line_id = fields.Many2one('sale.order.line',ondelete='cascade',index=True,)

    _sql_constraints = [
        (
            'unique_allocation',
            'UNIQUE(order_id, area_id, product_template_id)',
            'An allocation already exists for this product template and area.',
        ),
    ]

    @api.constrains('allocated_qty')
    def _check_allocated_qty(self):
        for alloc in self:
            if alloc.allocated_qty < 0:
                raise ValidationError(
                    _('Allocated quantity cannot be negative.')
                )
