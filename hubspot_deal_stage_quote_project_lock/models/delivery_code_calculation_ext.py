from odoo import fields, models,api, _

class DeliveryCodeCalculationExt(models.Model):
    _inherit = 'delivery.code.calculation'


    freeze_sale_order = fields.Boolean(string='Freeze Sale Order', related='order_id.freeze_sale_order', store=True)
    quote_type = fields.Selection(related='order_id.quote_type', store=True)
