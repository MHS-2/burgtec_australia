from odoo import models, fields

class WebsiteProductCategory(models.Model):
    _name = 'website.product.category'
    _description = 'Website Product Category'

    name = fields.Char(required=True, translate=True)
    parent_id = fields.Many2one('website.product.category', string='Parent Category', index=True, ondelete='cascade')

    def _compute_display_name(self):
        for record in self:
            if record.parent_id:
                if not record.parent_id.parent_id:
                    record.display_name = f'{record.parent_id.name} / {record.name}'
                else:
                    record.display_name = f'{record.parent_id.display_name} / {record.name}'
            elif not record.parent_id:
                record.display_name = f'{record.name}'
            else:
                return super(WebsiteProductCategory,self)._compute_display_name()
