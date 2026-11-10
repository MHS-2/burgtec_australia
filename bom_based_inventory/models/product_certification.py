from random import randint
from odoo import models, fields

class ProductCertification(models.Model):
    _name = 'product.certification'
    _description = 'Product Certification'

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(string='Certification Name')
    description = fields.Char(string='Description')
    certification_logo = fields.Binary(string='Certification Logo')
    active = fields.Boolean(string='Is Active', default=True)
    color = fields.Integer(string="Color Index", default=_get_default_color)


