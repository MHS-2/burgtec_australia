# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from http.cookiejar import unmatched

from dateutil.relativedelta import relativedelta

from odoo.addons.sale_purchase_inter_company_rules.models.sale_order import sale_order
from odoo.service.model import execute
from odoo.tools import float_compare
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons.stock.models.stock_rule import ProcurementException
from odoo.tools import groupby
from odoo.exceptions import UserError, ValidationError


class StockRuleExt(models.Model):
    _inherit = 'stock.rule'

    def _make_purchase_order(self, purchase_orders):
        # This is being fetched from stock picking ONLY WORKS WHEN MAKING PURCHASE ORDER FOR CHILD PO FROM PARENT PO.
        sale_order_id = self.env['stock.picking'].search([('name', '=', purchase_orders[0].origin)]).sale_id
        PurchaseOrder = self.env['purchase.order']
        deleted_po_count = 0
        purchase_order_sequence_obj = self.sudo().env.ref('purchase.seq_purchase_order')
        child_po_count = 0
        sale_order = False
        res = False
        # This If only works for child purchase orders when parent purchase order is confirmed.
        if sale_order_id.bom_component_id:
            # purchase_orders_obj = PurchaseOrder.browse([po.id for po in purchase_orders])
            # po_ref_list = purchase_orders_obj.mapped('name')
            # po_origin = purchase_orders_obj.mapped('origin')
            # po_date_order = purchase_orders_obj[0].date_order
            # purchase_orders_obj.sudo().button_cancel()
            # purchase_orders_obj.sudo().unlink()
            vendors = len(sale_order_id.order_line.filtered(lambda l: l.product_id).mapped(
                lambda l: l.product_id.seller_ids[0].partner_id))
            if vendors > 1:
                raise ValidationError(
                    'You cannot confirm this purchase order.because Products on this purchase order have different vendors!')
                # purchase_order_id = self.env.context.get('purchase_order_id')
                # if purchase_order_id:
                #     purchase_order = self.env['purchase.order'].browse(purchase_order_id)
                # for line in purchase_order.order_line:
                #     line_child_from_bom = sale_order_id.bom_component_id.component_line_ids.filtered(
                #         lambda l: l.parent_product_id.id == line.product_id.product_tmpl_id.id)
                #     self._create_po_for_multiple_order_lines(line_child_from_bom, po_ref_list, po_origin, po_date_order)
            else:
                purchase_orders_obj = PurchaseOrder.browse([po.id for po in purchase_orders])
                po_ref_list = purchase_orders_obj.mapped('name')
                po_origin = purchase_orders_obj.mapped('origin')
                po_date_order = purchase_orders_obj[0].mapped('date_order')
                source_po = purchase_orders_obj[0] if purchase_orders_obj else None
                picking_type_id = source_po.picking_type_id.id if source_po else False
                group_id = source_po.group_id.id if source_po and source_po.group_id else False
                company_id = source_po.company_id.id if source_po else False
                currency_id = source_po.currency_id.id if source_po else False
                dest_address_id = source_po.dest_address_id.id if source_po.dest_address_id else False
                fiscal_position_id = source_po.fiscal_position_id.id if source_po.fiscal_position_id else False
                payment_term_id = source_po.payment_term_id.id if source_po.payment_term_id else False
                user_id = source_po.user_id.id if source_po.user_id else False
                partner_id = source_po.partner_id
                deleted_po_count = len(purchase_orders_obj)  # Next number must be 1 count a head
                purchase_order_sequence_obj.sudo().number_next_actual = purchase_order_sequence_obj.sudo().number_next_actual - deleted_po_count
                purchase_orders_obj.sudo().button_cancel()
                purchase_orders_obj.sudo().unlink()
                purchase_order_id = self.env.context.get('purchase_order_id')
                if purchase_order_id:
                    purchase_order = self.env['purchase.order'].browse(purchase_order_id)

                    # Get all relevant component lines (non-parent)
                    component_lines = sale_order_id.bom_component_id.component_line_ids.filtered(
                        lambda l: not l.is_parent and l.product_id
                    )

                    # Map to hold final supplier grouped lines
                    supplier_grouped_data = {}

                    for po_line in purchase_order.order_line:
                        parent_tmpl = po_line.product_id.product_tmpl_id
                        parent_qty = po_line.product_qty

                        # Find components linked to this parent product
                        matched_components = component_lines.filtered(
                            lambda
                                l: l.parent_product_id.id == parent_tmpl.id and l.order_line_id.id == po_line.sale_line_id.id
                        )

                        # Get total parent quantity defined in BOM for proportion (assuming consistent for each)
                        total_bom_qty = sale_order_id.bom_component_id.component_line_ids.filtered(
                            lambda
                                l: l.is_parent and l.product_id.product_tmpl_id.id == parent_tmpl.id and l.order_line_id.id == po_line.sale_line_id.id
                        ).mapped('product_qty')

                        if not total_bom_qty:
                            continue  # Skip if BOM does not define quantity
                        bom_qty = total_bom_qty[0]

                        for comp in matched_components:
                            supplier = comp.supplier_id
                            if not supplier:
                                continue

                            # Calculate proportional quantity and price
                            qty_per_unit = comp.product_qty / bom_qty
                            final_qty = qty_per_unit * parent_qty

                            cost_per_unit = comp.live_unit_cost / bom_qty
                            com_per_unit_cost = comp.live_unit_cost / comp.product_qty
                            final_cost = cost_per_unit * parent_qty

                            # Normalize note
                            note_normalized = (comp.note or '').strip().lower()
                            com_group_code_id = comp.line_section_id_value

                            key = (supplier.id, comp.product_id.id, note_normalized, com_per_unit_cost,
                                   com_group_code_id)

                            if key not in supplier_grouped_data:
                                supplier_grouped_data[key] = {
                                    'supplier': supplier,
                                    'product_id': comp.product_id.id,
                                    'note': comp.note or '',
                                    'per_unit_cost': com_per_unit_cost,
                                    'total_qty': 0,
                                    'total_price': 0,
                                    'line_group_name': po_line.line_group_name,
                                    'line_section_name': po_line.line_section_name,
                                }

                            supplier_grouped_data[key]['total_qty'] += final_qty
                            supplier_grouped_data[key]['total_price'] += final_cost

                    # Now group by supplier and create purchase orders
                    for supplier, group in groupby(
                            sorted(supplier_grouped_data.items(), key=lambda x: x[1]['supplier'].id),
                            key=lambda x: x[1]['supplier']):
                        grouped_lines = list(group)
                        po_lines = []

                        for _, data in grouped_lines:
                            line_vals = {
                                'product_id': data['product_id'],
                                'product_qty': data['total_qty'],
                                'price_unit': data['total_price'] / data['total_qty'] if data['total_qty'] else 0.0,
                                'line_group_name_child': data['line_group_name'],
                                'line_section_name_child': data['line_section_name'],
                            }
                            if data['note']:
                                line_vals['note'] = data['note']
                            po_lines.append((0, 0, line_vals))

                        po_vals = {
                            'partner_id': supplier.id,
                            'delivery_stage': purchase_order.delivery_stage,
                            # 'hubspot_dispatch_date': purchase_order.hubspot_dispatch_date,
                            # 'builder_trend_po': purchase_order.builder_trend_po,
                            'date_order': purchase_order.date_order,
                            'sale_quote_reference': purchase_order.sale_quote_reference,
                            'origin': po_origin[0],
                            'order_line': po_lines,
                            'picking_type_id': picking_type_id,
                            'group_id': group_id,
                            'company_id': company_id,
                            'currency_id': currency_id,
                            'dest_address_id': dest_address_id,
                            'fiscal_position_id': fiscal_position_id,
                            'payment_term_id': payment_term_id,
                            'user_id': user_id,
                            'child_po_count': child_po_count + 1,
                            'date_planned': purchase_order.date_planned,
                            'tag': 'child',
                            'is_old_data': purchase_order.is_old_data,
                            'hubspot_reference': purchase_order.hubspot_reference,
                            'parent_po_id': purchase_order.id
                        }
                        child_po_count += 1

                        if po_ref_list:
                            po_vals['name'] = po_ref_list.pop(0)
                        if purchase_order.hubspot_dispatch_date:
                            po_vals['hubspot_dispatch_date'] = purchase_order.hubspot_dispatch_date

                        res = self.env['purchase.order'].create(po_vals)
                        if res:
                            purchase_order.child_purchase_order_ids = [(4, res.id, 0)]
                        purchase_order_sequence_obj.sudo().number_next_actual += 1


        # This will always work when Sale order is confirmed and Parent PO is being created!
        else:
            # In case of Parent PO creation this block will execute
            PurchaseOrder = self.env['purchase.order']
            purchase_orders_obj = PurchaseOrder.browse([po.id for po in purchase_orders])
            po_ref_list = purchase_orders_obj.mapped('name')
            po_origin_list = purchase_orders_obj.mapped('origin')
            source_po = purchase_orders_obj[0] if purchase_orders_obj else None
            # Fetch all necessary fields BEFORE deletion
            picking_type_id = source_po.picking_type_id.id if source_po else False
            group_id = source_po.group_id.id if source_po and source_po.group_id else False
            company_id = source_po.company_id.id if source_po else False
            currency_id = source_po.currency_id.id if source_po else False
            dest_address_id = source_po.dest_address_id.id if source_po.dest_address_id else False
            fiscal_position_id = source_po.fiscal_position_id.id if source_po.fiscal_position_id else False
            payment_term_id = source_po.payment_term_id.id if source_po.payment_term_id else False
            user_id = source_po.user_id.id if source_po.user_id else False
            partner_id = source_po.partner_id
            date_order = fields.Datetime.now()
            # Cancel and delete POs
            deleted_po_count = len(purchase_orders_obj)  # Next number must be 1 count a head
            purchase_order_sequence_obj.sudo().number_next_actual = purchase_order_sequence_obj.sudo().number_next_actual - deleted_po_count
            purchase_orders_obj.sudo().button_cancel()
            purchase_orders_obj.sudo().unlink()
            # Recreate POs
            if po_origin_list:
                sale_order = self.env['sale.order'].search([('name', '=', po_origin_list[0])], limit=1)
                # For live
                if sale_order:
                    hubspot_dispatch_date = sale_order.hubspot_ticket_schedule_dispatch

                if not sale_order:
                    raise UserError(_("No Sale Order Found For The Purchase Order Being Created!"))

                product_lines = []
                # This will work for the new data according to quote_type_customization_flow
                if not sale_order.is_old_data:
                    for line in sale_order.order_line:
                        if line.product_id and line.product_uom_qty > 0:
                            product_lines.append({
                                'product_id': line.product_id.product_variant_id.id,
                                'product_qty': line.product_uom_qty,
                                'name': line.product_id.display_name,
                                # 'group_code': line.line_section_name,
                                'sale_line_id': line.id,
                            })

                    if not product_lines:
                        raise ValidationError('Please add products to the Sale Order before creating a Purchase Order.')

                    po_vals = {
                        'partner_id': partner_id.id,
                        'origin': sale_order.name,
                        # 'sale_quote_reference': sale_order.burgtec_quote_reference if sale_order.burgtec_quote_reference else False,
                        'sale_quote_reference': sale_order.new_sale_order_number if sale_order.new_sale_order_number else False,
                        'delivery_stage': sale_order.delivery_stage,
                        'order_line': [(0, 0, line_vals) for line_vals in product_lines],
                        'picking_type_id': picking_type_id,
                        'group_id': group_id,
                        'company_id': company_id,
                        'currency_id': currency_id,
                        'dest_address_id': dest_address_id,
                        'fiscal_position_id': fiscal_position_id,
                        'payment_term_id': payment_term_id,
                        'user_id': user_id,
                        'date_order': date_order,
                        'date_planned': fields.Datetime.now(),
                        'tag': 'parent',
                        'is_old_data': sale_order.is_old_data,
                        'hubspot_reference': sale_order.hubspot_reference,
                    }

                    if po_ref_list:
                        po_vals['name'] = po_ref_list.pop(0)
                        # For live
                    if hubspot_dispatch_date:
                        po_vals['hubspot_dispatch_date'] = hubspot_dispatch_date

                    PurchaseOrder.create(po_vals)
                    purchase_order_sequence_obj.sudo().number_next_actual += 1
                # elif sale_order.is_old_data:
                elif sale_order.is_old_data and sale_order and sale_order.split_do_id.line_ids:
                    product_stage_map = {}
                    for line in sale_order.split_do_id.line_ids:
                        for stage in range(1, 6):
                            qty = getattr(line, f'do_stage_{stage}', 0) or 0
                            if qty > 0:
                                product_stage_map.setdefault(stage, []).append({
                                    'product_id': line.product_id.product_variant_id.id,
                                    'product_qty': qty,
                                    'name': line.product_id.display_name,
                                    # 'group_code': line.line_section_name,
                                    'sale_line_id': line.order_line_id.id,
                                })

                    for stage, po_lines in product_stage_map.items():
                        po_vals = {
                            'partner_id': partner_id.id,
                            'origin': po_origin_list[0],
                            # 'sale_quote_reference': sale_order.burgtec_quote_reference if sale_order.burgtec_quote_reference else False,
                            'sale_quote_reference': sale_order.new_sale_order_number if sale_order.new_sale_order_number else False,
                            'delivery_stage': sale_order.delivery_stage,
                            'order_line': [(0, 0, line_vals) for line_vals in po_lines],
                            'picking_type_id': picking_type_id,
                            'group_id': group_id,
                            'company_id': company_id,
                            'currency_id': currency_id,
                            'dest_address_id': dest_address_id,
                            'fiscal_position_id': fiscal_position_id,
                            'payment_term_id': payment_term_id,
                            'user_id': user_id,
                            'date_order': date_order,
                            'date_planned': fields.Datetime.now(),
                            'tag': 'parent',
                            'is_old_data': sale_order.is_old_data,
                            'hubspot_reference': sale_order.hubspot_reference,
                        }
                        if po_ref_list:
                            po_vals['name'] = po_ref_list.pop(0)
                        PurchaseOrder.create(po_vals)
                        purchase_order_sequence_obj.sudo().number_next_actual += 1
                else:
                    raise ValidationError('Please set the Delivery Order Lines and Stages')

    @api.model
    def _run_buy(self, procurements):
        procurements_by_po_domain = defaultdict(list)
        errors = []
        po_list = []
        for procurement, rule in procurements:

            # Get the schedule date in order to find a valid seller
            procurement_date_planned = fields.Datetime.from_string(procurement.values['date_planned'])

            supplier = False
            company_id = rule.company_id or procurement.company_id
            if procurement.values.get('supplierinfo_id'):
                supplier = procurement.values['supplierinfo_id']
            elif procurement.values.get('orderpoint_id') and procurement.values['orderpoint_id'].supplier_id:
                supplier = procurement.values['orderpoint_id'].supplier_id
            else:
                supplier = procurement.product_id.with_company(company_id.id)._select_seller(
                    partner_id=self._get_partner_id(procurement.values, rule),
                    quantity=procurement.product_qty,
                    date=max(procurement_date_planned.date(), fields.Date.today()),
                    uom_id=procurement.product_uom)

            # Fall back on a supplier for which no price may be defined. Not ideal, but better than
            # blocking the user.
            supplier = supplier or procurement.product_id._prepare_sellers(False).filtered(
                lambda s: not s.company_id or s.company_id == company_id
            )[:1]

            if not supplier:
                msg = _(
                    'There is no matching vendor price to generate the purchase order for product %s (no vendor defined, minimum quantity not reached, dates not valid, ...). Go on the product form and complete the list of vendors.',
                    procurement.product_id.display_name)
                errors.append((procurement, msg))

            partner = supplier.partner_id
            # we put `supplier_info` in values for extensibility purposes
            procurement.values['supplier'] = supplier
            procurement.values['propagate_cancel'] = rule.propagate_cancel

            domain = rule._make_po_get_domain(company_id, procurement.values, partner)
            procurements_by_po_domain[domain].append((procurement, rule))

        if errors:
            raise ProcurementException(errors)

        for domain, procurements_rules in procurements_by_po_domain.items():
            # Get the procurements for the current domain.
            # Get the rules for the current domain. Their only use is to create
            # the PO if it does not exist.
            procurements, rules = zip(*procurements_rules)

            # Get the set of procurement origin for the current domain.
            origins = set([p.origin for p in procurements if p.origin])
            # Check if a PO exists for the current domain.
            po = self.env['purchase.order'].sudo().search([dom for dom in domain], limit=1)
            company_id = rules[0].company_id or procurements[0].company_id
            if not po:
                positive_values = [p.values for p in procurements if
                                   float_compare(p.product_qty, 0.0, precision_rounding=p.product_uom.rounding) >= 0]
                if positive_values:
                    # We need a rule to generate the PO. However the rule generated
                    # the same domain for PO and the _prepare_purchase_order method
                    # should only uses the common rules's fields.
                    vals = rules[0]._prepare_purchase_order(company_id, origins, positive_values)
                    # The company_id is the same for all procurements since
                    # _make_po_get_domain add the company in the domain.
                    # We use SUPERUSER_ID since we don't want the current user to be follower of the PO.
                    # Indeed, the current user may be a user without access to Purchase, or even be a portal user.
                    po = self.env['purchase.order'].with_company(company_id).with_user(SUPERUSER_ID).create(vals)
                    po_list.append(po)
            else:
                # If a purchase order is found, adapt its `origin` field.
                if po.origin:
                    missing_origins = origins - set(po.origin.split(', '))
                    if missing_origins:
                        po.write({'origin': po.origin + ', ' + ', '.join(missing_origins)})
                else:
                    po.write({'origin': ', '.join(origins)})

            procurements_to_merge = self._get_procurements_to_merge(procurements)
            procurements = self._merge_procurements(procurements_to_merge)

            po_lines_by_product = {}
            grouped_po_lines = groupby(
                po.order_line.filtered(lambda l: not l.display_type and l.product_uom == l.product_id.uom_po_id),
                key=lambda l: l.product_id.id)
            for product, po_lines in grouped_po_lines:
                po_lines_by_product[product] = self.env['purchase.order.line'].concat(*po_lines)
            po_line_values = []
            for procurement in procurements:
                po_lines = po_lines_by_product.get(procurement.product_id.id, self.env['purchase.order.line'])
                po_line = po_lines._find_candidate(*procurement)

                if po_line:
                    # If the procurement can be merge in an existing line. Directly
                    # write the new values on it.
                    vals = self._update_purchase_order_line(procurement.product_id,
                                                            procurement.product_qty, procurement.product_uom,
                                                            company_id,
                                                            procurement.values, po_line)
                    po_line.sudo().write(vals)
                else:
                    if float_compare(procurement.product_qty, 0,
                                     precision_rounding=procurement.product_uom.rounding) <= 0:
                        # If procurement contains negative quantity, don't create a new line that would contain negative qty
                        continue
                    # If it does not exist a PO line for current procurement.
                    # Generate the create values for it and add it to a list in
                    # order to create it in batch.
                    partner = procurement.values['supplier'].partner_id
                    po_line_values.append(self.env['purchase.order.line']._prepare_purchase_order_line_from_procurement(
                        *procurement, po))
                    # Check if we need to advance the order date for the new line
                    order_date_planned = procurement.values['date_planned'] - relativedelta(
                        days=procurement.values['supplier'].delay)
                    if fields.Date.to_date(order_date_planned) < fields.Date.to_date(po.date_order):
                        po.date_order = order_date_planned
            self.env['purchase.order.line'].sudo().create(po_line_values)
        if po_list:
            self._make_purchase_order(po_list)
