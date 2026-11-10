from odoo import models, fields, api, _

class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    sub_attribute_line_ids = fields.One2many('sub.attribute.line','website_product_template_attribute_value_id')
    three_d_attachment_ids = fields.Many2many(
        'ir.attachment',
        string="3D Configurator Attachments"
    )
    material_allocation = fields.Char(string='Material Allocation Char')

    material_allocation_id = fields.Many2one('material.allocation')