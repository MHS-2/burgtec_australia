# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import http
from odoo.http import request, route
try:
    from odoo.addons.sale.controllers.product_configurator import (
        SaleProductConfiguratorController,
    )
except Exception:
    SaleProductConfiguratorController = None


class BurgtecProductConfiguratorController(http.Controller):

    @http.route(route='/burgtec/product_configurator/get_values', type='json', auth='public')
    def get_values(self, product_template_id, quantity, currency_id, so_date,
                   product_uom_id=None, company_id=None, pricelist_id=None,
                   ptav_ids=None, only_main_product=False, **kwargs):
        """Return product configurator values augmented with sub-attribute data.

        This endpoint reuses sale's configurator logic then enriches each attribute
        value with its related sub_attribute_line_ids and their values.
        """
        # We delegate most work to the sale controller logic by calling the internal
        # API on product.template through env; keep the same behaviour as /sale/product_configurator/get_values
        if company_id:
            request.update_context(allowed_company_ids=[company_id])
        product_template = request.env['product.template'].browse(product_template_id)

        # Build combination
        combination = request.env['product.template.attribute.value']
        if ptav_ids:
            combination = request.env['product.template.attribute.value'].browse(ptav_ids).filtered(
                lambda ptav: ptav.product_tmpl_id.id == product_template_id
            )
            unconfigured_ptals = (
                product_template.attribute_line_ids - combination.attribute_line_id).filtered(
                lambda ptal: ptal.attribute_id.display_type != 'multi')
            combination += unconfigured_ptals.mapped(
                lambda ptal: ptal.product_template_value_ids._only_active()[:1]
            )
        if not combination:
            combination = product_template._get_first_possible_combination()

        currency = request.env['res.currency'].browse(currency_id)
        pricelist = request.env['product.pricelist'].browse(pricelist_id)
        so_date_dt = datetime.fromisoformat(so_date)

        def augment(values):
            # For each attribute line and each attribute value, attach sub_attributes
            for ptal in values.get('attribute_lines', []):
                for av in ptal.get('attribute_values', []):
                    # try to find the ptav record to read its sub_attribute_line_ids
                    try:
                        ptav_rec = request.env['product.template.attribute.value'].browse(av.get('id'))
                        sub_lines = []
                        for sub in ptav_rec.sub_attribute_line_ids:
                            # Build PTAL-like shape so the client can reuse the same PTAL component
                            sub_vals = []
                            for val in sub.sub_attribute_value_ids:
                                sub_vals.append({
                                    'id': val.id,
                                    'name': val.name,
                                    'html_color': getattr(val, 'html_color', False),
                                    'image': False,
                                    'is_custom': False,
                                    'price_extra': getattr(val, 'default_extra_price', 0.0),
                                })
                            # If the sub-attribute has only one possible value, mark it as
                            # 'no_variant' so the PTAL will render the single choice.
                            create_variant = 'no_variant' if len(sub_vals) == 1 else 'always'
                            sub_lines.append({
                                'id': sub.id,
                                'productTmplId': values.get('product_tmpl_id'),
                                'attribute': {
                                    'id': sub.sub_attribute_id.id,
                                    'name': sub.sub_attribute_id.name,
                                    'display_type': getattr(sub.sub_attribute_id, 'display_type', 'select'),
                                },
                                'attribute_values': sub_vals,
                                'selected_attribute_value_ids': [],
                                'create_variant': create_variant,
                                'customValue': False,
                            })
                        av['sub_attributes'] = sub_lines
                    except Exception:
                        av['sub_attributes'] = []
            return values

        # Reuse sale controller logic if available
        products = []
        optional_products = []
        if SaleProductConfiguratorController is not None:
            sale_ctrl = SaleProductConfiguratorController()

            def get_product_info(template, combination_local, parent_combination=None):
                values = sale_ctrl._get_product_information(
                    template,
                    combination_local,
                    currency,
                    pricelist,
                    so_date_dt,
                    quantity=quantity,
                    product_uom_id=product_uom_id,
                    parent_combination=parent_combination,
                )
                values = dict(values)
                return augment(values)

            products = [get_product_info(product_template, combination)]
            if not only_main_product:
                for optional_product_template in product_template.optional_product_ids:
                    parent_comb = product_template.attribute_line_ids.product_template_value_ids
                    if sale_ctrl._should_show_product(optional_product_template, combination):
                        op_info = get_product_info(
                            optional_product_template,
                            optional_product_template._get_first_possible_combination(parent_combination=combination),
                            parent_combination=parent_comb,
                        )
                        op_info['parent_product_tmpl_id'] = product_template.id
                        optional_products.append(op_info)
        else:
            # Fallback: build a minimal response without optional products if sale controller is not present
            products = [augment({'product_tmpl_id': product_template.id, 'attribute_lines': [], 'price': 0.0, 'display_name': product_template.name, 'quantity': quantity})]

        return {
            'products': products,
            'optional_products': optional_products,
            'currency_id': currency_id,
        }
