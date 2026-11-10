from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class SubAttributeValueLine(models.Model):
    _name='sub.attribute.value.line'
    _description = "Sub Attributes Value Lines For Sub Attributes."
    _order = 'sub_attribute_id, sequence, id'

    name = fields.Char(string="Value")
    html_color = fields.Char(
        string="Color",
        help="Here you can set a specific HTML color index (e.g. #ff0000)"
            " to display the color if the attribute type is 'Color'.")
    sub_attribute_id = fields.Many2one('sub.attribute')
    image = fields.Image(
        string="Thumbnail Image",
        help="You can upload an image that will be used as the color of the attribute value.",
        max_width=70,
        max_height=70,
    )
    texture_image = fields.Image(
        string="Texture Image",
        help="You can upload an image that will be used as texture.",
    )
    lead_time = fields.Char(string="Lead Time")

    default_extra_price = fields.Float()

    roughness = fields.Float(digits=(16,1))
    metalness = fields.Float(digits=(16,1))

    is_default_website = fields.Boolean(default=False)

    sequence = fields.Integer(string="Sequence", help="Determine the display order", index=True)

    @api.constrains('is_default_website')
    def check_is_default_website(self):
        for record in self:
            sub_attribute_obj = record.sub_attribute_id
            lines_already_true = record.env['sub.attribute.value.line'].sudo().search_count([('sub_attribute_id','=',sub_attribute_obj.id),('is_default_website','=',True)])
            if lines_already_true > 1:
                raise ValidationError('Only One Sub Attribute Value Line At a time, can be Set As Default for website!')
    

    
    # === CRUD METHODS === #

    def write(self, vals):
        print("-----> EXECTUED WRITE METHOD ON LINE LEVEL <---------")

        invalidate = 'sequence' in vals and any(record.sequence != vals['sequence'] for record in self)
        res = super().write(vals)
        if invalidate:
            # prefetched o2m have to be resequenced
            # (eg. product.template.attribute.line: value_ids)
            self.env.flush_all()
            self.env.invalidate_all()
        return res


    


    