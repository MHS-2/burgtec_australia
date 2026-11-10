from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleOrderSeries(models.Model):
    _name = 'sale.order.series'
    _description = 'Sale Order Series'
    _rec_name = 'id'

    sequence = fields.Integer(string="Sequence")
    starting_value = fields.Integer(string="Starting Value")
    ending_value = fields.Integer(string="Ending Value")

    # New zeland Customisation
    currency_id = fields.Many2one('res.currency')
    pricelist_ids = fields.Many2many('product.pricelist')
    

