from odoo import models, fields, api, _

class PreconfiguredAttributeLine(models.Model):
    _name= 'preconfigured.attribute.line'
    _description = "Model For Variants To Select Sub attribute value for allocation area if variant is preconfigured."
    
    product_id = fields.Many2one('product.product')
    product_template_attribute_value_id = fields.Many2one('product.template.attribute.value', ondelete='cascade')
    material_allocation = fields.Char(string='Material Allocation Char')
    material_allocation_id = fields.Many2one('material.allocation')
    sub_attribute_id = fields.Many2one('sub.attribute')
    sub_attribute_value_ids = fields.Many2many('sub.attribute.value.line')
    sub_attribute_line_id = fields.Many2one('sub.attribute.line', ondelete='cascade') # <----- Lines from this model are used to create vals, storing the id for recomputation logic