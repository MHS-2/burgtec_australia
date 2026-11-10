import json
import logging
from odoo import http, _
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class ProductController(http.Controller):

    def _get_attachments(self, attachment_records):
        """
        Helper method to process attachment records into standardized format
        Args:
            attachment_records: recordset of ir.attachment
        Returns:
            list: List of attachment dictionaries with id, name, mimetype, file_url
        """
        attachments = []
        for attach in attachment_records:
            if not attach.public:
                attach.public = True
            attachment_url = f"{request.httprequest.host_url}web/content/{attach.id}?download=true"
            attachments.append({
                'id': attach.id,
                'name': attach.name,
                'mimetype': attach.mimetype,
                'file_url': attachment_url
            })
        return attachments

    @http.route("/api/products/published/search", type='json', auth='public', csrf=False, cors='*')
    def get_product_with_params(self, **kwargs):
        domain = [(key, '=', value) for key, value in kwargs.items()]
        try:
            base_url = request.httprequest.host_url
            product_template_object = request.env['product.template']
            published_product_with_params = product_template_object.sudo().search(domain)
            if not published_product_with_params:
                return {
                    'status': 'success',
                    'count': 0,
                    'message': 'No products available to fetch',
                    'data': []
                }

            products_data = []

            for template in published_product_with_params:
                # Basic template data
                template_data = {
                    'id': template.id,
                    'product_origin': template.api_website_product_origin,
                    'name': template.api_template_product_name,
                    'image_url': f"{base_url}web/image/product.template/{template.id}/image_1920",
                    'default_code': template.api_template_default_code,
                    'parent_category': template.api_template_custom_categ_id.parent_id.display_name,
                    'child_category': template.api_template_custom_categ_id.name,
                    'sale_price': template.api_template_list_price,
                    'customer_tax': template.api_template_taxes_id.name,
                    'is_modular_template_product': template.is_modular_template_product,
                    'is_purchasable_online_template': template.is_purchasable_online_template,
                    # 'lead_time': template.api_template_quotation_lead_time,
                    'brand': template.api_template_brand,
                    # 'weight': template.weight,
                    # 'volume': template.api_template_volume,
                    'type': 'template',
                    'unit': template.api_template_unit,
                }

                if template.api_website_description:
                    template_data['description'] = template.api_website_description
                if template.api_website_dimensions:
                    template_data['dimensions'] = template.api_website_dimensions
                if template.api_website_finishes:
                    template_data['finishes'] = template.api_website_finishes
                if template.api_website_features:
                    template_data['features'] = template.api_website_features
                if template.api_website_warranty:
                    template_data['warranty'] = template.api_website_warranty
                if template.api_website_lead_time:
                    template_data['lead_time'] = template.api_website_lead_time

                if template.api_template_image_attachment_ids:
                    template_data['image_attachments'] = self._get_attachments(
                        template.api_template_image_attachment_ids)

                if template.api_template_docs_attachment_ids:
                    template_data['docs_attachments'] = self._get_attachments(template.api_template_docs_attachment_ids)

                if template.api_template_featured_attachment_ids:
                    template_data['featured_attachments'] = self._get_attachments(
                        template.api_template_featured_attachment_ids)


                api_template_delivery_code_selection = template.api_template_delivery_code_selection_id
                if api_template_delivery_code_selection:
                    # Delivery Cost
                    zone1_delivery_cost = api_template_delivery_code_selection.delivery_code_cost
                    zone2_delivery_cost = api_template_delivery_code_selection.zone2_delivery_cost
                    zone3_delivery_cost = api_template_delivery_code_selection.zone3_delivery_cost

                    # Installation Cost
                    zone1_installation_cost = api_template_delivery_code_selection.installation_cost
                    zone2_installation_cost = api_template_delivery_code_selection.zone2_installation_cost
                    zone3_installation_cost = api_template_delivery_code_selection.zone3_installation_cost

                    # Postal Code
                    zone_postal_obj = request.env['zone.postal'].search([], limit=1)
                    zone1_postal_codes = zone_postal_obj.zone1_postal_code_ids.mapped('name')
                    zone2_postal_codes = zone_postal_obj.zone2_postal_code_ids.mapped('name')
                    zone3_postal_codes = zone_postal_obj.zone3_postal_code_ids.mapped('name')

                    # Website minimum
                    zone1_website_minimum = api_template_delivery_code_selection.zone1_website_minimum
                    zone2_website_minimum = api_template_delivery_code_selection.zone2_website_minimum
                    zone3_website_minimum = api_template_delivery_code_selection.zone3_website_minimum

                    # Website Sales Price
                    zone1_website_sales_price = api_template_delivery_code_selection.zone1_website_sale_price
                    zone2_website_sales_price = api_template_delivery_code_selection.zone2_website_sale_price
                    zone3_website_sales_price = api_template_delivery_code_selection.zone3_website_sale_price

                    zone_data = {
                        'zone1': {
                            'postal_codes': zone1_postal_codes,
                            # 'delivery_cost': zone1_delivery_cost,
                            # 'installation_cost': zone1_installation_cost,
                            'website_minimum': zone1_website_minimum,
                            'website_sales_price': zone1_website_sales_price,
                        },
                        'zone2': {
                            'postal_codes': zone2_postal_codes,
                            # 'delivery_cost': zone2_delivery_cost,
                            # 'installation_cost': zone2_installation_cost,
                            'website_minimum': zone2_website_minimum,
                            'website_sales_price': zone2_website_sales_price,
                        },
                        'zone3': {
                            'postal_codes': zone3_postal_codes,
                            # 'delivery_cost': zone3_delivery_cost,
                            # 'installation_cost': zone3_installation_cost,
                            'website_minimum': zone3_website_minimum,
                            'website_sales_price': zone3_website_sales_price,
                        }
                    }
                    if zone_data:
                        template_data['zone_postal_data'] = zone_data


                optional_group_lines = request.env['optional.groups.line']
                optional_groups = optional_group_lines.sudo().search([('product_template_id', '=', template.id),('is_publish','=',True)])
                optional_group_list = []
                display_vals = {}
                group_vals = {}
                if optional_groups:
                    for line in optional_groups:
                        group_vals['group_name'] = line.optional_group_id.name
                        group_vals['website_name'] = line.website_name
                        group_vals['products'] = line.product_ids.mapped('name') if line.product_ids else False
                        display_vals[line.name] = group_vals
                        optional_group_list.append(display_vals)
                        group_vals = {}
                        display_vals = {}
                        
                if optional_group_list:
                    template_data['optional_groups_data'] = optional_group_list


                total_attribute_values = []
                if template.attribute_line_ids:
                    for attribute_line in template.attribute_line_ids:
                        for val in attribute_line.value_ids:
                            total_attribute_values.append(val.name)
                    if total_attribute_values:
                        template_data['all_attribute_values'] = total_attribute_values

                template_data['variants'] = []

                # Get published variants for this template
                published_variants = request.env['product.product'].sudo().search([
                    ('product_tmpl_id', '=', template.id),
                    ('is_product_published', '=', True)
                ])
                if template.attribute_line_ids:
                    for variant in published_variants:
                        # Get variant attributes
                        variant_attributes = []
                        sub_attribute_data = []
                        sub_attribute_value_data = []
                        for attribute_value in variant.product_template_attribute_value_ids:

                            if attribute_value.sub_attribute_line_ids:
                                for sub_attribute_line in attribute_value.sub_attribute_line_ids:
                                    sub_attribute_vals = {
                                        'sub_attribute_id': sub_attribute_line.sub_attribute_id.id,
                                        'sub_attribute_name': sub_attribute_line.sub_attribute_id.name,
                                        'sub_attribute_display_type': sub_attribute_line.sub_attribute_id.display_type,
                                        'sub_attribute_type':sub_attribute_line.sub_attribute_id.sub_attribute_type_id.name
                                    }
                                    if sub_attribute_line.sub_attribute_value_ids:
                                        for sub_attribute_value in sub_attribute_line.sub_attribute_value_ids:
                                            value_data = {
                                                'id': sub_attribute_value.id,
                                                'name': sub_attribute_value.name,
                                                'lead_time': sub_attribute_value.lead_time,
                                                'default_for_website': sub_attribute_value.is_default_website,
                                                'extra_price': sub_attribute_value.default_extra_price,
                                                'metalness': sub_attribute_value.metalness,
                                                'roughness': sub_attribute_value.roughness
                                            }
                                            if sub_attribute_value.sub_attribute_id.display_type == 'color':
                                                value_data[
                                                    'color'] = sub_attribute_value.html_color if sub_attribute_value.html_color else False
                                                value_data['image_url'] = (
                                                    f"{base_url}web/image/sub.attribute.value.line/{sub_attribute_value.id}/image"
                                                    if sub_attribute_value.image
                                                    else False
                                                )
                                            value_data['texture_image_url'] = (
                                                f"{base_url}web/image/sub.attribute.value.line/{sub_attribute_value.id}/texture_image"
                                                if sub_attribute_value.texture_image
                                                else False
                                            )
                                            sub_attribute_value_data.append(value_data)
                                            value_data = {}
                                        sub_attribute_vals['sub_attribute_values'] = sub_attribute_value_data
                                        sub_attribute_data.append(sub_attribute_vals)
                                        sub_attribute_value_data = []
                            attribute_data = {
                                'attribute_id': attribute_value.attribute_id.id,
                                'attribute_name': attribute_value.attribute_id.attribute_website_name,
                                'value_id': attribute_value.product_attribute_value_id.id,
                                'value_name': attribute_value.product_attribute_value_id.name,
                                'material_allocation': attribute_value.material_allocation_id.name,
                                # 'sub_attribute_details': sub_attribute_data
                            }
                            if attribute_value.three_d_attachment_ids:
                                attribute_data['attribute_value_three_d_attachments'] = self._get_attachments(
                                    attribute_value.three_d_attachment_ids)
                            if sub_attribute_data:
                                attribute_data['sub_attribute_details'] = sub_attribute_data
                            variant_attributes.append(attribute_data)
                            sub_attribute_data = []
                        # Create variant data with attributes
                        variant_data = {
                            'id': variant.id,
                            'website_name': variant.api_variant_website_name,
                            'image_url': f"{base_url}web/image/product.product/{variant.id}/image_1920",
                            # 'default_code': variant.api_variant_default_code,
                            'type': 'variant',
                            'unit': variant.api_variant_unit,
                            'variant_attribute_values': variant.product_template_attribute_value_ids.mapped('name'),
                            'is_preconfigured': variant.is_preconfigured,
                            'is_modular_variant_product': variant.is_modular_variant_product,
                            'is_purchasable_online_variant': variant.is_purchasable_online_variant,

                        }
                        api_variant_delivery_code_selection = variant.api_variant_delivery_code_selection_id
                        if api_variant_delivery_code_selection:
                            # Delivery Cost
                            zone1_delivery_cost = api_variant_delivery_code_selection.delivery_code_cost
                            zone2_delivery_cost = api_variant_delivery_code_selection.zone2_delivery_cost
                            zone3_delivery_cost = api_variant_delivery_code_selection.zone3_delivery_cost

                            # Installation Cost
                            zone1_installation_cost = api_variant_delivery_code_selection.installation_cost
                            zone2_installation_cost = api_variant_delivery_code_selection.zone2_installation_cost
                            zone3_installation_cost = api_variant_delivery_code_selection.zone3_installation_cost

                            # Postal Code
                            zone_postal_obj = request.env['zone.postal'].search([], limit=1)
                            zone1_postal_codes = zone_postal_obj.zone1_postal_code_ids.mapped('name')
                            zone2_postal_codes = zone_postal_obj.zone2_postal_code_ids.mapped('name')
                            zone3_postal_codes = zone_postal_obj.zone3_postal_code_ids.mapped('name')

                            # Website minimum
                            zone1_website_minimum = api_variant_delivery_code_selection.zone1_website_minimum
                            zone2_website_minimum = api_variant_delivery_code_selection.zone2_website_minimum
                            zone3_website_minimum = api_variant_delivery_code_selection.zone3_website_minimum

                            # Website Sales Price
                            zone1_website_sales_price = api_variant_delivery_code_selection.zone1_website_sale_price
                            zone2_website_sales_price = api_variant_delivery_code_selection.zone2_website_sale_price
                            zone3_website_sales_price = api_variant_delivery_code_selection.zone3_website_sale_price

                            variant_zone_data = {
                                'zone1': {
                                    'postal_codes': zone1_postal_codes,
                                    # 'delivery_cost': zone1_delivery_cost,
                                    # 'installation_cost': zone1_installation_cost,
                                    'website_minimum': zone1_website_minimum,
                                    'website_sales_price': zone1_website_sales_price,
                                },
                                'zone2': {
                                    'postal_codes': zone2_postal_codes,
                                    # 'delivery_cost': zone2_delivery_cost,
                                    # 'installation_cost': zone2_installation_cost,
                                    'website_minimum': zone2_website_minimum,
                                    'website_sales_price': zone2_website_sales_price,
                                },
                                'zone3': {
                                    'postal_codes': zone3_postal_codes,
                                    # 'delivery_cost': zone3_delivery_cost,
                                    # 'installation_cost': zone3_installation_cost,
                                    'website_minimum': zone3_website_minimum,
                                    'website_sales_price': zone3_website_sales_price,
                                }
                            }
                            if variant_zone_data:
                                variant_data['variant_zone_postal_data'] = variant_zone_data


                        if variant.api_variant_list_price:
                            variant_data['sales_price'] = variant.api_variant_list_price

                        if variant.api_variant_three_d_attachment_ids:
                            variant_data['variant_three_d_attachments'] = self._get_attachments(
                                variant.api_variant_three_d_attachment_ids)
                        if variant_attributes:
                            variant_data['attributes'] = variant_attributes

                        preconfigured_data = []
                        preconfigured_line_values = {}
                        option_data = []
                        option_vals = {}
                        if variant.is_preconfigured:
                            if not variant.preconfigured_attribute_option_ids and not variant.preconfigured_attribute_option_ids:
                                preconfigured_line_values['options'] = False
                                preconfigured_data.append(preconfigured_line_values)
                                preconfigured_line_values = {}
                                variant_data['preconfigured_data'] = preconfigured_data

                            if not variant.preconfigured_attribute_option_ids:
                                for preconfigured_line in variant.preconfigured_attribute_line_ids:
                                    preconfigured_line_values[
                                        'attribute_value'] = preconfigured_line.product_template_attribute_value_id.display_name or preconfigured_line.product_template_attribute_value_id.name
                                    preconfigured_line_values[
                                        'material_allocation'] = preconfigured_line.material_allocation_id.name
                                    preconfigured_line_values[
                                        'sub_attribute'] = preconfigured_line.sub_attribute_id.display_name or preconfigured_line.sub_attribute_id.name
                                    preconfigured_line_values[
                                        'sub_attribute_values'] = preconfigured_line.sub_attribute_value_ids.mapped(
                                        'name')
                                    preconfigured_data.append(preconfigured_line_values)
                                    preconfigured_line_values = {}

                                variant_data['preconfigured_data'] = preconfigured_data

                            if variant.preconfigured_attribute_option_ids:
                                for option in variant.preconfigured_attribute_option_ids:
                                    option_vals['name'] = option.name
                                    if option.option_image_attachment_ids:
                                        option_vals['option_image_attachments'] = self._get_attachments(
                                            option.option_image_attachment_ids)
                                    for pre_line in option.preconfigured_option_line_ids:
                                        preconfigured_line_values[
                                            'attribute_value'] = pre_line.product_template_attribute_value_id.display_name or pre_line.product_template_attribute_value_id.name
                                        preconfigured_line_values['material_allocation'] = pre_line.material_allocation_id.name
                                        preconfigured_line_values[
                                            'sub_attribute'] = pre_line.sub_attribute_id.display_name or pre_line.sub_attribute_id.name
                                        preconfigured_line_values[
                                            'sub_attribute_values'] = pre_line.sub_attribute_value_ids.mapped('name')
                                        preconfigured_data.append(preconfigured_line_values)
                                        preconfigured_line_values = {}
                                    option_vals['pre-congigured-option-lines'] = preconfigured_data
                                    preconfigured_data = []
                                    option_data.append(option_vals)
                                    option_vals = {}

                                variant_data['preconfigured_option_data'] = option_data

                            
                            if variant.api_variant_featured_attachment_ids:
                                variant_data['variant_featured_attachments'] = self._get_attachments(
                                    variant.api_variant_featured_attachment_ids)
                            
                        variant_optional_groups = optional_group_lines.sudo().search([('product_product_id', '=', variant.id),('is_publish','=',True)])
                        variant_optional_group_list = []
                        vairant_display_vals = {}
                        variant_group_vals = {}
                        if variant_optional_groups:
                            for line in variant_optional_groups:
                                variant_group_vals['group_name'] = line.optional_group_id.name
                                variant_group_vals['website_name'] = line.website_name
                                variant_group_vals['products'] = line.product_ids.mapped('name') if line.product_ids else False
                                vairant_display_vals[line.name] = variant_group_vals
                                variant_optional_group_list.append(vairant_display_vals)
                                variant_group_vals = {}
                                vairant_display_vals = {}
                                
                        if variant_optional_group_list:
                            variant_data['variant_optional_groups_data'] = variant_optional_group_list

                        template_data['variants'].append(variant_data)
                products_data.append(template_data)
            response_data = {
                'status': 'success',
                'count': len(products_data),
                'data': products_data
            }
            return response_data
        except Exception as e:
            error_response = {
                'status': 'error',
                'message': str(e)
            }
            return error_response

    @http.route(['''/api/products/published/type/<string:type>'''], type='json', auth='public', csrf=False, cors='*')
    def get_product_with_type(self, **kwargs):
        try:
            base_url = request.httprequest.host_url
            product_template_object = request.env['product.template']
            published_product_with_type = product_template_object.sudo().search([
                ('is_product_published', '=', True),
                ('type', '=', kwargs['type'])
            ])
            if not published_product_with_type:
                return {
                    'status': 'success',
                    'count': 0,
                    'message': 'No products available to fetch',
                    'data': []
                }

            products_data = []

            for template in published_product_with_type:
                # Basic template data
                template_data = {
                    'id': template.id,
                    'product_origin': template.api_website_product_origin,
                    'name': template.api_template_product_name,
                    'image_url': f"{request.httprequest.host_url}web/image/product.template/{template.id}/image_1920",
                    'default_code': template.api_template_default_code,
                    'parent_category': template.api_template_custom_categ_id.parent_id.display_name,
                    'child_category': template.api_template_custom_categ_id.name,
                    'sale_price': template.api_template_list_price,
                    'customer_tax': template.api_template_taxes_id.name,
                    'is_modular_template_product': template.is_modular_template_product,
                    'is_purchasable_online_template': template.is_purchasable_online_template,
                    # 'lead_time': template.api_template_quotation_lead_time,
                    'brand': template.api_template_brand,
                    'type': 'template',
                    'unit': template.api_template_unit,

                }

                if template.api_website_description:
                    template_data['description'] = template.api_website_description
                if template.api_website_dimensions:
                    template_data['dimensions'] = template.api_website_dimensions
                if template.api_website_finishes:
                    template_data['finishes'] = template.api_website_finishes
                if template.api_website_features:
                    template_data['features'] = template.api_website_features
                if template.api_website_warranty:
                    template_data['warranty'] = template.api_website_warranty
                if template.api_website_lead_time:
                    template_data['lead_time'] = template.api_website_lead_time


                if template.api_template_image_attachment_ids:
                    template_data['image_attachments'] = self._get_attachments(
                        template.api_template_image_attachment_ids)

                if template.api_template_featured_attachment_ids:
                    template_data['featured_attachments'] = self._get_attachments(
                        template.api_template_featured_attachment_ids)

                if template.api_template_docs_attachment_ids:
                    template_data['docs_attachments'] = self._get_attachments(template.api_template_docs_attachment_ids)

                api_template_delivery_code_selection = template.api_template_delivery_code_selection_id
                if api_template_delivery_code_selection:
                    # Delivery Cost
                    zone1_delivery_cost = api_template_delivery_code_selection.delivery_code_cost
                    zone2_delivery_cost = api_template_delivery_code_selection.zone2_delivery_cost
                    zone3_delivery_cost = api_template_delivery_code_selection.zone3_delivery_cost

                    # Installation Cost
                    zone1_installation_cost = api_template_delivery_code_selection.installation_cost
                    zone2_installation_cost = api_template_delivery_code_selection.zone2_installation_cost
                    zone3_installation_cost = api_template_delivery_code_selection.zone3_installation_cost

                    # Postal Code
                    zone_postal_obj = request.env['zone.postal'].search([], limit=1)
                    zone1_postal_codes = zone_postal_obj.zone1_postal_code_ids.mapped('name')
                    zone2_postal_codes = zone_postal_obj.zone2_postal_code_ids.mapped('name')
                    zone3_postal_codes = zone_postal_obj.zone3_postal_code_ids.mapped('name')

                    # Website minimum
                    zone1_website_minimum = api_template_delivery_code_selection.zone1_website_minimum
                    zone2_website_minimum = api_template_delivery_code_selection.zone2_website_minimum
                    zone3_website_minimum = api_template_delivery_code_selection.zone3_website_minimum

                    # Website Sales Price
                    zone1_website_sales_price = api_template_delivery_code_selection.zone1_website_sale_price
                    zone2_website_sales_price = api_template_delivery_code_selection.zone2_website_sale_price
                    zone3_website_sales_price = api_template_delivery_code_selection.zone3_website_sale_price


                    zone_data = {
                        'zone1': {
                            'postal_codes': zone1_postal_codes,
                            # 'delivery_cost': zone1_delivery_cost,
                            # 'installation_cost': zone1_installation_cost,
                            'website_minimum': zone1_website_minimum,
                            'website_sales_price': zone1_website_sales_price,
                        },
                        'zone2': {
                            'postal_codes': zone2_postal_codes,
                            # 'delivery_cost': zone2_delivery_cost,
                            # 'installation_cost': zone2_installation_cost,
                            'website_minimum': zone2_website_minimum,
                            'website_sales_price': zone2_website_sales_price,
                        },
                        'zone3': {
                            'postal_codes': zone3_postal_codes,
                            # 'delivery_cost': zone3_delivery_cost,
                            # 'installation_cost': zone3_installation_cost,
                            'website_minimum': zone3_website_minimum,
                            'website_sales_price': zone3_website_sales_price,
                        }
                    }
                    if zone_data:
                        template_data['zone_postal_data'] = zone_data


                optional_group_lines = request.env['optional.groups.line']
                optional_groups = optional_group_lines.sudo().search([('product_template_id', '=', template.id),('is_publish','=',True)])
                optional_group_list = []
                display_vals = {}
                group_vals = {}
                if optional_groups:
                    for line in optional_groups:
                        group_vals['group_name'] = line.optional_group_id.name
                        group_vals['website_name'] = line.website_name
                        group_vals['products'] = line.product_ids.mapped('name') if line.product_ids else False
                        display_vals[line.name] = group_vals
                        optional_group_list.append(display_vals)
                        group_vals = {}
                        display_vals = {}
                        
                if optional_group_list:
                    template_data['optional_groups_data'] = optional_group_list

                total_attribute_values = []
                if template.attribute_line_ids:
                    for attribute_line in template.attribute_line_ids:
                        for val in attribute_line.value_ids:
                            total_attribute_values.append(val.name)
                    if total_attribute_values:
                        template_data['all_attribute_values'] = total_attribute_values

                template_data['variants'] = []

                # Get published variants for this template
                published_variants = request.env['product.product'].sudo().search([
                    ('product_tmpl_id', '=', template.id),
                    ('is_product_published', '=', True)
                ])
                if template.attribute_line_ids:
                    for variant in published_variants:
                        # Get variant attributes
                        variant_attributes = []
                        sub_attribute_data = []
                        sub_attribute_value_data = []
                        for attribute_value in variant.product_template_attribute_value_ids:

                            if attribute_value.sub_attribute_line_ids:
                                for sub_attribute_line in attribute_value.sub_attribute_line_ids:
                                    sub_attribute_vals = {
                                        'sub_attribute_id': sub_attribute_line.sub_attribute_id.id,
                                        'sub_attribute_name': sub_attribute_line.sub_attribute_id.name,
                                        'sub_attribute_display_type': sub_attribute_line.sub_attribute_id.display_type,
                                        'sub_attribute_type':sub_attribute_line.sub_attribute_id.sub_attribute_type_id.name
                                    }
                                    if sub_attribute_line.sub_attribute_value_ids:
                                        for sub_attribute_value in sub_attribute_line.sub_attribute_value_ids:
                                            value_data = {
                                                'id': sub_attribute_value.id,
                                                'name': sub_attribute_value.name,
                                                'lead_time': sub_attribute_value.lead_time,
                                                'default_for_website': sub_attribute_value.is_default_website,
                                                'extra_price': sub_attribute_value.default_extra_price,
                                                'metalness': sub_attribute_value.metalness,
                                                'roughness': sub_attribute_value.roughness
                                            }
                                            if sub_attribute_value.sub_attribute_id.display_type == 'color':
                                                value_data[
                                                    'color'] = sub_attribute_value.html_color if sub_attribute_value.html_color else False
                                                value_data['image_url'] = (
                                                    f"{base_url}web/image/sub.attribute.value.line/{sub_attribute_value.id}/image"
                                                    if sub_attribute_value.image
                                                    else False
                                                )
                                            value_data['texture_image_url'] = (
                                                f"{base_url}web/image/sub.attribute.value.line/{sub_attribute_value.id}/texture_image"
                                                if sub_attribute_value.texture_image
                                                else False
                                            )
                                            sub_attribute_value_data.append(value_data)
                                            value_data = {}
                                        sub_attribute_vals['sub_attribute_values'] = sub_attribute_value_data
                                        sub_attribute_data.append(sub_attribute_vals)
                                        sub_attribute_value_data = []
                            attribute_data = {
                                'attribute_id': attribute_value.attribute_id.id,
                                'attribute_name': attribute_value.attribute_id.name,
                                'value_id': attribute_value.product_attribute_value_id.id,
                                'value_name': attribute_value.product_attribute_value_id.name,
                                'material_allocation': attribute_value.material_allocation_id.name,
                                # 'sub_attribute_details': sub_attribute_data
                            }
                            if attribute_value.three_d_attachment_ids:
                                attribute_data['attribute_value_three_d_attachments'] = self._get_attachments(
                                    attribute_value.three_d_attachment_ids)
                            if sub_attribute_data:
                                attribute_data['sub_attribute_details'] = sub_attribute_data
                            variant_attributes.append(attribute_data)
                            sub_attribute_data = []
                        # Create variant data with attributes
                        variant_data = {
                            'id': variant.id,
                            'website_name': variant.api_variant_website_name,
                            'image_url': f"{request.httprequest.host_url}web/image/product.product/{variant.id}/image_1920",
                            # 'default_code': variant.api_variant_default_code,
                            'type': 'variant',
                            'unit': variant.api_variant_unit,
                            'variant_attribute_values': variant.product_template_attribute_value_ids.mapped('name'),
                            'is_preconfigured': variant.is_preconfigured,
                            'is_modular_variant_product': variant.is_modular_variant_product,
                            'is_purchasable_online_variant': variant.is_purchasable_online_variant,
                        }
                        api_variant_delivery_code_selection = variant.api_variant_delivery_code_selection_id
                        if api_variant_delivery_code_selection:
                            # Delivery Cost
                            zone1_delivery_cost = api_variant_delivery_code_selection.delivery_code_cost
                            zone2_delivery_cost = api_variant_delivery_code_selection.zone2_delivery_cost
                            zone3_delivery_cost = api_variant_delivery_code_selection.zone3_delivery_cost

                            # Installation Cost
                            zone1_installation_cost = api_variant_delivery_code_selection.installation_cost
                            zone2_installation_cost = api_variant_delivery_code_selection.zone2_installation_cost
                            zone3_installation_cost = api_variant_delivery_code_selection.zone3_installation_cost

                            # Postal Code
                            zone_postal_obj = request.env['zone.postal'].search([], limit=1)
                            zone1_postal_codes = zone_postal_obj.zone1_postal_code_ids.mapped('name')
                            zone2_postal_codes = zone_postal_obj.zone2_postal_code_ids.mapped('name')
                            zone3_postal_codes = zone_postal_obj.zone3_postal_code_ids.mapped('name')

                            # Website minimum
                            zone1_website_minimum = api_variant_delivery_code_selection.zone1_website_minimum
                            zone2_website_minimum = api_variant_delivery_code_selection.zone2_website_minimum
                            zone3_website_minimum = api_variant_delivery_code_selection.zone3_website_minimum

                            # Website Sales Price
                            zone1_website_sales_price = api_variant_delivery_code_selection.zone1_website_sale_price
                            zone2_website_sales_price = api_variant_delivery_code_selection.zone2_website_sale_price
                            zone3_website_sales_price = api_variant_delivery_code_selection.zone3_website_sale_price


                            variant_zone_data = {
                                'zone1': {
                                    'postal_codes': zone1_postal_codes,
                                    # 'delivery_cost': zone1_delivery_cost,
                                    # 'installation_cost': zone1_installation_cost,
                                    'website_minimum': zone1_website_minimum,
                                    'website_sales_price': zone1_website_sales_price,
                                },
                                'zone2': {
                                    'postal_codes': zone2_postal_codes,
                                    # 'delivery_cost': zone2_delivery_cost,
                                    # 'installation_cost': zone2_installation_cost,
                                    'website_minimum': zone2_website_minimum,
                                    'website_sales_price': zone2_website_sales_price,
                                },
                                'zone3': {
                                    'postal_codes': zone3_postal_codes,
                                    # 'delivery_cost': zone3_delivery_cost,
                                    # 'installation_cost': zone3_installation_cost,
                                    'website_minimum': zone3_website_minimum,
                                    'website_sales_price': zone3_website_sales_price,
                                }
                            }
                            if variant_zone_data:
                                variant_data['variant_zone_postal_data'] = variant_zone_data
                        if variant.api_variant_list_price:
                            variant_data['sales_price'] = variant.api_variant_list_price

                        if variant.api_variant_three_d_attachment_ids:
                            variant_data['variant_three_d_attachments'] = self._get_attachments(
                                variant.api_variant_three_d_attachment_ids)
                        if variant_attributes:
                            variant_data['attributes'] = variant_attributes

                        preconfigured_data = []
                        preconfigured_line_values = {}
                        option_data = []
                        option_vals = {}
                        if variant.is_preconfigured:
                            if not variant.preconfigured_attribute_option_ids and not variant.preconfigured_attribute_option_ids:
                                preconfigured_line_values['options'] = False
                                preconfigured_data.append(preconfigured_line_values)
                                preconfigured_line_values = {}
                                variant_data['preconfigured_data'] = preconfigured_data

                            if not variant.preconfigured_attribute_option_ids:
                                for preconfigured_line in variant.preconfigured_attribute_line_ids:
                                    preconfigured_line_values[
                                        'attribute_value'] = preconfigured_line.product_template_attribute_value_id.display_name or preconfigured_line.product_template_attribute_value_id.name
                                    preconfigured_line_values[
                                        'material_allocation'] = preconfigured_line.material_allocation_id.name
                                    preconfigured_line_values[
                                        'sub_attribute'] = preconfigured_line.sub_attribute_id.display_name or preconfigured_line.sub_attribute_id.name
                                    preconfigured_line_values[
                                        'sub_attribute_values'] = preconfigured_line.sub_attribute_value_ids.mapped(
                                        'name')
                                    preconfigured_data.append(preconfigured_line_values)
                                    preconfigured_line_values = {}

                                variant_data['preconfigured_data'] = preconfigured_data

                            if variant.preconfigured_attribute_option_ids:
                                for option in variant.preconfigured_attribute_option_ids:
                                    option_vals['name'] = option.name
                                    if option.option_image_attachment_ids:
                                        option_vals['option_image_attachments'] = self._get_attachments(
                                            option.option_image_attachment_ids)
                                    for pre_line in option.preconfigured_option_line_ids:
                                        preconfigured_line_values[
                                            'attribute_value'] = pre_line.product_template_attribute_value_id.display_name or pre_line.product_template_attribute_value_id.name
                                        preconfigured_line_values['material_allocation'] = pre_line.material_allocation_id.name
                                        preconfigured_line_values[
                                            'sub_attribute'] = pre_line.sub_attribute_id.display_name or pre_line.sub_attribute_id.name
                                        preconfigured_line_values[
                                            'sub_attribute_values'] = pre_line.sub_attribute_value_ids.mapped('name')
                                        preconfigured_data.append(preconfigured_line_values)
                                        preconfigured_line_values = {}
                                    option_vals['pre-configered-option-lines'] = preconfigured_data
                                    preconfigured_data = []
                                    option_data.append(option_vals)
                                    option_vals = {}

                                variant_data['preconfigured_option_data'] = option_data

                            
                            if variant.api_variant_featured_attachment_ids:
                                variant_data['variant_featured_attachments'] = self._get_attachments(
                                    variant.api_variant_featured_attachment_ids)
                            
                        variant_optional_groups = optional_group_lines.sudo().search([('product_product_id', '=', variant.id),('is_publish','=',True)])
                        variant_optional_group_list = []
                        vairant_display_vals = {}
                        variant_group_vals = {}
                        if variant_optional_groups:
                            for line in variant_optional_groups:
                                variant_group_vals['group_name'] = line.optional_group_id.name
                                variant_group_vals['website_name'] = line.website_name
                                variant_group_vals['products'] = line.product_ids.mapped('name') if line.product_ids else False
                                vairant_display_vals[line.name] = variant_group_vals
                                variant_optional_group_list.append(vairant_display_vals)
                                variant_group_vals = {}
                                vairant_display_vals = {}
                                
                        if variant_optional_group_list:
                            variant_data['variant_optional_groups_data'] = variant_optional_group_list

                        # if variant.api_variant_docs_attachment_ids:
                        #     variant_data['docs_attachments'] = self._get_attachments(
                        #         variant.api_variant_docs_attachment_ids)
                        template_data['variants'].append(variant_data)
                products_data.append(template_data)
            response_data = {
                'status': 'success',
                'count': len(products_data),
                'data': products_data
            }
            return response_data
        except Exception as e:
            error_response = {
                'status': 'error',
                'message': str(e)
            }
            return error_response


    # @http.route('/api/products/published/<model("product.template"):product>', type='json', auth='public', methods=['GET'], csrf=False, cors='*')
    @http.route(['''/api/products/published/<int:product>'''], type='json', auth='public', csrf=False, cors='*')
    def get_product(self, **kwargs):
        try:
            base_url = request.httprequest.host_url
            product_template_object = request.env['product.template']
            published_product = product_template_object.sudo().search([
                ('is_product_published', '=', True),
                ('id', '=', kwargs['product'])
            ])
            if not published_product:
                return {
                    'status': 'success',
                    'count': 0,
                    'message': 'No products available to fetch',
                    'data': []
                }

            products_data = []

            # Basic template data
            template_data = {
                'id': published_product.id,
                'product_origin': published_product.api_website_product_origin,
                'name': published_product.api_template_product_name,
                'image_url': f"{request.httprequest.host_url}web/image/product.template/{published_product.id}/image_1920",
                'default_code': published_product.api_template_default_code,
                'parent_category': published_product.api_template_custom_categ_id.parent_id.display_name,
                'child_category': published_product.api_template_custom_categ_id.name,
                'sale_price': published_product.api_template_list_price,
                'customer_tax': published_product.api_template_taxes_id.name,
                'is_modular_template_product': published_product.is_modular_template_product,
                'is_purchasable_online_template': published_product.is_purchasable_online_template,
                # 'lead_time': published_product.api_template_quotation_lead_time,
                'brand': published_product.api_template_brand,
                # 'weight': published_product.weight,
                # 'volume': published_product.api_template_volume,
                'type': 'template',
                'unit': published_product.api_template_unit,

            }

            if published_product.api_website_description:
                template_data['description'] = published_product.api_website_description
            if published_product.api_website_dimensions:
                template_data['dimensions'] = published_product.api_website_dimensions
            if published_product.api_website_finishes:
                template_data['finishes'] = published_product.api_website_finishes
            if published_product.api_website_features:
                template_data['features'] = published_product.api_website_features
            if published_product.api_website_warranty:
                template_data['warranty'] = published_product.api_website_warranty
            if published_product.api_website_lead_time:
                template_data['lead_time'] = published_product.api_website_lead_time


            if published_product.api_template_image_attachment_ids:
                template_data['image_attachments'] = self._get_attachments(
                    published_product.api_template_image_attachment_ids)

            if published_product.api_template_docs_attachment_ids:
                template_data['docs_attachments'] = self._get_attachments(
                    published_product.api_template_docs_attachment_ids)

            if published_product.api_template_featured_attachment_ids:
                template_data['featured_attachments'] = self._get_attachments(
                    published_product.api_template_featured_attachment_ids)


            api_template_delivery_code_selection = published_product.api_template_delivery_code_selection_id
            if api_template_delivery_code_selection:
                # Delivery Cost
                zone1_delivery_cost = api_template_delivery_code_selection.delivery_code_cost
                zone2_delivery_cost = api_template_delivery_code_selection.zone2_delivery_cost
                zone3_delivery_cost = api_template_delivery_code_selection.zone3_delivery_cost

                # Installation Cost
                zone1_installation_cost = api_template_delivery_code_selection.installation_cost
                zone2_installation_cost = api_template_delivery_code_selection.zone2_installation_cost
                zone3_installation_cost = api_template_delivery_code_selection.zone3_installation_cost

                # Postal Code
                zone_postal_obj = request.env['zone.postal'].search([], limit=1)
                zone1_postal_codes = zone_postal_obj.zone1_postal_code_ids.mapped('name')
                zone2_postal_codes = zone_postal_obj.zone2_postal_code_ids.mapped('name')
                zone3_postal_codes = zone_postal_obj.zone3_postal_code_ids.mapped('name')

                # Website minimum
                zone1_website_minimum = api_template_delivery_code_selection.zone1_website_minimum
                zone2_website_minimum = api_template_delivery_code_selection.zone2_website_minimum
                zone3_website_minimum = api_template_delivery_code_selection.zone3_website_minimum

                # Website Sales Price
                zone1_website_sales_price = api_template_delivery_code_selection.zone1_website_sale_price
                zone2_website_sales_price = api_template_delivery_code_selection.zone2_website_sale_price
                zone3_website_sales_price = api_template_delivery_code_selection.zone3_website_sale_price


                zone_data = {
                    'zone1': {
                        'postal_codes': zone1_postal_codes,
                        # 'delivery_cost': zone1_delivery_cost,
                        # 'installation_cost': zone1_installation_cost,
                        'website_minimum': zone1_website_minimum,
                        'website_sales_price': zone1_website_sales_price,
                    },
                    'zone2': {
                        'postal_codes': zone2_postal_codes,
                        # 'delivery_cost': zone2_delivery_cost,
                        # 'installation_cost': zone2_installation_cost,
                        'website_minimum': zone2_website_minimum,
                        'website_sales_price': zone2_website_sales_price,
                    },
                    'zone3': {
                        'postal_codes': zone3_postal_codes,
                        # 'delivery_cost': zone3_delivery_cost,
                        # 'installation_cost': zone3_installation_cost,
                        'website_minimum': zone3_website_minimum,
                        'website_sales_price': zone3_website_sales_price,
                    }
                }
                if zone_data:
                    template_data['zone_postal_data'] = zone_data

            optional_group_lines = request.env['optional.groups.line']
            optional_groups = optional_group_lines.sudo().search([('product_template_id', '=', published_product.id),('is_publish','=',True)])
            optional_group_list = []
            display_vals = {}
            group_vals = {}
            if optional_groups:
                for line in optional_groups:
                    group_vals['group_name'] = line.optional_group_id.name
                    group_vals['website_name'] = line.website_name
                    group_vals['products'] = line.product_ids.mapped('name') if line.product_ids else False
                    display_vals[line.name] = group_vals
                    optional_group_list.append(display_vals)
                    group_vals = {}
                    display_vals = {}
                    
            if optional_group_list:
                template_data['optional_groups_data'] = optional_group_list

            total_attribute_values = []
            if published_product.attribute_line_ids:
                for attribute_line in published_product.attribute_line_ids:
                    for val in attribute_line.value_ids:
                        total_attribute_values.append(val.name)
                if total_attribute_values:
                    template_data['all_attribute_values'] = total_attribute_values

            template_data['variants'] = []

            # Get published variants for this template
            published_variants = request.env['product.product'].sudo().search([
                ('product_tmpl_id', '=', kwargs['product']),
                ('is_product_published', '=', True)
            ])
            if published_product.attribute_line_ids:
                for variant in published_variants:
                    # Get variant attributes
                    variant_attributes = []
                    sub_attribute_data = []
                    sub_attribute_value_data = []
                    for attribute_value in variant.product_template_attribute_value_ids:
                        if attribute_value.sub_attribute_line_ids:
                            for sub_attribute_line in attribute_value.sub_attribute_line_ids:
                                sub_attribute_vals = {
                                    'sub_attribute_id': sub_attribute_line.sub_attribute_id.id,
                                    'sub_attribute_name': sub_attribute_line.sub_attribute_id.name,
                                    'sub_attribute_display_type': sub_attribute_line.sub_attribute_id.display_type,
                                    'sub_attribute_type':sub_attribute_line.sub_attribute_id.sub_attribute_type_id.name
                                }
                                if sub_attribute_line.sub_attribute_value_ids:
                                    for sub_attribute_value in sub_attribute_line.sub_attribute_value_ids:
                                        value_data = {
                                            'id': sub_attribute_value.id,
                                            'name': sub_attribute_value.name,
                                            'lead_time': sub_attribute_value.lead_time,
                                            'extra_price': sub_attribute_value.default_extra_price,
                                            'default_for_website': sub_attribute_value.is_default_website,
                                            'metalness': sub_attribute_value.metalness,
                                            'roughness': sub_attribute_value.roughness
                                        }
                                        if sub_attribute_value.sub_attribute_id.display_type == 'color':
                                            value_data[
                                                'color'] = sub_attribute_value.html_color if sub_attribute_value.html_color else False
                                            value_data['image_url'] = (
                                                    f"{base_url}web/image/sub.attribute.value.line/{sub_attribute_value.id}/image"
                                                    if sub_attribute_value.image
                                                    else False
                                                )
                                        value_data['texture_image_url'] = (
                                                f"{base_url}web/image/sub.attribute.value.line/{sub_attribute_value.id}/texture_image"
                                                if sub_attribute_value.texture_image
                                                else False
                                            )
                                        sub_attribute_value_data.append(value_data)
                                        value_data = {}
                                    sub_attribute_vals['sub_attribute_values'] = sub_attribute_value_data
                                    sub_attribute_data.append(sub_attribute_vals)
                                    sub_attribute_value_data = []
                        attribute_data = {
                            'attribute_id': attribute_value.attribute_id.id,
                            'attribute_name': attribute_value.attribute_id.attribute_website_name,
                            'value_id': attribute_value.product_attribute_value_id.id,
                            'value_name': attribute_value.product_attribute_value_id.name,
                            'material_allocation': attribute_value.material_allocation_id.name,
                            # 'sub_attribute_details': sub_attribute_data
                        }
                        if attribute_value.three_d_attachment_ids:
                            attribute_data['attribute_value_three_d_attachments'] = self._get_attachments(
                                attribute_value.three_d_attachment_ids)
                        if sub_attribute_data:
                            attribute_data['sub_attribute_details'] = sub_attribute_data
                        variant_attributes.append(attribute_data)
                        sub_attribute_data = []
                    variant_data = {
                        'id': variant.id,
                        'website_name': variant.api_variant_website_name,
                        'image_url': f"{request.httprequest.host_url}web/image/product.product/{variant.id}/image_1920",
                        # 'default_code': variant.api_variant_default_code,
                        'type': 'variant',
                        'unit': variant.api_variant_unit,
                        'variant_attribute_values': variant.product_template_attribute_value_ids.mapped('name'),
                        'is_preconfigured': variant.is_preconfigured,
                        'is_modular_variant_product': variant.is_modular_variant_product,
                        'is_purchasable_online_variant': variant.is_purchasable_online_variant,

                    }
                    api_variant_delivery_code_selection = variant.api_variant_delivery_code_selection_id
                    if api_variant_delivery_code_selection:
                        # Delivery Cost
                        zone1_delivery_cost = api_variant_delivery_code_selection.delivery_code_cost
                        zone2_delivery_cost = api_variant_delivery_code_selection.zone2_delivery_cost
                        zone3_delivery_cost = api_variant_delivery_code_selection.zone3_delivery_cost

                        # Installation Cost
                        zone1_installation_cost = api_variant_delivery_code_selection.installation_cost
                        zone2_installation_cost = api_variant_delivery_code_selection.zone2_installation_cost
                        zone3_installation_cost = api_variant_delivery_code_selection.zone3_installation_cost

                        # Postal Code
                        zone_postal_obj = request.env['zone.postal'].search([], limit=1)
                        zone1_postal_codes = zone_postal_obj.zone1_postal_code_ids.mapped('name')
                        zone2_postal_codes = zone_postal_obj.zone2_postal_code_ids.mapped('name')
                        zone3_postal_codes = zone_postal_obj.zone3_postal_code_ids.mapped('name')

                        # Website minimum
                        zone1_website_minimum = api_variant_delivery_code_selection.zone1_website_minimum
                        zone2_website_minimum = api_variant_delivery_code_selection.zone2_website_minimum
                        zone3_website_minimum = api_variant_delivery_code_selection.zone3_website_minimum

                        # Website Sales Price
                        zone1_website_sales_price = api_variant_delivery_code_selection.zone1_website_sale_price
                        zone2_website_sales_price = api_variant_delivery_code_selection.zone2_website_sale_price
                        zone3_website_sales_price = api_variant_delivery_code_selection.zone3_website_sale_price


                        variant_zone_data = {
                            'zone1': {
                                'postal_codes': zone1_postal_codes,
                                # 'delivery_cost': zone1_delivery_cost,
                                # 'installation_cost': zone1_installation_cost,
                                'website_minimum': zone1_website_minimum,
                                'website_sales_price': zone1_website_sales_price,
                            },
                            'zone2': {
                                'postal_codes': zone2_postal_codes,
                                # 'delivery_cost': zone2_delivery_cost,
                                # 'installation_cost': zone2_installation_cost,
                                'website_minimum': zone2_website_minimum,
                                'website_sales_price': zone2_website_sales_price,
                            },
                            'zone3': {
                                'postal_codes': zone3_postal_codes,
                                # 'delivery_cost': zone3_delivery_cost,
                                # 'installation_cost': zone3_installation_cost,
                                'website_minimum': zone3_website_minimum,
                                'website_sales_price': zone3_website_sales_price,
                            }
                        }
                        if variant_zone_data:
                            variant_data['variant_zone_postal_data'] = variant_zone_data

                    if variant.api_variant_list_price:
                        variant_data['sales_price'] = variant.api_variant_list_price
                    if variant.api_variant_three_d_attachment_ids:
                        variant_data['variant_three_d_attachments'] = self._get_attachments(
                            variant.api_variant_three_d_attachment_ids)

                    if variant_attributes:
                        variant_data['attributes'] = variant_attributes

                    preconfigured_data = []
                    preconfigured_line_values = {}
                    option_data = []
                    option_vals = {}
                    if variant.is_preconfigured:
                        if not variant.preconfigured_attribute_option_ids and not variant.preconfigured_attribute_option_ids:
                            preconfigured_line_values['options'] = False
                            preconfigured_data.append(preconfigured_line_values)
                            preconfigured_line_values = {}
                            variant_data['preconfigured_data'] = preconfigured_data
                        if not variant.preconfigured_attribute_option_ids:
                            for preconfigured_line in variant.preconfigured_attribute_line_ids:
                                preconfigured_line_values[
                                    'attribute_value'] = preconfigured_line.product_template_attribute_value_id.display_name or preconfigured_line.product_template_attribute_value_id.name
                                preconfigured_line_values[
                                    'material_allocation'] = preconfigured_line.material_allocation_id.name
                                preconfigured_line_values[
                                    'sub_attribute'] = preconfigured_line.sub_attribute_id.display_name or preconfigured_line.sub_attribute_id.name
                                preconfigured_line_values[
                                    'sub_attribute_values'] = preconfigured_line.sub_attribute_value_ids.mapped('name')
                                preconfigured_data.append(preconfigured_line_values)
                                preconfigured_line_values = {}

                            variant_data['preconfigured_data'] = preconfigured_data

                        if variant.preconfigured_attribute_option_ids:
                            for option in variant.preconfigured_attribute_option_ids:
                                option_vals['name'] = option.name
                                if option.option_image_attachment_ids:
                                    option_vals['option_image_attachments'] = self._get_attachments(
                                        option.option_image_attachment_ids)
                                for pre_line in option.preconfigured_option_line_ids:
                                    preconfigured_line_values[
                                        'attribute_value'] = pre_line.product_template_attribute_value_id.display_name or pre_line.product_template_attribute_value_id.name
                                    preconfigured_line_values['material_allocation'] = pre_line.material_allocation_id.name
                                    preconfigured_line_values[
                                        'sub_attribute'] = pre_line.sub_attribute_id.display_name or pre_line.sub_attribute_id.name
                                    preconfigured_line_values[
                                        'sub_attribute_values'] = pre_line.sub_attribute_value_ids.mapped('name')
                                    preconfigured_data.append(preconfigured_line_values)
                                    preconfigured_line_values = {}
                                option_vals['pre-configered-option-lines'] = preconfigured_data
                                preconfigured_data = []
                                option_data.append(option_vals)
                                option_vals = {}

                            variant_data['preconfigured_option_data'] = option_data

                        
                        if variant.api_variant_featured_attachment_ids:
                            variant_data['variant_featured_attachments'] = self._get_attachments(
                                variant.api_variant_featured_attachment_ids)
                    
                    variant_optional_groups = optional_group_lines.sudo().search([('product_product_id', '=', variant.id),('is_publish','=',True)])
                    variant_optional_group_list = []
                    vairant_display_vals = {}
                    variant_group_vals = {}
                    if variant_optional_groups:
                        for line in variant_optional_groups:
                            variant_group_vals['group_name'] = line.optional_group_id.name
                            variant_group_vals['website_name'] = line.website_name
                            variant_group_vals['products'] = line.product_ids.mapped('name') if line.product_ids else False
                            vairant_display_vals[line.name] = variant_group_vals
                            variant_optional_group_list.append(vairant_display_vals)
                            variant_group_vals = {}
                            vairant_display_vals = {}
                            
                    if variant_optional_group_list:
                        variant_data['variant_optional_groups_data'] = variant_optional_group_list

                    template_data['variants'].append(variant_data)
            products_data.append(template_data)
            response_data = {
                'status': 'success',
                'count': len(products_data),
                'data': products_data
            }
            return response_data
        except Exception as e:
            error_response = {
                'status': 'error',
                'message': str(e)
            }
            return error_response

    @http.route('/api/products/published', type='json', auth='public', csrf=False, cors='*')
    def get_published_products(self, **kwargs):
        """
        Get all published product templates with their published variants and variants attributes
        Returns: JSON response with product templates and their variants and  variants attributes
        """
        try:
            # Get all published product templates
            base_url = request.httprequest.host_url
            product_template_object = request.env['product.template']
            published_templates = product_template_object.sudo().search([
                ('is_product_published', '=', True)
            ])
            if not published_templates:
                return {
                    'status': 'success',
                    'count': 0,
                    'message': 'No products available to fetch',
                    'data': []
                }

            products_data = []

            for template in published_templates:
                # Basic template data
                template_data = {
                    'id': template.id,
                    'product_origin': template.api_website_product_origin,
                    'name': template.api_template_product_name,
                    'image_url': f"{request.httprequest.host_url}web/image/product.template/{template.id}/image_1920",
                    'default_code': template.api_template_default_code,
                    'parent_category': template.api_template_custom_categ_id.parent_id.display_name,
                    'child_category': template.api_template_custom_categ_id.name,
                    'sale_price': template.api_template_list_price,
                    'customer_tax': template.api_template_taxes_id.name,
                    'is_modular_template_product': template.is_modular_template_product,
                    'is_purchasable_online_template': template.is_purchasable_online_template,
                    # 'lead_time': template.api_template_quotation_lead_time,
                    'brand': template.api_template_brand,
                    # 'weight': template.weight,
                    # 'volume': template.api_template_volume,
                    'type': 'template',
                    'unit': template.api_template_unit,

                }
                if template.api_website_description:
                    template_data['description'] = template.api_website_description
                if template.api_website_dimensions:
                    template_data['dimensions'] = template.api_website_dimensions
                if template.api_website_finishes:
                    template_data['finishes'] = template.api_website_finishes
                if template.api_website_features:
                    template_data['features'] = template.api_website_features
                if template.api_website_warranty:
                    template_data['warranty'] = template.api_website_warranty
                if template.api_website_lead_time:
                    template_data['lead_time'] = template.api_website_lead_time


                if template.api_template_image_attachment_ids:
                    template_data['image_attachments'] = self._get_attachments(
                        template.api_template_image_attachment_ids)


                if template.api_template_docs_attachment_ids:
                    template_data['docs_attachments'] = self._get_attachments(template.api_template_docs_attachment_ids)

                if template.api_template_featured_attachment_ids:
                    template_data['featured_attachments'] = self._get_attachments(
                        template.api_template_featured_attachment_ids)
                api_template_delivery_code_selection = template.api_template_delivery_code_selection_id
                if api_template_delivery_code_selection:
                    # Delivery Cost
                    zone1_delivery_cost = api_template_delivery_code_selection.delivery_code_cost
                    zone2_delivery_cost = api_template_delivery_code_selection.zone2_delivery_cost
                    zone3_delivery_cost = api_template_delivery_code_selection.zone3_delivery_cost

                    # Installation Cost
                    zone1_installation_cost = api_template_delivery_code_selection.installation_cost
                    zone2_installation_cost = api_template_delivery_code_selection.zone2_installation_cost
                    zone3_installation_cost = api_template_delivery_code_selection.zone3_installation_cost

                    # Postal Code
                    zone_postal_obj = request.env['zone.postal'].search([], limit=1)
                    zone1_postal_codes = zone_postal_obj.zone1_postal_code_ids.mapped('name')
                    zone2_postal_codes = zone_postal_obj.zone2_postal_code_ids.mapped('name')
                    zone3_postal_codes = zone_postal_obj.zone3_postal_code_ids.mapped('name')

                    # Website minimum
                    zone1_website_minimum = api_template_delivery_code_selection.zone1_website_minimum
                    zone2_website_minimum = api_template_delivery_code_selection.zone2_website_minimum
                    zone3_website_minimum = api_template_delivery_code_selection.zone3_website_minimum

                    # Website Sales Price
                    zone1_website_sales_price = api_template_delivery_code_selection.zone1_website_sale_price
                    zone2_website_sales_price = api_template_delivery_code_selection.zone2_website_sale_price
                    zone3_website_sales_price = api_template_delivery_code_selection.zone3_website_sale_price


                    zone_data = {
                        'zone1': {
                            'postal_codes': zone1_postal_codes,
                            # 'delivery_cost': zone1_delivery_cost,
                            # 'installation_cost': zone1_installation_cost,
                            'website_minimum': zone1_website_minimum,
                            'website_sales_price': zone1_website_sales_price,
                        },
                        'zone2': {
                            'postal_codes': zone2_postal_codes,
                            # 'delivery_cost': zone2_delivery_cost,
                            # 'installation_cost': zone2_installation_cost,
                            'website_minimum': zone2_website_minimum,
                            'website_sales_price': zone2_website_sales_price,
                        },
                        'zone3': {
                            'postal_codes': zone3_postal_codes,
                            # 'delivery_cost': zone3_delivery_cost,
                            # 'installation_cost': zone3_installation_cost,
                            'website_minimum': zone3_website_minimum,
                            'website_sales_price': zone3_website_sales_price,
                        }
                    }
                    if zone_data:
                        template_data['zone_postal_data'] = zone_data



                optional_group_lines = request.env['optional.groups.line']
                optional_groups = optional_group_lines.sudo().search([('product_template_id', '=', template.id),('is_publish','=',True)])
                optional_group_list = []
                display_vals = {}
                group_vals = {}
                if optional_groups:
                    for line in optional_groups:
                        group_vals['group_name'] = line.optional_group_id.name
                        group_vals['website_name'] = line.website_name
                        group_vals['products'] = line.product_ids.mapped('name') if line.product_ids else False
                        display_vals[line.name] = group_vals
                        optional_group_list.append(display_vals)
                        group_vals = {}
                        display_vals = {}
                        
                if optional_group_list:
                    template_data['optional_groups_data'] = optional_group_list

                total_attribute_values = []
                if template.attribute_line_ids:
                    for attribute_line in template.attribute_line_ids:
                        for val in attribute_line.value_ids:
                            total_attribute_values.append(val.name)
                    if total_attribute_values:
                        template_data['all_attribute_values'] = total_attribute_values

                template_data['variants'] = []

                # Get published variants for this template
                published_variants = request.env['product.product'].sudo().search([
                    ('product_tmpl_id', '=', template.id),
                    ('is_product_published', '=', True)
                ])
                total_attribute_values = []
                if template.attribute_line_ids:
                    for variant in published_variants:
                        # Get variant attributes
                        variant_attributes = []
                        sub_attribute_data = []
                        sub_attribute_value_data = []
                        for attribute_value in variant.product_template_attribute_value_ids:

                            if attribute_value.sub_attribute_line_ids:
                                for sub_attribute_line in attribute_value.sub_attribute_line_ids:
                                    sub_attribute_vals = {
                                        'sub_attribute_id': sub_attribute_line.sub_attribute_id.id,
                                        'sub_attribute_name': sub_attribute_line.sub_attribute_id.name,
                                        'sub_attribute_display_type': sub_attribute_line.sub_attribute_id.display_type,
                                        'sub_attribute_type':sub_attribute_line.sub_attribute_id.sub_attribute_type_id.name
                                    }
                                    if sub_attribute_line.sub_attribute_value_ids:
                                        for sub_attribute_value in sub_attribute_line.sub_attribute_value_ids:
                                            value_data = {
                                                'id': sub_attribute_value.id,
                                                'name': sub_attribute_value.name,
                                                'lead_time': sub_attribute_value.lead_time,
                                                'default_for_website': sub_attribute_value.is_default_website,
                                                'extra_price': sub_attribute_value.default_extra_price,
                                                'metalness': sub_attribute_value.metalness,
                                                'roughness': sub_attribute_value.roughness
                                            }
                                            if sub_attribute_value.sub_attribute_id.display_type == 'color':
                                                value_data[
                                                    'color'] = sub_attribute_value.html_color if sub_attribute_value.html_color else False
                                                value_data['image_url'] = (
                                                    f"{base_url}web/image/sub.attribute.value.line/{sub_attribute_value.id}/image"
                                                    if sub_attribute_value.image
                                                    else False
                                                )
                                            value_data['texture_image_url'] = (
                                                f"{base_url}web/image/sub.attribute.value.line/{sub_attribute_value.id}/texture_image"
                                                if sub_attribute_value.texture_image
                                                else False
                                            )
                                            sub_attribute_value_data.append(value_data)
                                            value_data = {}
                                        sub_attribute_vals['sub_attribute_values'] = sub_attribute_value_data
                                        sub_attribute_data.append(sub_attribute_vals)
                                        sub_attribute_value_data = []
                            attribute_data = {
                                'attribute_id': attribute_value.attribute_id.id,
                                'attribute_name': attribute_value.attribute_id.attribute_website_name,
                                'value_id': attribute_value.product_attribute_value_id.id,
                                'value_name': attribute_value.product_attribute_value_id.name,
                                'material_allocation': attribute_value.material_allocation_id.name,
                                # 'sub_attribute_details': sub_attribute_data
                            }
                            if attribute_value.three_d_attachment_ids:
                                attribute_data['attribute_value_three_d_attachments'] = self._get_attachments(
                                    attribute_value.three_d_attachment_ids)
                            if sub_attribute_data:
                                attribute_data['sub_attribute_details'] = sub_attribute_data
                            variant_attributes.append(attribute_data)
                            sub_attribute_data = []
                        # Create variant data with attributes
                        variant_data = {
                            'id': variant.id,
                            'website_name': variant.api_variant_website_name,
                            'image_url': f"{request.httprequest.host_url}web/image/product.product/{variant.id}/image_1920",
                            # 'default_code': variant.api_variant_default_code,
                            'type': 'variant',
                            'unit': variant.api_variant_unit,
                            'variant_attribute_values': variant.product_template_attribute_value_ids.mapped('name'),
                            'is_preconfigured': variant.is_preconfigured,
                            'is_modular_variant_product': variant.is_modular_variant_product,
                            'is_purchasable_online_variant': variant.is_purchasable_online_variant,
                            # 'weight': variant.api_variant_weight,
                            # 'volume': variant.api_variant_volume,
                            # 'description_sale':variant.api_variant_description_sale,
                            # 'attributes': variant_attributes,
                        }
                        api_variant_delivery_code_selection = variant.api_variant_delivery_code_selection_id
                        if api_variant_delivery_code_selection:
                            # Delivery Cost
                            zone1_delivery_cost = api_variant_delivery_code_selection.delivery_code_cost
                            zone2_delivery_cost = api_variant_delivery_code_selection.zone2_delivery_cost
                            zone3_delivery_cost = api_variant_delivery_code_selection.zone3_delivery_cost

                            # Installation Cost
                            zone1_installation_cost = api_variant_delivery_code_selection.installation_cost
                            zone2_installation_cost = api_variant_delivery_code_selection.zone2_installation_cost
                            zone3_installation_cost = api_variant_delivery_code_selection.zone3_installation_cost

                            # Postal Code
                            zone_postal_obj = request.env['zone.postal'].search([], limit=1)
                            zone1_postal_codes = zone_postal_obj.zone1_postal_code_ids.mapped('name')
                            zone2_postal_codes = zone_postal_obj.zone2_postal_code_ids.mapped('name')
                            zone3_postal_codes = zone_postal_obj.zone3_postal_code_ids.mapped('name')

                            # Website minimum
                            zone1_website_minimum = api_variant_delivery_code_selection.zone1_website_minimum
                            zone2_website_minimum = api_variant_delivery_code_selection.zone2_website_minimum
                            zone3_website_minimum = api_variant_delivery_code_selection.zone3_website_minimum

                            # Website Sales Price
                            zone1_website_sales_price = api_variant_delivery_code_selection.zone1_website_sale_price
                            zone2_website_sales_price = api_variant_delivery_code_selection.zone2_website_sale_price
                            zone3_website_sales_price = api_variant_delivery_code_selection.zone3_website_sale_price


                            variant_zone_data = {
                                'zone1': {
                                    'postal_codes': zone1_postal_codes,
                                    # 'delivery_cost': zone1_delivery_cost,
                                    # 'installation_cost': zone1_installation_cost,
                                    'website_minimum': zone1_website_minimum,
                                    'website_sales_price': zone1_website_sales_price,
                                },
                                'zone2': {
                                    'postal_codes': zone2_postal_codes,
                                    # 'delivery_cost': zone2_delivery_cost,
                                    # 'installation_cost': zone2_installation_cost,
                                    'website_minimum': zone2_website_minimum,
                                    'website_sales_price': zone2_website_sales_price,
                                },
                                'zone3': {
                                    'postal_codes': zone3_postal_codes,
                                    # 'delivery_cost': zone3_delivery_cost,
                                    # 'installation_cost': zone3_installation_cost,
                                    'website_minimum': zone3_website_minimum,
                                    'website_sales_price': zone3_website_sales_price,
                                }
                            }
                            if variant_zone_data:
                                variant_data['variant_zone_postal_data'] = variant_zone_data
                        if variant.api_variant_list_price:
                            variant_data['sales_price'] = variant.api_variant_list_price

                        if variant.api_variant_three_d_attachment_ids:
                            variant_data['variant_three_d_attachments'] = self._get_attachments(
                                variant.api_variant_three_d_attachment_ids)

                        if variant_attributes:
                            variant_data['attributes'] = variant_attributes

                        preconfigured_data = []
                        preconfigured_line_values = {}
                        option_data = []
                        option_vals = {}
                        if variant.is_preconfigured:
                            if not variant.preconfigured_attribute_option_ids and not variant.preconfigured_attribute_option_ids:
                                preconfigured_line_values['options'] = False
                                preconfigured_data.append(preconfigured_line_values)
                                preconfigured_line_values = {}
                                variant_data['preconfigured_data'] = preconfigured_data
                            if not variant.preconfigured_attribute_option_ids:
                                for preconfigured_line in variant.preconfigured_attribute_line_ids:
                                    preconfigured_line_values[
                                        'attribute_value'] = preconfigured_line.product_template_attribute_value_id.display_name or preconfigured_line.product_template_attribute_value_id.name
                                    preconfigured_line_values[
                                        'material_allocation'] = preconfigured_line.material_allocation_id.name
                                    preconfigured_line_values[
                                        'sub_attribute'] = preconfigured_line.sub_attribute_id.display_name or preconfigured_line.sub_attribute_id.name
                                    preconfigured_line_values[
                                        'sub_attribute_values'] = preconfigured_line.sub_attribute_value_ids.mapped(
                                        'name')
                                    preconfigured_data.append(preconfigured_line_values)
                                    preconfigured_line_values = {}

                                variant_data['preconfigured_data'] = preconfigured_data

                            if variant.preconfigured_attribute_option_ids:
                                for option in variant.preconfigured_attribute_option_ids:
                                    option_vals['name'] = option.name
                                    if option.option_image_attachment_ids:
                                        option_vals['option_image_attachments'] = self._get_attachments(
                                            option.option_image_attachment_ids)
                                    for pre_line in option.preconfigured_option_line_ids:
                                        preconfigured_line_values[
                                            'attribute_value'] = pre_line.product_template_attribute_value_id.display_name or pre_line.product_template_attribute_value_id.name
                                        preconfigured_line_values['material_allocation'] = pre_line.material_allocation_id.name
                                        preconfigured_line_values[
                                            'sub_attribute'] = pre_line.sub_attribute_id.display_name or pre_line.sub_attribute_id.name
                                        preconfigured_line_values[
                                            'sub_attribute_values'] = pre_line.sub_attribute_value_ids.mapped('name')
                                        preconfigured_data.append(preconfigured_line_values)
                                        preconfigured_line_values = {}
                                    option_vals['pre-configered-option-lines'] = preconfigured_data
                                    preconfigured_data = []
                                    option_data.append(option_vals)
                                    option_vals = {}

                                variant_data['preconfigured_option_data'] = option_data

                            
                            if variant.api_variant_featured_attachment_ids:
                                variant_data['variant_featured_attachments'] = self._get_attachments(
                                    variant.api_variant_featured_attachment_ids)

                                    #  {
                                    #     'attribute_value': preconfigured_line.product_template_attribute_value_id.display_name or preconfigured_line.product_template_attribute_value_id.name,
                                    #     'material_allocation': preconfigured_line.material_allocation_id.name,
                                    #     'sub_attribute': preconfigured_line.sub_attribute_id.display_name or preconfigured_line.sub_attribute_id.name,

                                    # }


                        variant_optional_groups = optional_group_lines.sudo().search([('product_product_id', '=', variant.id),('is_publish','=',True)])
                        variant_optional_group_list = []
                        vairant_display_vals = {}
                        variant_group_vals = {}
                        if variant_optional_groups:
                            for line in variant_optional_groups:
                                variant_group_vals['group_name'] = line.optional_group_id.name
                                variant_group_vals['website_name'] = line.website_name
                                variant_group_vals['products'] = line.product_ids.mapped('name') if line.product_ids else False
                                vairant_display_vals[line.name] = variant_group_vals
                                variant_optional_group_list.append(vairant_display_vals)
                                variant_group_vals = {}
                                vairant_display_vals = {}
                                
                        if variant_optional_group_list:
                            variant_data['variant_optional_groups_data'] = variant_optional_group_list
                        template_data['variants'].append(variant_data)
                products_data.append(template_data)
            response_data = {
                'status': 'success',
                'count': len(products_data),
                'data': products_data
            }
            return response_data
        except Exception as e:
            error_response = {
                'status': 'error',
                'message': str(e)
            }
            return error_response

    @http.route(['''/api/products/published/<int:product>/images'''], type='json', auth='public', csrf=False, cors='*')
    def get_product_attachments(self, **kwargs):
        try:
            product_template_object = request.env['product.template']
            attachment_found = False
            published_product = product_template_object.sudo().search([
                ('is_product_published', '=', True),
                ('id', '=', kwargs['product'])
            ])
            if not published_product:
                return {
                    'status': 'success',
                    'count': 0,
                    'message': 'No products available to fetch',
                    'data': []
                }

            products_data = []

            # Basic template data
            template_data = {
                'id': published_product.id,
                'name': published_product.api_template_product_name,
                'type': 'template',
            }
            template_image_attahments = published_product.api_template_image_attachment_ids
            template_doc_attachments = published_product.api_template_docs_attachment_ids
            template_featured_attachments = published_product.api_template_featured_attachment_ids
            if any([template_image_attahments, template_doc_attachments, template_featured_attachments]):
                attachment_found = True
                if template_image_attahments:
                    template_data['image_attachments'] = self._get_attachments(
                        template_image_attahments)

                if template_doc_attachments:
                    template_data['docs_attachments'] = self._get_attachments(template_doc_attachments)

                if template_featured_attachments:
                    template_data['featured_attachments'] = self._get_attachments(template_featured_attachments)

            template_data['variants'] = []

            # Get published variants for this template
            published_variants = request.env['product.product'].sudo().search([
                ('product_tmpl_id', '=', kwargs['product']),
                ('is_product_published', '=', True)
            ])
            if published_product.attribute_line_ids:
                for variant in published_variants:
                    featured_attachments = variant.api_variant_featured_attachment_ids
                    three_d_attachments = variant.api_variant_three_d_attachment_ids
                    if any([featured_attachments, three_d_attachments]):
                        attachment_found = True
                        variant_data = {
                            'id': variant.id,
                            'image_url': f"{request.httprequest.host_url}web/image/product.product/{variant.id}/image_1920",
                            'type': 'variant',
                        }
                        if featured_attachments:
                            variant_data['variant_featured_attachment_ids'] = self._get_attachments(
                                featured_attachments)
                        if three_d_attachments:
                            variant_data['variant_three_d_attachments'] = self._get_attachments(
                                three_d_attachments)

                        template_data['variants'].append(variant_data)
            products_data.append(template_data)
            if not attachment_found:
                return {
                    'status': 'success',
                    'message': 'No product attachments available to fetch',
                    'data': []
                }
            response_data = {
                'status': 'success',
                'count': len(products_data),
                'data': products_data
            }
            return response_data
        except Exception as e:
            error_response = {
                'status': 'error',
                'message': str(e)
            }
            return error_response

    @http.route(['/api/products/templates/simple/<int:product>'], type='json', auth='public', csrf=False, cors='*')
    def get_simple_product_template(self, **kwargs):
        """
        Get a single published product template with limited fields:
        id, name, category, sale_price, featured_attachments
        """
        try:
            # Get specific published product template
            published_product = request.env['product.template'].sudo().search([
                ('is_product_published', '=', True),
                ('id', '=', kwargs['product'])
            ], limit=1)

            if not published_product:
                return {
                    'status': 'success',
                    'count': 0,
                    'message': 'No product found with the provided ID',
                    'data': []
                }

            # Prepare data
            template_data = {
                'id': published_product.id,
                'name': published_product.api_template_product_name,
                'parent_category': published_product.api_template_custom_categ_id.parent_id.display_name,
                'child_category': published_product.api_template_custom_categ_id.name if published_product.api_template_custom_categ_id else False,
                'sale_price': published_product.api_template_list_price,
            }

            # Add featured attachments if available
            if published_product.api_template_featured_attachment_ids:
                template_data['featured_attachments'] = self._get_attachments(
                    published_product.api_template_featured_attachment_ids)

            # Response format consistent with your other endpoints
            response_data = {
                'status': 'success',
                'count': 1,
                'data': [template_data]
            }
            return response_data

        except Exception as e:
            error_response = {
                'status': 'error',
                'message': str(e)
            }
            return error_response

    @http.route('/api/products/templates/simple', type='json', auth='public', csrf=False, cors='*')
    def get_simple_published_templates(self, **kwargs):
        """
        Get all published product templates with limited fields:
        id, name, category, sale_price, featured_attachments
        """
        try:
            # Get all published product templates
            published_templates = request.env['product.template'].sudo().search([
                ('is_product_published', '=', True)
            ])

            if not published_templates:
                return {
                    'status': 'success',
                    'count': 0,
                    'message': 'No products available to fetch',
                    'data': []
                }

            products_data = []

            for template in published_templates:
                # Basic template data (using same field names and style)
                template_data = {
                    'id': template.id,
                    'name': template.api_template_product_name,
                    'parent_category': template.api_template_custom_categ_id.parent_id.display_name,
                    'child_category': template.api_template_custom_categ_id.name if template.api_template_custom_categ_id else False,
                    'sale_price': template.api_template_list_price,
                }

                # Featured attachments
                if template.api_template_featured_attachment_ids:
                    template_data['featured_attachments'] = self._get_attachments(
                        template.api_template_featured_attachment_ids)

                products_data.append(template_data)

            response_data = {
                'status': 'success',
                'count': len(products_data),
                'data': products_data
            }
            return response_data

        except Exception as e:
            error_response = {
                'status': 'error',
                'message': str(e)
            }
            return error_response
