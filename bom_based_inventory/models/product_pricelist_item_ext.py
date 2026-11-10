from odoo import models, fields, api, _

class ProductPricelistItemExt(models.Model):
    _inherit="product.pricelist.item"

    manual_cost = fields.Float()