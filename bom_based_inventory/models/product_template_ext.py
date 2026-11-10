from email.policy import default

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError, AccessError


class ProductTemplateExtExt(models.Model):
    _inherit = 'product.template'

    product_bom_type = fields.Selection([
        ('product', 'Product'),
        ('components', 'Components')
    ], string='Burgtec Product Template Type')

    is_old_data = fields.Boolean(default=False)

    external_id_computed = fields.Char(string="Computed External ID", compute="_compute_external_id")

    old_product_template_eid = fields.Char(string="Old Product E.ID")
    old_product_template_name = fields.Char(string="Old Product Name")

    is_delivery_and_installation = fields.Boolean('Delivery/Installation', default=False)

    product_pricing_category = fields.Text('Product Pricing Category')

    product_sale_type = fields.Selection([
        ('burgtec','Burgtec'),
        ('dpg','DPG'),
    ],required=True)

    def _compute_external_id(self):
        for record in self:
            record.external_id_computed = record.get_metadata()[0].get('xmlid')

    @api.onchange('product_bom_type')
    def _set_routes(self):
        for record in self:
            dropship_route = record.env.ref('stock_dropshipping.route_drop_shipping')
            dropship_subcontractor_route = record.env.ref(
                'mrp_subcontracting_dropshipping.route_subcontracting_dropshipping')
            if record.product_bom_type:
                if record.product_bom_type == 'product':
                    record.route_ids = [(5, 0, 0)]
                    record.route_ids = [(4, dropship_route.id, 0)]
                if record.product_bom_type == 'components':
                    record.route_ids = [(5, 0, 0)]
                    record.route_ids = [(4, dropship_subcontractor_route.id, 0)]

    # def write(self, vals):
    #     current_user = self.env.user
    #     if not current_user.has_group("bom_based_inventory.group_product_manager"):
    #         raise AccessError(_("Only Product Managers Can Edit Products."))
    #     return super(ProductTemplateExtExt, self).write(vals)

    # def web_save(self, vals, specification: dict[str, dict], next_id=None) -> list[dict]:
    #     if self:
    #         if not self.env.user.has_group("bom_based_inventory.group_product_manager"):
    #             raise AccessError(_("Only Product Managers Can Edit Products."))
    #     return super(ProductTemplateExtExt, self).web_save(vals, specification)

    def unlink(self):
        current_user = self.env.user
        if not current_user.has_group("bom_based_inventory.group_product_manager"):
            raise AccessError(_("Only Product Managers Can Delete Products."))
        return super(ProductTemplateExtExt, self).unlink()


    def set_old_data_true(self):
        for record in self:
            record.is_old_data = True

    def action_update_product_template_cost(self):
        for product in self:
            if product.bom_ids:
                total_bom_cost = sum(bom.bom_cost for bom in product.bom_ids)
                product.standard_price = total_bom_cost
