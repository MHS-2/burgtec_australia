from odoo import models, fields, api, _

class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    attribute_website_name = fields.Char(string="Website Name", compute="_compute_attribute_website_name", store=True, readonly=False)

    def _compute_attribute_website_name(self):
        for record in self:
            attribute_name = record.name
            if attribute_name:
                record.attribute_website_name = attribute_name