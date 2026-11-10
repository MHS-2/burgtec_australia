from odoo import models, fields, api, _, Command

class PreconfiguredAttributeOption(models.Model):
    _name = 'preconfigured.attribute.option'
    _description = 'Preconfigured Attribute Option'
    
    name = fields.Char()
    option_image_attachment_ids = fields.Many2many(
        'ir.attachment',  # related model
        'preconfigured_option_image_rel',  # relation table name
        'option_id',  # column referring to this model
        'attachment_id',  # column referring to ir.attachment
        string="Option Image Attachments",
        help="Image Attachments."
    )
    preconfigured_option_line_ids = fields.One2many('preconfigured.option.line','preconfigured_attribute_option_id')

class PreconfiguredOptionLine(models.Model):
    _name='preconfigured.option.line'
    _description = 'Preconfigured Option Line'



    preconfigured_attribute_option_id = fields.Many2one('preconfigured.attribute.option' , ondelete='cascade')
    product_template_attribute_value_id = fields.Many2one('product.template.attribute.value')
    material_allocation = fields.Char(string='Material Allocation Char')
    material_allocation_id = fields.Many2one('material.allocation')
    sub_attribute_id = fields.Many2one('sub.attribute')
    sub_attribute_value_ids = fields.Many2many('sub.attribute.value.line')
    # sub_attribute_line_id = fields.Many2one('sub.attribute.line')
