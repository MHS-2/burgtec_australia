from odoo import models, fields, api, _

class SubAttributeLine(models.Model):
    _name='sub.attribute.line'
    _description = 'Model Lets you select sub attribute and its available values.'

    website_product_template_attribute_value_id = fields.Many2one('product.template.attribute.value')
    sub_attribute_id = fields.Many2one('sub.attribute')
    sub_attribute_value_ids = fields.Many2many('sub.attribute.value.line')
