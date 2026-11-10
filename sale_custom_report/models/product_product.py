# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    variant_delivery_code_selection_id = fields.Many2one('product.delivery.cost.group.code',string='Variant Delivery Code')

    variant_cbm_flatpacked = fields.Float(related='variant_delivery_code_selection_id.cbm_flatpacked',store=True, string="CBM Flatpacked")
    variant_cbm_assembled = fields.Float(related='variant_delivery_code_selection_id.cbm_assembled',store=True, string="CBM Assembled")

    variant_zone1_delivery_cost = fields.Monetary(related='variant_delivery_code_selection_id.delivery_code_cost', store=True, string="Zone 1 Delivery Cost")
    variant_zone1_installation_cost = fields.Monetary(related='variant_delivery_code_selection_id.installation_cost', store=True, string="Zone 1 Install Cost")
    zone1_total_cost = fields.Monetary(compute="_compute_zone1_total_cost",store=True, string="Zone 1 Total Cost",help="Total Cost is Sum of (Zone 1 Delivery Cost, Zone 1 Installation Cost, Product Cost)")

    # Quotation Description Fields.

    variant_quotation_dimensions = fields.Text(
        string="Variant Quotation Dimensions",
        help="This field is used to store Quotation Dimensions, which will be added in Quotation Description Field."
    )

    variant_quotation_features = fields.Text(
        string="Variant Quotation Features",
        help="This field is used to store Quotation Features, which will be added in Quotation Description Field."
    )

    variant_quotation_finishes = fields.Text(
        string="Variant Quotation Finishes",
        help="This field is used to store Quotation Finishes, which will be added in Quotation Description Field."
    )

    variant_quotation_warranty = fields.Text(
        string="Variant Quotation Warranty",
        help="This field is used to store Quotation Warranty, which will be added in Quotation Description Field."
    ) 

    variant_quotation_lead_time = fields.Text(
        string="Variant Quotation Lead Time",
        help="This field is used to store Lead Time, which will be added in Quotation Description Field."
    )

    variant_quotation_other_details = fields.Text(
        string="Variant Other Details",
        help="This field is used to store Other Details, which will be added in Quotation Description Field."
    )

    variant_description_sale = fields.Text(
        'Variant Sales Description', translate=True,
        help="A description of the Product that you want to communicate to your customers. "
             "This description will be copied to every Sales Order, Delivery Order and Customer Invoice/Credit Note",
        compute="_compute_variant_description_sale",
        store=True
    )

    description_sale = fields.Text(
        'Sales Description', translate=True,
        help="A description of the Product that you want to communicate to your customers. "
             "This description will be copied to every Sales Order, Delivery Order and Customer Invoice/Credit Note",
    )

    def get_product_multiline_description_sale(self):
        """ Compute a multiline description of this product, in the context of sales
                (do not use for purchases or other display reasons that don't intend to use "description_sale").
            It will often be used as the default description of a sale order line referencing this product.
        """
        name = self.display_name
        description = """
            """
        dimension = ""
        features = ""
        finishes = ""
        warranty = ""
        lead_time = ""
        other_details = ""
        # Making the description before computing the main field
        if self.variant_quotation_dimensions:
            dimension = f"Dimensions:\n{self.variant_quotation_dimensions}\n"
        if self.variant_quotation_features:
            features = f"Features:\n{self.variant_quotation_features}\n"
        if self.variant_quotation_finishes:
            finishes = f"Finishes:\n{self.variant_quotation_finishes}\n"
        if self.variant_quotation_warranty:
            warranty = f"Warranty:\n{self.variant_quotation_warranty}\n"
        if self.variant_quotation_lead_time:
            lead_time = f"Lead Time:\n{self.variant_quotation_lead_time}\n"
        if self.variant_quotation_other_details:
            other_details = f"Other Details:\n{self.variant_quotation_other_details}"
        
        description = f"""{dimension}{features}{finishes}{warranty}{lead_time}{other_details}"""
        if self.product_sale_type == 'burgtec':
            name += '\n' + description
        if self.product_sale_type == 'dpg':
            if self.description_sale:
                name += '\n' + self.description_sale
        return name

    @api.depends("variant_quotation_dimensions", "variant_quotation_features", "variant_quotation_finishes", "variant_quotation_warranty", "variant_quotation_lead_time", "variant_quotation_other_details")
    def _compute_variant_description_sale(self):
        for record in self:
            description = """
            """
            dimension = ""
            features = ""
            finishes = ""
            warranty = ""
            lead_time = ""
            other_details = ""
            # Making the description before computing the main field
            if record.variant_quotation_dimensions:
                dimension = f"Dimensions:\n{record.variant_quotation_dimensions}\n"
            if record.variant_quotation_features:
                features = f"Features:\n{record.variant_quotation_features}\n"
            if record.variant_quotation_finishes:
                finishes = f"Finishes:\n{record.variant_quotation_finishes}\n"
            if record.variant_quotation_warranty:
                warranty = f"Warranty:\n{record.variant_quotation_warranty}\n"
            if record.variant_quotation_lead_time:
                lead_time = f"Lead Time:\n{record.variant_quotation_lead_time}\n"
            if record.variant_quotation_other_details:
                other_details = f"Other Details:\n{record.variant_quotation_other_details}"
            
            description = f"""{dimension}{features}{finishes}{warranty}{lead_time}{other_details}"""

            record.variant_description_sale = description
            if record.product_sale_type == 'burgtec':
                record.description_sale = description
    
    def set_product_delivery_code_from_product_tmpl_id(self):
        "This Method will set Product Delivery Codes for the Variants of old data from its product template."
        for record in self:
            if record.product_tmpl_id:
                record.variant_delivery_code_selection_id = record.product_tmpl_id.delivery_code_selection_id.id
    
    @api.depends('variant_zone1_delivery_cost','variant_zone1_installation_cost','standard_price')
    def _compute_zone1_total_cost(self):
        for record in self:
            record.zone1_total_cost = record.standard_price + record.variant_zone1_delivery_cost + record.variant_zone1_installation_cost
