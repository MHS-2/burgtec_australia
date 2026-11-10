from odoo import api, models, fields, _

class ProductTemplateExt(models.Model):
    _inherit = 'product.template'



    custom_product_description = fields.Text(
        string='Product Description',
        help='This field is used to store a description for the product, which can be used in reports or other contexts where a specific description is needed.'
    )

    # Quotation Description Fields.

    quotation_dimensions = fields.Text(
        string="Quotation Dimensions",
        help="This field is used to store Quotation Dimensions, which will be added in Quotation Description Field."
    )

    quotation_features = fields.Text(
        string="Quotation Features",
        help="This field is used to store Quotation Features, which will be added in Quotation Description Field."
    )

    quotation_finishes = fields.Text(
        string="Quotation Finishes",
        help="This field is used to store Quotation Finishes, which will be added in Quotation Description Field."
    )

    quotation_warranty = fields.Text(
        string="Quotation Warranty",
        help="This field is used to store Quotation Warranty, which will be added in Quotation Description Field."
    ) 

    quotation_lead_time = fields.Text(
        string="Quotation Lead Time",
        help="This field is used to store Lead Time, which will be added in Quotation Description Field."
    )

    quotation_other_details = fields.Text(
        string="Other Details",
        help="This field is used to store Other Details, which will be added in Quotation Description Field."
    )

    delivery_code_selection_id = fields.Many2one('product.delivery.cost.group.code',string='Template Delivery Code Selections')

    cbm_flatpacked = fields.Float(related='delivery_code_selection_id.cbm_flatpacked',store=True, string='Template CBM Flatpacked')
    cbm_assembled = fields.Float(related='delivery_code_selection_id.cbm_assembled',store=True, string='Template CBM Assembled')

