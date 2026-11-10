from odoo import _, models
from odoo.exceptions import AccessError

ALLOWED_IMAGE_FIELDS = {
    "image_1920", "image_1024", "image_512", "image_256", "image_128",
    "image_variant_1920", "image_variant_1024", "image_variant_512",
    "image_variant_256", "image_variant_128",
    "write_date", "write_uid",
}

class ProductTemplateExt(models.Model):
    _inherit = "product.template"


    # i have commented the web_save in bom_based_inventory module because now
    # we have an other group to only update the images thats
    # why now we will check both group before raising an access error

    def web_save(self, vals, specification: dict[str, dict], next_id=None) -> list[dict]:
        if self:
            current_user = self.env.user
            if not current_user.has_group("bom_based_inventory.group_product_manager") and not current_user.has_group("burgtec_hubspot_customization.group_product_image_editor"):
                raise AccessError(_("Only Product Managers Can Edit Products."))
        return super(ProductTemplateExt, self).web_save(vals, specification)

    def write(self, vals):
        if not self.env.su and self.env.user.has_group("burgtec_hubspot_customization.group_product_image_editor"):
            for field in vals:
                if field not in ALLOWED_IMAGE_FIELDS:
                    raise AccessError(
                        _("You can only edit product images.")
                    )

        return super().write(vals)

class ProductProductExt(models.Model):
    _inherit = "product.product"

    def write(self, vals):
        if not self.env.su and self.env.user.has_group("burgtec_hubspot_customization.group_product_image_editor"):
            for field in vals:
                if field not in ALLOWED_IMAGE_FIELDS:
                    raise AccessError(
                        _("You can only edit product images.")
                    )

        return super().write(vals)