from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SubAttribute(models.Model):
    _name='sub.attribute'
    _description = "Sub Attribute For Attribute Values."

    name = fields.Char()
    sub_attribute_value_line_ids = fields.One2many('sub.attribute.value.line','sub_attribute_id')
    display_type = fields.Selection(
        [
            ('radio','Radio'),
            ('pills', 'Pills'),
            ('select', 'Select'),
            ('color','Color'),
            ('multi','Multi-checkbox')
        ], default="radio"
    )

    sub_attribute_type_id = fields.Many2one('sub.attribute.type')

    def write(self, vals):
        # """Override to make sure attribute type can't be changed if it's used on
        # a product template.

        # This is important to prevent because changing the type would make
        # existing combinations invalid without recomputing them, and recomputing
        # them might take too long and we don't want to change products without
        # the user knowing about it."""

        invalidate = 'sequence' in vals and any(record.sequence != vals['sequence'] for record in self)
        res = super().write(vals)
        if invalidate:
            # prefetched o2m have to be resequenced
            # (eg. product.template: attribute_line_ids)
            self.env.flush_all()
            self.env.invalidate_all()
        return res

class SubAttributeType(models.Model):
    _name='sub.attribute.type'
    _description="Model used relate sub attribute to this model."

    name= fields.Char()
    