import logging

from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class ProductProductExt(models.Model):
    _inherit = 'product.product'

    # product_bom_type = fields.Selection(
    #     related='product_tmpl_id.product_bom_type',
    #     string='Product Type',
    #     readonly=True,
    #     store=True
    # )
    variant_bom_type = fields.Selection([
        ('product', 'Product'),
        ('components', 'Components')
    ], string='Burgtec Product Variant Type', compute="_compute_variant_bom_type", inverse="_set_tmpl_bom_type",
        store=True, readonly=False, required=True)

    fabric_meterage = fields.Float('Fabric Meterage')

    external_id_computed = fields.Char(string="Computed External ID", compute="_compute_external_id")

    old_product_variant_eid = fields.Char(string="Old Variant E.ID")
    old_product_variant_name = fields.Char(string="Old Variant Name")

    is_delivery_and_installation = fields.Boolean('Delivery/Installation', default=False)

    product_sale_type = fields.Selection([
        ('burgtec', 'Burgtec'),
        ('dpg', 'DPG'),
    ], compute="compute_product_sale_type", inverse="_set_product_tmpl_product_sale_type", required=True,
        readonly=False, store=True)

    product_certification_ids = fields.Many2many('product.certification', string="Certifications")

    def _compute_external_id(self):
        for record in self:
            record.external_id_computed = record.get_metadata()[0].get('xmlid')

    def action_update_product_product_cost(self):
        for product in self:
            if product.bom_ids:
                for bom in product.bom_ids:
                    if bom.product_id.id == product.id:
                        product.standard_price = bom.bom_cost

    @api.depends('product_tmpl_id.product_bom_type')
    def _compute_variant_bom_type(self):
        for record in self:
            product_template = record.product_tmpl_id
            if product_template:
                _logger.info('Current Variant Of Id %d BOM Type -----> %s', record.id, record.variant_bom_type)
                record.variant_bom_type = product_template.product_bom_type
                _logger.info('Variant of Id %d BOM Type Updated To -----> %s', record.id, record.variant_bom_type)
            else:
                record.variant_bom_type = False

    def _set_tmpl_bom_type(self):
        for rec in self:
            rec.product_tmpl_id.product_bom_type = rec.variant_bom_type

    @api.depends('product_tmpl_id.product_sale_type')
    def compute_product_sale_type(self):
        for record in self:
            product_template = record.product_tmpl_id
            if product_template:
                record.product_sale_type = product_template.product_sale_type
            else:
                record.product_sale_type = False

    def _set_product_tmpl_product_sale_type(self):
        for rec in self:
            rec.product_tmpl_id.product_sale_type = rec.product_sale_type

    def _set_image_1920(self):
        """Store the image on the variant itself when the template has
        several variants, instead of pushing it to the template."""
        multi = self.filtered(lambda p: p.product_tmpl_id.product_variant_count > 1)
        for rec in multi:
            rec.image_variant_1920 = rec.image_1920
        return super(ProductProductExt, self - multi)._set_image_1920()
