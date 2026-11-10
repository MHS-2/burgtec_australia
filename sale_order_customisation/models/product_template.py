from odoo import models, fields,api,_

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_variant_count = fields.Integer(
        '# Product Variants', compute='_compute_product_variant_count', store=True)