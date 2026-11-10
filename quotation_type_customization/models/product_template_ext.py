from odoo import fields, models, _
from odoo.exceptions import AccessError

class ProductTemplateExt(models.Model):
    _inherit = 'product.template'


    def write(self, vals):
        current_user = self.env.user
        if 'active' in vals and vals['active'] is False:
            if not current_user.has_group("product.group_product_manager"):
                raise AccessError(_("Only Product Managers Can Archive Products."))
        return super(ProductTemplateExt, self).write(vals)


class ProductProductExt(models.Model):
    _inherit = 'product.product'


    def write(self, vals):
        current_user = self.env.user
        if 'active' in vals and vals['active'] is False:
            if not current_user.has_group("product.group_product_manager"):
                raise AccessError(_("Only Product Managers Can Archive Products."))
        return super(ProductProductExt, self).write(vals)








