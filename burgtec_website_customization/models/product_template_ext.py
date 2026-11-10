from odoo import models, fields, api


class ProductTemplateExt(models.Model):
    _inherit = 'product.template'

    api_template_product_name = fields.Char(
        string="Product Name",
        compute="_compute_api_template_product_fields",
        store=True,
        readonly=False
    )
    api_template_default_code = fields.Char(
        string="Template Internal Reference",
        compute="_compute_api_template_product_fields",
        store=True,
        readonly=False
    )
    api_template_categ_id = fields.Many2one(
        'product.category',
        string="Category"
    )
    api_template_custom_categ_id = fields.Many2one(
        'website.product.category',
        string="Website Category"
    )
    api_template_list_price = fields.Float(string="Template Sales Price")
    api_template_quotation_lead_time = fields.Char(string="Template Quotation Lead Time")
    api_template_weight = fields.Float(string="Template Weight")
    api_template_weight_uom_name = fields.Char(string="Template Weight UoM", readonly=True)
    api_template_volume = fields.Float(string="Template Volume")
    api_template_volume_uom_name = fields.Char(string="Template Volume UoM", readonly=True)
    # api_template_description_sale = fields.Text(string="Website Description", compute="_compute_api_description_sale",store=True)
    api_template_brand = fields.Char(string="Brand")
    api_template_taxes_id = fields.Many2one('account.tax',
                                            string='Template Customer Taxes', domain=[('type_tax_use', '!=', 'purchase')])

    api_template_image_attachment_ids = fields.Many2many(
        'ir.attachment',
        'product_api_template_image_rel',
        'product_id',
        'attachment_id',
        string="Image Attachments"
    )
    api_template_three_d_attachment_ids = fields.Many2many(
        'ir.attachment',
        'product_api_template_3d_rel',
        'product_id',
        'attachment_id',
        string="3D Configurator Attachments"
    )
    api_template_docs_attachment_ids = fields.Many2many(
        'ir.attachment',
        'product_api_template_docs_rel',
        'product_id',
        'attachment_id',
        string="Docs Attachments"
    )

    is_product_published = fields.Boolean(default=False)

    is_modular_template_product = fields.Boolean(default=False, string='Is Modular Template Product')
    is_purchasable_online_template = fields.Boolean(default=False, string='Is Purchasable Online Template')


        # website Description Fields.

    api_website_dimensions = fields.Text(
        string="Website Dimensions",
        help="This field is used to store Website Dimensions, which will be added in Website Description Field."
    )

    api_website_features = fields.Text(
        string="Website Features",
        help="This field is used to store Website Features, which will be added in Website Description Field."
    )

    api_website_finishes = fields.Text(
        string="Website Finishes",
        help="This field is used to store Website Finishes, which will be added in Website Description Field."
    )

    api_website_warranty = fields.Text(
        string="Website Warranty",
        help="This field is used to store Website Warranty, which will be added in Website Description Field."
    ) 

    api_website_lead_time = fields.Text(
        string="Website Lead Time",
        help="This field is used to store Lead Time, which will be added in Website Description Field."
    )

    api_website_description = fields.Text(
        string="Website Description",
        help="This field is used to store Other Details, which will be added in Website Description Field."
    )

    api_website_product_origin = fields.Char()

    api_template_featured_attachment_ids = fields.Many2many(
        'ir.attachment',
        'product_api_template_featured_rel',
        'product_id',
        'attachment_id',
        string="Featured Images"
    )

    # api_zone_postal_id = fields.Many2one('zone.postal')
    api_template_delivery_code_selection_id = fields.Many2one('product.delivery.cost.group.code',string='API Template Delivery Code Selections')


    api_template_unit = fields.Selection([
        ('1','1'),
        ('2','2')
        ], default="1"
    )

    optional_group_ids = fields.One2many('optional.groups.line','product_template_id')

    api_template_height = fields.Char()
    api_template_width = fields.Char()
    api_template_depth = fields.Char()

    api_template_worktop_height = fields.Char()
    api_template_worktop_width = fields.Char()

    api_template_seat_height = fields.Char()
    api_template_seat_depth = fields.Char()
    api_template_seat_width = fields.Char()




    @api.depends("name", "default_code")
    def _compute_api_template_product_fields(self):
        for template in self:
            if not template.api_template_product_name:
                template.api_template_product_name = template.name
            if not template.api_template_default_code:
                template.api_template_default_code = template.default_code


