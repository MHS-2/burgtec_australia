import io
from io import BytesIO
from PIL import Image, features
from lxml import etree
import xlsxwriter
import xlwt
import base64
import pytz
from datetime import date, datetime, timedelta
import calendar
import re
from datetime import datetime
from markupsafe import Markup
from urllib3 import request

from odoo import api, fields, models, Command, _
from odoo.api import readonly
from odoo.exceptions import UserError, ValidationError
import pytz
from pytz import timezone, UTC
from odoo.addons.sale.models.sale_order import SALE_ORDER_STATE
from datetime import datetime, timedelta

import logging

_logger = logging.getLogger(__name__)


class PlanningScreenExt(models.Model):
    _inherit = 'planning.screen'
    do_1_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage1 Status", default='draft')

    do_2_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage2 Status", default='draft')

    do_3_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage3 Status", default='draft')

    do_4_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage4 Status", default='draft')

    do_5_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage5 Status", default='draft')

    do_6_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage6 Status", default='draft')

    do_7_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage7 Status", default='draft')

    do_8_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage8 Status", default='draft')

    do_9_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage9 Status", default='draft')

    do_10_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage10 Status", default='draft')

    do_11_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage11 Status", default='draft')

    do_12_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage12 Status", default='draft')

    do_13_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage13 Status", default='draft')

    do_14_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage14 Status", default='draft')

    do_15_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage15 Status", default='draft')

    do_16_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage16 Status", default='draft')

    do_17_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage17 Status", default='draft')

    do_18_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage18 Status", default='draft')

    do_19_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage19 Status", default='draft')

    do_20_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage20 Status", default='draft')

    do_21_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage21 Status", default='draft')

    do_22_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage22 Status", default='draft')

    do_23_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage23 Status", default='draft')

    do_24_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage24 Status", default='draft')

    do_25_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage25 Status", default='draft')

    do_26_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage26 Status", default='draft')

    do_27_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage27 Status", default='draft')

    do_28_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage28 Status", default='draft')

    do_29_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage29 Status", default='draft')

    do_30_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage30 Status", default='draft')

    do_31_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage31 Status", default='draft')

    do_32_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage32 Status", default='draft')

    do_33_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage33 Status", default='draft')

    do_34_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage34 Status", default='draft')

    do_35_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage35 Status", default='draft')

    do_36_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage36 Status", default='draft')

    do_37_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage37 Status", default='draft')

    do_38_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage38 Status", default='draft')

    do_39_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage39 Status", default='draft')

    do_40_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage40 Status", default='draft')

    do_41_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage41 Status", default='draft')

    do_42_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage42 Status", default='draft')

    do_43_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage43 Status", default='draft')

    do_44_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage44 Status", default='draft')

    do_45_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage45 Status", default='draft')

    do_46_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage46 Status", default='draft')

    do_47_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage47 Status", default='draft')

    do_48_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage48 Status", default='draft')

    do_49_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage49 Status", default='draft')

    do_50_status = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed')
    ], string="DO Stage50 Status", default='draft')

    stage_count = fields.Integer(
        string="Number of Stages", required=True
    )

    delivery_stage_cost_line_ids = fields.One2many('delivery.stage.delivery.cost', 'planning_screen_id',
                                                   compute="_compute_delivery_stage_cost_lines", store=True)

    line_item_status_ids = fields.One2many('line.item.status', 'planning_screen_id',
                                           compute="_compute_line_item_status_quantity", store=True)

    zone_type = fields.Selection(related="order_id.zone_type", store=True)

    total_installation_cost = fields.Monetary(compute="_compute_totals")

    total_deleivery_cost = fields.Monetary(compute="_compute_totals")

    company_id = fields.Many2one('res.company', store=True, copy=False,
                                 string="Company",
                                 default=lambda self: self.env.user.company_id.id)

    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id', )

    @api.depends('line_ids', 'line_ids.line_item_status')
    def _compute_line_item_status_quantity(self):
        values_dict = {
            "sales_sales_court": "Sales-Sales Court",
            "sales_customer_court": "Sales-Customer Court",
            "technical_initial_check": "Technical-Initial Check",
            "technical_final_check": "Technical-Final Check",
            "technical_purchasing": "Technical-Purchasing",
            "projects_awaiting_delivery": "Projects-Awaiting Delivery",
            "projects_delivered": "Projects-Delivered",
            "projects_installed": "Projects-Installed",
            "unschedule": "Unschedule",
        }
        for rec in self:
            status_quantity_dict = {}
            lines = rec.line_ids
            for line in lines:
                status = line.line_item_status
                status_quantity_dict[status] = status_quantity_dict.get(status, 0) + 1
            commands = [(5, 0, 0)]
            for status, qty in status_quantity_dict.items():
                if status:
                    commands.append(Command.create({
                        'status_name': values_dict[status],
                        'status_quantity': qty,
                    }))
            rec.line_item_status_ids = commands

    @api.depends('line_ids')
    def _compute_totals(self):
        for record in self:
            total_installation_cost = 0
            total_delivery_cost = 0
            if record.line_ids and record.zone_type and record.zone_type == 'zone1':
                for line in record.line_ids:
                    total_delivery_cost += (
                            line.product_variant_id.variant_delivery_code_selection_id.delivery_code_cost * line.quantity)
                    total_installation_cost += (
                            line.product_variant_id.variant_delivery_code_selection_id.installation_cost * line.quantity)
            elif record.line_ids and record.zone_type and record.zone_type == 'zone2':
                for line in record.line_ids:
                    total_delivery_cost += (
                            line.product_variant_id.variant_delivery_code_selection_id.zone2_delivery_cost * line.quantity)
                    total_installation_cost += (
                            line.product_variant_id.variant_delivery_code_selection_id.zone2_installation_cost * line.quantity)
            elif record.line_ids and record.zone_type and record.zone_type == 'zone3':
                for line in record.line_ids:
                    total_delivery_cost += (
                            line.product_variant_id.variant_delivery_code_selection_id.zone3_delivery_cost * line.quantity)
                    total_installation_cost += (
                            line.product_variant_id.variant_delivery_code_selection_id.zone3_installation_cost * line.quantity)
            else:
                total_installation_cost = 0
                total_delivery_cost = 0
            record.total_installation_cost = total_installation_cost
            record.total_deleivery_cost = total_delivery_cost

    @api.onchange('line_ids')
    def onchange_line_ids(self):
        for line in self.line_ids:
            # Collect all fields that start with "do_stage_"
            stage_fields = [f for f in line._fields if f.startswith("do_stage_")]
            # Sum their values (default to 0 if False/None)
            total_stages = sum(getattr(line, f) or 0 for f in stage_fields)
            # Compute available quantity
            line.available_quantity = line.quantity - total_stages
            # Validation
            if line.available_quantity < 0:
                raise ValidationError(
                    f"You cannot enter more quantities than the original quantity"
                )

    @api.model_create_multi
    def create(self, vals_list):
        res = super(PlanningScreenExt, self).create(vals_list)
        model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if model and active_id:
            sale_order = self.env[model].browse(active_id)
            sale_order.planning_screen_id = res.id
        return res

    @api.onchange("stage_count")
    def _onchange_stage_count(self):
        # if not self.stage_count:
        #     return
        if self._origin and self._origin.stage_count:
            old_count = self._origin.stage_count
            new_count = self.stage_count
            if new_count < old_count:
                for line in self.line_ids:
                    for stage_num in range(new_count + 1, old_count + 1):
                        field_name = f"do_stage_{stage_num}"
                        field_value = getattr(line, field_name, 0)
                        if field_value and field_value > 0:
                            # self.stage_count = old_count
                            raise ValidationError(
                                f"You cannot reduce stages to {new_count}, "
                                f"because stage {stage_num} already has a value "
                                f"on item {getattr(line, 'item', None)} and product {getattr(line, 'product_id', None) and line.product_id.name or 'Unknown Product'}."
                            )

    def action_handle_do_stage(self, selectedValue, fieldName):
        try:
            match = re.search(r'do_stage_(\d+)', fieldName)
            stage_number = match.group(1)
            target_field = f"do_{stage_number}_status"

            field_obj = self._fields.get(target_field)
            if field_obj and hasattr(field_obj, 'selection'):
                valid_values = [option[0] for option in field_obj.selection]
                if selectedValue not in valid_values:
                    raise ValueError(f"Invalid value '{selectedValue}' for field {target_field}")
                for record in self:
                    setattr(record, target_field, selectedValue)
                    record.sudo().write(
                        {
                            target_field: selectedValue
                        }
                    )
                    # Create delivery stage if status changed from draft to planned
                    current_value = getattr(record, target_field, False)
                    if current_value == 'planned' and selectedValue == 'planned':
                        result = record._create_single_delivery_stage(stage_number)
                        return result
        except UserError:
            # Re-raise UserError as-is to preserve the original message
            raise

    @api.model
    def fetch_do_stages(self, record_ids=None):
        records = self.browse(record_ids) if record_ids else self
        stage_data = {}

        status_fields = [f for f in self._fields if f.startswith('do_') and f.endswith('_status')]

        for record in records:
            for field in status_fields:
                value = getattr(record, field, False)
                if value:
                    stage_num = field.split('_')[1]
                    stage_field = f"do_stage_{stage_num}"
                    stage_data[stage_field] = {
                        'value': value,
                        'disabled': value in ['planned', 'confirmed']
                    }

        return stage_data

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        sale_order_id = self.env.context.get('active_id')
        if not sale_order_id:
            return res
        sale_order = self.env['sale.order'].browse(sale_order_id)
        lines = []
        item = 0
        for sol in sale_order.order_line:
            if not sol.display_type:
                item += 1  # increment counter each loop
                vals = {
                    'display_type': sol.display_type or False,
                    'name': sol.name if sol.display_type else False,
                    'product_reference': sol.product_template_id.default_code if sol.product_template_id else False,
                    'product_id': sol.product_template_id.id if sol.product_id else False,
                    'quantity': sol.product_uom_qty if sol.product_uom_qty else 0,
                    'order_line_id': sol.id,
                    'origin_order_line': sol.old_order_line if sol.old_order_line else False,
                    'code': sol.line_section_name,
                    'item': item,
                    'lead_time': sol.product_template_id.quotation_lead_time,
                    'line_group_name': sol.line_group_name,
                    'line_section_name': sol.line_section_name,
                    'line_group_id_value': int(sol.line_group_id_value),
                    'line_section_id_value': int(sol.line_section_id_value),

                }
                lines.append((0, 0, vals))
        res.update({
            'order_id': sale_order.id,
            'line_ids': lines,
        })
        return res

    def _create_single_delivery_stage(self, stage_number):
        """Create delivery stage for a specific stage number when changed from draft to planned"""
        try:
            sale_order_obj = self.env['sale.order']
            counter = len(self.order_id.child_sale_order_ids) + 1

            for rec in self:
                stage_field = f"do_stage_{stage_number}"

                # Get lines with quantity for this specific stage
                lines_with_qty = []
                for line in rec.line_ids:
                    stage_qty = getattr(line, stage_field, 0)
                    if stage_qty > 0:
                        lines_with_qty.append(line)
                        # Check if this line is fully approved
                        if not line.is_fully_approved:
                            raise UserError(
                                f'Product "{line.product_id.name}" in stage {stage_number} is not fully approved')

                # If no lines with quantity for this stage, raise error
                if not lines_with_qty:
                    raise UserError(f'Stage {stage_number} has no quantity values!')

                self._validate_vendor_requirements(lines_with_qty)

                # Initialize variables for this stage
                all_component_data = []
                order_lines = []

                # Organize lines by group and code with names
                organized = {}
                for line in lines_with_qty:
                    group_id = line.line_group_id_value
                    code_id = line.line_section_id_value

                    # Create group key if it doesn't exist
                    if group_id not in organized:
                        organized[group_id] = {
                            'group_name': line.line_group_name,
                            'codes': {}
                        }
                    # Create code key under group if it doesn't exist
                    if code_id not in organized[group_id]['codes']:
                        organized[group_id]['codes'][code_id] = {
                            'section_name': line.line_section_name,
                            'lines': []
                        }
                    # Append line to the specific group-code combination
                    organized[group_id]['codes'][code_id]['lines'].append(line)

                # Create organized order lines with headers
                for group_id, group_data in organized.items():
                    # Add Group Header
                    order_lines.append((0, 0, {
                        'display_type': 'line_section',
                        'name': group_data['group_name'],
                    }))
                    # Add sections and products under this group
                    for code_id, code_data in group_data['codes'].items():
                        # Add Section Header
                        order_lines.append((0, 0, {
                            'display_type': 'line_note',
                            'name': code_data['section_name'],
                        }))
                        # Add product lines under this section
                        for line in code_data['lines']:
                            if line.product_id:
                                stage_qty = getattr(line, stage_field, 0)
                                order_lines.append((0, 0, {
                                    'product_id': line.product_variant_id.id,
                                    'product_uom_qty': stage_qty,
                                    'price_unit': line.product_id.list_price,
                                    'name': line.product_id.name,
                                    'origin_planning_screen_line': line.id
                                }))

                # Create quotation if we have lines
                if order_lines:
                    # stage_ref = f"{rec.order_id.burgtec_quote_reference}-DS-{str(counter).zfill(2)}"
                    desired_burgtec_quote_reference = rec.order_id.burgtec_quote_reference[:6]
                    stage_ref = f"{desired_burgtec_quote_reference}-{stage_number.zfill(3)}"
                    new_so = sale_order_obj.create({
                        # 'name': f"{rec.order_id.name}-DS-{str(counter).zfill(2)}",
                        'name': f"{rec.order_id.name}-{stage_number.zfill(3)}",
                        'partner_id': rec.order_id.partner_id.id,
                        'quote_type': 'delivery_stage',
                        'series_sequence_id': rec.order_id.series_sequence_id.id,
                        'new_sale_order_number': stage_ref,
                        'source_sale_order_id': rec.order_id.id,
                        'is_child_sale_order': True,
                        'order_line': order_lines,
                        'system_revision': rec.order_id.system_revision,
                        # 'hubspot_ticket_id': rec.order_id.hubspot_ticket_id.id,
                        # 'hubspot_ticket_schedule_dispatch': rec.order_id.hubspot_ticket_schedule_dispatch,
                    })

                    # Link to parent order
                    rec.order_id.write({
                        'is_parent_sale_order': True,
                        'child_sale_order_ids': [(4, new_so.id)],
                    })

                    # Create BOM Components for this specific stage
                    for line in lines_with_qty:
                        order_line_obj = new_so.order_line.filtered(
                            lambda l: l.origin_planning_screen_line and int(l.origin_planning_screen_line) == line.id)

                        if not order_line_obj:
                            continue

                        parent_line = line.planning_screen_id.order_id.bom_component_id.component_line_ids.filtered(
                            lambda l: l.is_parent and l.order_line_id == line.order_line_id
                        )

                        if parent_line:
                            parent_live_unit_cost = 0.0
                            parent_vals = parent_line.copy_data()[0]
                            stage_qty = getattr(line, stage_field, 0)
                            # original full parent qty from source BOM
                            original_parent_qty = parent_line.product_qty or 1.0

                            parent_vals.update({
                                'product_qty': stage_qty,
                                'order_line_id': order_line_obj.id
                            })

                            # parent.live_unit_cost = sum(line.live_unit_cost for line in child_lines)

                            child_lines = line.planning_screen_id.order_id.bom_component_id.component_line_ids.filtered(
                                lambda l: l.parent_product_id.id == parent_line.product_id.product_tmpl_id.id
                                          and l.order_line_id.id == parent_line.order_line_id.id
                            )

                            # parent.live_unit_cost = sum(line.live_unit_cost for line in child_lines)
                            for child in child_lines:
                                child_vals = child.copy_data()[0]
                                proportion_qty = (child.product_qty / original_parent_qty) * stage_qty
                                child_live_unit_cost = proportion_qty * child.manual_live_unit_cost
                                parent_live_unit_cost += child_live_unit_cost
                            parent_vals['live_unit_cost'] = parent_live_unit_cost
                            parent_vals[
                                'manual_live_unit_cost'] = parent_live_unit_cost / stage_qty if stage_qty else 0.0

                            all_component_data.append(parent_vals)

                            for child in child_lines:
                                child_vals = child.copy_data()[0]
                                proportion_qty = (child.product_qty / original_parent_qty) * stage_qty
                                child_live_unit_cost = proportion_qty * child.manual_live_unit_cost
                                child_vals.update({
                                    'parent_product_id': parent_line.product_id.product_tmpl_id.id,
                                    'order_line_id': order_line_obj.id,
                                    'product_qty': proportion_qty,
                                    'live_unit_cost': child_live_unit_cost
                                })
                                all_component_data.append(child_vals)

                    # Create BOM if we have component data
                    if all_component_data:
                        new_bom = self.env['sale.order.bom.component'].with_context(auto_create_bom=True).create(
                            {'order_id': new_so.id})
                        new_so.write({
                            'bom_component_id': new_bom.id
                        })
                        for dic in all_component_data:
                            dic['component_id'] = new_bom.id
                        self.env['sale.order.bom.component.line'].sudo().create(all_component_data)

                        # Log successful creation
                        print("Successfully created delivery stage for stage {stage_number}, Sale Order")
            return self.order_id.action_show_child_sale_orders()

        except Exception as e:
            _logger.error(f"Error creating delivery stage for stage {stage_number}: {str(e)}")
            raise UserError(f"Failed to create delivery stage for stage {stage_number}: {str(e)}")

    def _validate_vendor_requirements(self, lines_with_qty):
        """Validate vendor requirements for planning lines."""
        products_without_vendor = []
        vendors = {}

        for line in lines_with_qty:
            product = line.product_id
            vendor = product.seller_ids[0].partner_id if product.seller_ids else False

            if not vendor:
                products_without_vendor.append(str(line.item))
            else:
                if vendor.id not in vendors:
                    vendors[vendor.id] = {'name': vendor.name, 'items': []}
                vendors[vendor.id]['items'].append(str(line.item))

        if products_without_vendor:
            raise ValidationError(_("Product has no vendor on Item: %s") % ', '.join(products_without_vendor))

        if len(vendors) > 1:
            vendor_details = [
                "%s (Item: %s)" % (data['name'], ', '.join(data['items']))
                for data in vendors.values()
            ]
            raise ValidationError(_("Products having different Vendors  :\n- %s") % '\n- '.join(vendor_details))



    def _format_delivery_date(self, value):
        if not value:
            return '', False

        # Convert string date to date object
        if isinstance(value, str):
            delivery_date = None
            for pattern in ('%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S'):
                try:
                    delivery_date = datetime.strptime(value.strip(), pattern).date()
                    break
                except ValueError:
                    continue
            if not delivery_date:
                return value, False

        elif isinstance(value, datetime):
            delivery_date = value.date()

        else:
            # Already a date object
            delivery_date = value

        today = datetime.today().date()
        two_weeks_from_today = today + timedelta(days=14)

        # Past date OR within next 2 weeks
        if delivery_date <= two_weeks_from_today:
            return delivery_date, False

        # More than 2 weeks away
        # Find Friday of that week
        friday = delivery_date + timedelta(
            days=(4 - delivery_date.weekday()) % 7
        )

        return f"Week Ending {friday.strftime('%d/%m/%Y')}", True

    def action_split_delivery_excel_report(self):

        download_date = datetime.now().strftime('%d%m%Y')
        deal_number = self.order_id.opportunity_id.name
        project_name = self.project_name

        file_name = f'{deal_number}_{project_name}_{download_date}.xlsx'
        fp = io.BytesIO()

        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})
        sheet = workbook.add_worksheet("Planning Screen Report")

        # ---------------- FORMATS ----------------

        project_header_fmt = workbook.add_format({
            'bold': True,
            'font_size': 22,
            'font_color': 'black',
            'bg_color': '#B7DEE8',
            'align': 'center',
            'valign': 'vcenter',
            'border': 2,
        })

        section_header_fmt = workbook.add_format({
            'bold': True,
            'font_size': 18,
            'bg_color': '#B7DEE8',
            'align': 'center',
            'valign': 'vcenter',
            'border': 2,
        })

        header_fmt = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True,
        })

        info_fmt = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'left',
        })

        value_fmt = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
        })
        value_info_fmt = workbook.add_format({
            'bold': False,
            'border': 1,
            'align': 'left',
        })

        left_fmt = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
        })

        date_fmt = workbook.add_format({
            'border': 1,
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'num_format': 'dd/mm/yyyy',
        })
        week_ending_fmt = workbook.add_format({
            'border': 1,
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
        })

        green_status_fmt = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#C6D9A8',
        })

        red_status_fmt = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#F4CCCC',
        })

        grey_status_fmt = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D9D9D9',
        })

        yellow_status_fmt = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#FFF2CC',
        })

        blue_status_fmt = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#9DC3E6',
        })
        grey_label_fmt = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'bg_color': '#D9D9D9',
        })

        status_mapping = {

            'off_track': (
                'Off Track',
                red_status_fmt
            ),

            'on_track': (
                'On Track',
                green_status_fmt
            ),

            'unscheduled': (
                'UnScheduled',
                grey_status_fmt
            ),

            'caution': (
                'Caution',
                yellow_status_fmt
            ),

            'fully_received': (
                'Fully Received',
                blue_status_fmt
            ),
        }

        # ---------------- CONFIG ----------------

        product_headers = [
            'Item #',
            'Code',
            'Product Name',
            'Quantity'
        ]

        product_widths = [
            14,
            23,
            55,
            10
        ]

        DS_FIELDS = [
            'Target Dispatch Date',
            'Target Delivery Date',
            'Target Install Start Date',
            'Target Install Complete Date',
        ]

        N_DS = min(max(self.mapped('stage_count'), default=1), 50) or 1

        LABEL_COL = len(product_headers)

        # IMPORTANT FIX
        # Stage Field sits directly after Quantity
        DS_START = LABEL_COL

        LAST_COL = DS_START + N_DS

        HDR = 5
        FIELD_R0 = HDR + 2
        DATA_ROW0 = HDR + 6

        # widths
        for col, width in enumerate(product_widths):
            sheet.set_column(col, col, width)

        sheet.set_column(DS_START, DS_START, 28)

        sheet.set_column(
            DS_START + 1,
            LAST_COL,
            23
        )

        # ---------------- TOP HEADER ----------------

        sheet.set_row(0, 45)

        sheet.merge_range(
            0,
            0,
            0,
            LAST_COL,
            "PROJECT REPORT",
            project_header_fmt
        )

        # ---------------- PROJECT INFORMATION ----------------

        # Column A will match Item # column width
        sheet.set_column(0, 0, 14)

        # PROJECT
        # ---------------- PROJECT INFORMATION ----------------

        project_name = self.project_name or ''

        deal_number_on_header = self.order_id.opportunity_id.odoo_deal_number_6digit or ''

        site_address = self.order_id.site_address or ''

        report_date = datetime.today().strftime("%d-%m-%Y")

        # PROJECT

        # DEAL NUMBER
        sheet.write(
            1,
            0,
            "DEAL NUMBER:",
            info_fmt
        )

        sheet.merge_range(
            1,
            1,
            1,
            LAST_COL,
            deal_number_on_header,
            value_info_fmt
        )

        # PROJECT
        sheet.write(
            2,
            0,
            "PROJECT:",
            info_fmt
        )

        sheet.merge_range(
            2,
            1,
            2,
            LAST_COL,
            project_name,
            value_info_fmt
        )

        # ADDRESS
        sheet.write(
            3,
            0,
            "ADDRESS:",
            info_fmt
        )

        sheet.merge_range(
            3,
            1,
            3,
            LAST_COL,
            site_address,
            value_info_fmt
        )

        # REPORT DATE
        sheet.write(
            4,
            0,
            "REPORT DATE:",
            info_fmt
        )

        sheet.merge_range(
            4,
            1,
            4,
            LAST_COL,
            report_date,
            value_info_fmt
        )

        # Row heights
        sheet.set_row(1, 30)
        sheet.set_row(2, 30)
        sheet.set_row(3, 30)
        sheet.set_row(4, 30)

        # ---------------- MAIN HEADER ----------------

        sheet.set_row(HDR, 45)

        sheet.merge_range(
            HDR,
            0,
            HDR,
            LABEL_COL - 1,
            "PRODUCT SUMMARY",
            section_header_fmt
        )

        sheet.merge_range(
            HDR,
            DS_START,
            HDR,
            LAST_COL,
            "DELIVERY STAGES",
            section_header_fmt
        )

        for col, name in enumerate(product_headers):
            sheet.merge_range(
                HDR + 1,
                col,
                HDR + 5,
                col,
                name,
                header_fmt
            )

        sheet.write(
            HDR + 1,
            DS_START,
            "",
            grey_status_fmt
        )

        for i in range(N_DS):
            sheet.write(
                HDR + 1,
                DS_START + i + 1,
                f"Delivery {i + 1}",
                header_fmt
            )

        for r, field in enumerate(DS_FIELDS):
            sheet.write(
                FIELD_R0 + r,
                DS_START,
                field,
                grey_label_fmt
            )
            sheet.set_row(
                FIELD_R0 + r,
                25
            )

        # ---------------- DELIVERY DATE VALUES ----------------

        planning_screen_data = self.fetch_planning_screen_data()

        for entry in planning_screen_data:

            if not entry.get('field_name'):
                continue

            try:
                stage_number = int(
                    entry['field_name'].split('_')[-1]
                )

            except:
                continue

            if stage_number > N_DS:
                continue

            # Delivery column
            delivery_col = DS_START + stage_number

            # Prepare dates
            dispatch_date, dispatch_is_week = self._format_delivery_date(
                entry.get('dispatch_date')
            )
            delivery_date, delivery_is_week = self._format_delivery_date(
                entry.get('delivery_date')
            )
            install_start_date, install_start_is_week = self._format_delivery_date(
                entry.get('install_start_date')
            )
            install_complete_date, install_complete_is_week = self._format_delivery_date(
                entry.get('install_complete_date')
            )

            # Dispatch Date
            sheet.write(
                FIELD_R0,
                delivery_col,
                dispatch_date,
                week_ending_fmt if dispatch_is_week else date_fmt
            )

            # Delivery Date
            sheet.write(
                FIELD_R0 + 1,
                delivery_col,
                delivery_date,
                week_ending_fmt if delivery_is_week else date_fmt
            )

            # Install Start Date
            sheet.write(
                FIELD_R0 + 2,
                delivery_col,
                install_start_date,
                week_ending_fmt if install_start_is_week else date_fmt
            )

            # Install Complete Date
            sheet.write(
                FIELD_R0 + 3,
                delivery_col,
                install_complete_date,
                week_ending_fmt if install_complete_is_week else date_fmt
            )

        # ---------------- DATA ----------------

        row = DATA_ROW0

        for rec in self:

            item = 1

            for line in rec.line_ids.sorted(lambda line: line.sequence):

                sheet.write(row, 0, item, value_fmt)
                sheet.write(row, 1, line.code or '', left_fmt)
                sheet.write(row, 2, line.product_name or '', left_fmt)
                sheet.write(row, 3, float(line.quantity or 0), value_fmt)
                sheet.write(row, DS_START, '', grey_label_fmt)  # NEW: grey + border under date-label column

                planning_data = self.fetch_planning_screen_data()

                stage_status_map = {}

                for entry in planning_data:

                    if entry.get('field_name'):
                        stage_number = int(
                            entry['field_name'].split('_')[-1]
                        )

                        stage_status_map[stage_number] = entry.get(
                            'delivery_stage_status',
                            ''
                        )

                for stage in range(1, N_DS + 1):

                    # check stage quantity
                    stage_qty = getattr(
                        line,
                        f"do_stage_{stage}",
                        0
                    )

                    if stage_qty and float(stage_qty) > 0:

                        status = stage_status_map.get(
                            stage,
                            ''
                        )

                        status_format = value_fmt

                        if status == "Off Track":
                            status_format = red_status_fmt

                        elif status == "On Track":
                            status_format = green_status_fmt

                        elif status == "Unscheduled":
                            status_format = grey_status_fmt

                        elif status == "Caution":
                            status_format = yellow_status_fmt

                        elif status == "Fully Received":
                            status_format = blue_status_fmt

                        sheet.write(
                            row,
                            DS_START + stage,
                            status,
                            status_format
                        )

                    else:

                        sheet.write(
                            row,
                            DS_START + stage,
                            '',
                            value_fmt
                        )

                item += 1
                sheet.set_row(
                    row,
                    30
                )

                row += 1

            # ================= CLAIM PREP SHEET =================
        cp = workbook.add_worksheet("Claim Prep")

        # currency formats
        currency = self.order_id.currency_id
        symbol = (currency.symbol or '').replace('"', '')
        money = f'"{symbol}"#,##0.00' if currency.position == 'before' else f'#,##0.00" {symbol}"'

        price_fmt = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'num_format': money,
        })
        price_hdr_fmt = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True,
        })
        total_label_fmt = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D9D9D9',
        })
        total_fmt = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D9D9D9',
            'num_format': money,
        })

        P1 = LAST_COL + 1  # Unit Price col
        P2 = LAST_COL + 2  # Total Price col

        # widths
        for col, width in enumerate(product_widths):
            cp.set_column(col, col, width)
        cp.set_column(DS_START, DS_START, 28)
        cp.set_column(DS_START + 1, LAST_COL, 23)
        # cp.set_column(P1, P2, 18)
        cp.set_column(P1, P2, 22)

        # top header + project info
        cp.set_row(0, 45)
        cp.merge_range(0, 0, 0, P2, "PROJECT REPORT", project_header_fmt)
        for r, (label, val) in enumerate([
            ("DEAL NUMBER:", deal_number_on_header),
            ("PROJECT:", project_name),
            ("ADDRESS:", site_address),
            ("REPORT DATE:", report_date),
        ], start=1):
            cp.write(r, 0, label, info_fmt)
            cp.merge_range(r, 1, r, P2, val, value_info_fmt)
            cp.set_row(r, 30)

        # section headers
        cp.set_row(HDR, 45)
        cp.merge_range(HDR, 0, HDR, LABEL_COL - 1, "PRODUCT SUMMARY", section_header_fmt)
        cp.merge_range(HDR, DS_START, HDR, LAST_COL, "DELIVERY STAGES", section_header_fmt)
        cp.merge_range(HDR, P1, HDR, P2, "COST", section_header_fmt)

        # column headers
        for col, name in enumerate(product_headers):
            cp.merge_range(HDR + 1, col, HDR + 5, col, name, header_fmt)
        cp.merge_range(HDR + 1, P1, HDR + 5, P1, f"Cost Per Unit({symbol})", price_hdr_fmt)
        cp.merge_range(HDR + 1, P2, HDR + 5, P2, f"Total Cost({symbol})", price_hdr_fmt)

        cp.write(HDR + 1, DS_START, "", grey_status_fmt)
        for i in range(N_DS):
            cp.write(HDR + 1, DS_START + i + 1, f"Delivery {i + 1}", header_fmt)
        for r, field in enumerate(DS_FIELDS):
            cp.write(FIELD_R0 + r, DS_START, field, grey_label_fmt)
            cp.set_row(FIELD_R0 + r, 25)

        # delivery dates + status map
        status_map = {}
        for entry in planning_screen_data:
            try:
                stage = int(entry['field_name'].split('_')[-1])
            except (KeyError, AttributeError, ValueError):
                continue
            status_map[stage] = entry.get('delivery_stage_status', '')
            if stage > N_DS:
                continue
            for r, key in enumerate(['dispatch_date', 'delivery_date', 'install_start_date', 'install_complete_date']):
                val, is_week = self._format_delivery_date(entry.get(key))
                cp.write(FIELD_R0 + r, DS_START + stage, val, week_ending_fmt if is_week else date_fmt)

        status_fmt = {
            'Off Track': red_status_fmt,
            'On Track': green_status_fmt,
            'Unscheduled': grey_status_fmt,
            'Caution': yellow_status_fmt,
            'Fully Received': blue_status_fmt,
        }

        # data rows
        r = DATA_ROW0
        grand_total = 0.0
        for rec in self:
            for item, line in enumerate(rec.line_ids.sorted(lambda l:l.sequence), start=1):
                qty = float(line.quantity or 0)
                unit_price = float(line.order_line_id.price_unit or 0)  # <-- change if your field name differs
                line_total = qty * unit_price
                grand_total += line_total

                cp.write(r, 0, item, value_fmt)
                cp.write(r, 1, line.code or '', left_fmt)
                cp.write(r, 2, line.product_name or '', left_fmt)
                cp.write(r, 3, qty, value_fmt)
                cp.write(r, DS_START, '', grey_label_fmt)

                for stage in range(1, N_DS + 1):
                    if float(getattr(line, f"do_stage_{stage}", 0) or 0) > 0:
                        status = status_map.get(stage, '')
                        cp.write(r, DS_START + stage, status, status_fmt.get(status, value_fmt))
                    else:
                        cp.write(r, DS_START + stage, '', value_fmt)

                cp.write(r, P1, unit_price, price_fmt)
                cp.write(r, P2, line_total, price_fmt)
                cp.set_row(r, 30)
                r += 1

        # grand total
        cp.set_row(r, 30)
        cp.write(r, P1, "TOTAL", total_label_fmt)
        cp.write(r, P2, grand_total, total_fmt)
        # ================= CLAIM PREP SHEET END =================

        workbook.close()

        fp.seek(0)

        excel_file = base64.b64encode(fp.read())
        fp.close()

        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': excel_file,
            'mimetype':
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _fmt_ddmmyy(self, value):
        """Date/Datetime -> 'DD/MM/YY', no time. False/None -> ''."""
        if not value:
            return ''
        user_tz = self.env.user.tz or 'UTC'
        tz = pytz.timezone(user_tz)
        local_dt = UTC.localize(value).astimezone(tz)
        return local_dt.strftime('%d/%m/%y')

    def fetch_planning_screen_data(self):
        planning_screen_extra_data = []
        delivery_stage_name = {'unscheduled': 'Unscheduled', 'on_track': 'On Track', 'caution': 'Caution',
                               'off_track': 'Off Track', 'fully_received': 'Fully Received'}
        project_quote_reference = self.order_id.burgtec_quote_reference
        all_tickets = self.env['hubspot.ticket.data'].search(
            [('delivery_stage_number', 'ilike', project_quote_reference)])
        for ticket in all_tickets:
            stage = ticket.delivery_stage_number
            if stage:
                delivery_stage = self.env['sale.order'].sudo().search([('burgtec_quote_reference', '=', stage)],
                                                                      limit=1)
                if delivery_stage:
                    delivery_stage_status = delivery_stage.delivery_status_tracking
                    try:
                        stage_num = int(stage.split('-')[-1])
                        field_name = f"do_stage_{stage_num}"
                    except (ValueError, IndexError):
                        field_name = None
                    planning_screen_extra_data.append({
                        'field_name': field_name,
                        'ticket_number': ticket.delivery_stage_number or '',
                        'dispatch_date': self._fmt_ddmmyy(ticket.scheduled_dispatch),
                        'delivery_date': self._fmt_ddmmyy(ticket.scheduled_delivers_date),
                        'install_start_date': self._fmt_ddmmyy(ticket.scheduled_install_date),
                        'install_complete_date': self._fmt_ddmmyy(ticket.scheduled_install_complete_date),
                        'delivery_stage_status': delivery_stage_name[
                            delivery_stage_status] if delivery_stage_status else '',

                    })
        return planning_screen_extra_data

    @api.depends('stage_count', *(f'line_ids.do_stage_{i}' for i in range(1, 51)), 'zone_type', 'line_ids')
    def _compute_delivery_stage_cost_lines(self):
        for record in self:
            total_qty = 0
            total_installation_cost = 0
            total_delivery_cost = 0
            if record.stage_count > 0:
                for line in record.delivery_stage_cost_line_ids:
                    record.update(
                        {
                            'delivery_stage_cost_line_ids': [Command.delete(line.id)]
                        }
                    )
                for count in range(record.stage_count):
                    total_qty = 0
                    total_installation_cost = 0
                    total_delivery_cost = 0
                    for planning_line in record.line_ids:
                        stage_fields = [f for f in planning_line._fields if f == f"do_stage_{count + 1}"]
                        if record.zone_type and record.zone_type == 'zone1':
                            total_installation_cost += (sum(getattr(planning_line, f) or 0 for f in
                                                            stage_fields) * planning_line.product_variant_id.variant_delivery_code_selection_id.installation_cost)
                            total_delivery_cost += (sum(getattr(planning_line, f) or 0 for f in
                                                        stage_fields) * planning_line.product_variant_id.variant_delivery_code_selection_id.delivery_code_cost)
                        elif record.zone_type and record.zone_type == 'zone2':
                            total_installation_cost += (sum(getattr(planning_line, f) or 0 for f in
                                                            stage_fields) * planning_line.product_variant_id.variant_delivery_code_selection_id.zone2_installation_cost)
                            total_delivery_cost += (sum(getattr(planning_line, f) or 0 for f in
                                                        stage_fields) * planning_line.product_variant_id.variant_delivery_code_selection_id.zone2_delivery_cost)
                        elif record.zone_type and record.zone_type == 'zone3':
                            total_installation_cost += (sum(getattr(planning_line, f) or 0 for f in
                                                            stage_fields) * planning_line.product_variant_id.variant_delivery_code_selection_id.zone3_installation_cost)
                            total_delivery_cost += (sum(getattr(planning_line, f) or 0 for f in
                                                        stage_fields) * planning_line.product_variant_id.variant_delivery_code_selection_id.zone3_delivery_cost)
                        total_qty += sum(getattr(planning_line, f) or 0 for f in stage_fields)
                    record.delivery_stage_cost_line_ids = [
                        # Command.clear(),
                        Command.create({
                            'name': _('Delivery Stage ') + str(count + 1),
                            'ds_quantity': total_qty,
                            'ds_installation_cost': total_installation_cost,
                            'ds_delivery_cost': total_delivery_cost

                        }),
                    ]
            else:
                record.delivery_stage_cost_line_ids = False

    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.order_id.burgtec_quote_reference} Planning Screen"


class PlanningScreenLineExt(models.Model):
    _inherit = 'planning.screen.line'

    line_group_name = fields.Char(related='order_line_id.line_group_name')
    line_section_name = fields.Char(related='order_line_id.line_section_name')
    line_group_id_value = fields.Char(related='order_line_id.line_group_id_value')
    line_section_id_value = fields.Char(related='order_line_id.line_section_id_value')
    code = fields.Char(related='order_line_id.line_section_name', string='code')
    product_name = fields.Char(related='order_line_id.custom_product_name', string='Product Name')

    item = fields.Integer(string="Item", readonly=True)
    lead_time = fields.Text(string="Lead Time")
    requested_delivery_date = fields.Date(string="Requested Delivery Date")
    approval_required_by = fields.Date(string="Approval Required By")
    approval_method = fields.Selection([
        ('shop_drawing', 'Shop Drawing'),
        ('approved_quote', 'Approved Quote'),
        ('spec_sheet', 'Spec Sheet')
    ], string="Approval Method")
    approval_status = fields.Selection([
        ('awaiting_approval', 'Awaiting Approval'),
        ('awaiting_revision', 'Awaiting Revision'),
        ('approved_with_comment', 'Approved with Comment'),
        ('fully_approved', 'Fully Approved By Customer')
    ], string="Approval Status")
    line_item_status = fields.Selection([
        ('unschedule', 'Unschedule'),
        ('sales_sales_court', 'Sales-Sales Court'),
        ('sales_customer_court', 'Sales-Customer Court'),
        ('technical_initial_check', 'Technical-Initial Check'),
        ('technical_final_check', 'Technical-Final Check'),
        ('technical_purchasing', 'Technical-Purchasing'),
        ('projects_awaiting_delivery', 'Projects-Awaiting Delivery'),
        ('projects_delivered', 'Projects-Delivered'),
        ('projects_installed', 'Projects-Installed'),
    ], string="Line Item Status", default='unschedule')
    approval_comments = fields.Text(string="Approval Comments")
    sales_comments = fields.Text(string="Sales Comments")
    technical_comments = fields.Text(string="Technical Comments")
    delivery_comments = fields.Text(string="Delivery Comments")
    do_stage_1 = fields.Integer("DS1")
    do_stage_2 = fields.Integer("DS2")
    do_stage_3 = fields.Integer("DS3")
    do_stage_4 = fields.Integer("DS4")
    do_stage_5 = fields.Integer("DS5")
    do_stage_6 = fields.Integer("DS6")
    do_stage_7 = fields.Integer("DS7")
    do_stage_8 = fields.Integer("DS8")
    do_stage_9 = fields.Integer("DS9")
    do_stage_10 = fields.Integer("DS10")
    do_stage_11 = fields.Integer("DS11")
    do_stage_12 = fields.Integer("DS12")
    do_stage_13 = fields.Integer("DS13")
    do_stage_14 = fields.Integer("DS14")
    do_stage_15 = fields.Integer("DS15")
    do_stage_16 = fields.Integer("DS16")
    do_stage_17 = fields.Integer("DS17")
    do_stage_18 = fields.Integer("DS18")
    do_stage_19 = fields.Integer("DS19")
    do_stage_20 = fields.Integer("DS20")
    do_stage_21 = fields.Integer("DS21")
    do_stage_22 = fields.Integer("DS22")
    do_stage_23 = fields.Integer("DS23")
    do_stage_24 = fields.Integer("DS24")
    do_stage_25 = fields.Integer("DS25")
    do_stage_26 = fields.Integer("DS26")
    do_stage_27 = fields.Integer("DS27")
    do_stage_28 = fields.Integer("DS28")
    do_stage_29 = fields.Integer("DS29")
    do_stage_30 = fields.Integer("DS30")
    do_stage_31 = fields.Integer("DS31")
    do_stage_32 = fields.Integer("DS32")
    do_stage_33 = fields.Integer("DS33")
    do_stage_34 = fields.Integer("DS34")
    do_stage_35 = fields.Integer("DS35")
    do_stage_36 = fields.Integer("DS36")
    do_stage_37 = fields.Integer("DS37")
    do_stage_38 = fields.Integer("DS38")
    do_stage_39 = fields.Integer("DS39")
    do_stage_40 = fields.Integer("DS40")
    do_stage_41 = fields.Integer("DS41")
    do_stage_42 = fields.Integer("DS42")
    do_stage_43 = fields.Integer("DS43")
    do_stage_44 = fields.Integer("DS44")
    do_stage_45 = fields.Integer("DS45")
    do_stage_46 = fields.Integer("DS46")
    do_stage_47 = fields.Integer("DS47")
    do_stage_48 = fields.Integer("DS48")
    do_stage_49 = fields.Integer("DS49")
    do_stage_50 = fields.Integer("DS50")

    approval_status_readonly = fields.Boolean(
        compute='_compute_approval_status_readonly',
        store=True,
        copy=False
    )
    is_fully_approved = fields.Boolean(
        string='Fully Approved',
        default=False)

    @api.depends(
        *(f'do_stage_{i}' for i in range(1, 51)),  # the line quantities
        *(f'planning_screen_id.do_{i}_status' for i in range(1, 51)),  # the header statuses
        'is_fully_approved'  # line approval status
    )
    def _compute_approval_status_readonly(self):
        for rec in self:
            header = rec.planning_screen_id
            # check each stage: if line quantity > 0 and header status is confirmed
            readonly_flag = False
            for i in range(1, 51):
                qty = getattr(rec, f'do_stage_{i}', 0.0) or 0.0
                status = getattr(header, f'do_{i}_status', False)
                if qty > 0 and status == 'planned':
                    readonly_flag = True
                    break  # no need to continue once we found one

            # only make readonly if line already has approval_status value
            rec.approval_status_readonly = bool(readonly_flag and rec.is_fully_approved)

    @api.onchange('is_fully_approved')
    def onchange_is_fully_approved(self):
        current_user = self.env.user
        # Security check — only allow the planning admin to approve
        if not current_user.has_group('quotation_type_customization.group_planning_screen_admin'):
            raise UserError(_('Only the Planning Screen Admin can approve or unapprove the product!'))
        for line in self:
            if not line._origin.is_fully_approved:
                message = line._check_for_archieved_parent_or_component()
                if message:
                    raise ValidationError(message)
            sale_order = line.planning_screen_id.order_id
            if not sale_order:
                continue
            # Find the related sale order line
            sale_order_line = sale_order.order_line.filtered(lambda l: l.id == line.order_line_id.id)
            if not sale_order_line:
                continue
            # Determine the approval status
            approval_status = line.is_fully_approved
            # Update Sale Order Line approval
            sale_order_line.sudo().write({'is_product_fully_approved': approval_status})
            # Find respective BOM parent line
            bom_parent_line = sale_order.bom_component_id.component_line_ids.filtered(
                lambda l: l.is_parent and l.order_line_id == sale_order_line
            )
            if bom_parent_line:
                parent_line = bom_parent_line[0]
                parent_line.sudo().write({'is_product_fully_approved': approval_status})
                child_lines = sale_order.bom_component_id.component_line_ids.filtered(
                    lambda
                        l: l.parent_product_id.id == parent_line.product_id.product_tmpl_id.id and l.order_line_id.id == parent_line.order_line_id.id and not l.is_parent and not l.display_type
                )
                child_lines.sudo().write({'is_product_fully_approved': approval_status})

    def _check_for_archieved_parent_or_component(self):
        self.ensure_one()
        if not self.order_line_id.product_id.active:
            return f"You Cannot Approve!! Because Product '{self.product_id.display_name}' is Archived."
        sale_line_product_id = self.order_line_id.product_id
        bom_component_lines = self.order_line_id.order_id.bom_component_id.component_line_ids
        if bom_component_lines:
            child_lines = bom_component_lines.filtered(
                lambda l: not l.is_parent and l.parent_product_id == sale_line_product_id.product_tmpl_id
                          and l.order_line_id == self.order_line_id)
            archived_components = child_lines.filtered(lambda l: not l.product_id.active)
            if archived_components:
                names = '\n- '.join(archived_components.mapped('product_id.display_name'))
                return f"You Cannot Approve!! Beacuse The following component(s) of Product '{self.product_id.display_name}' are Archived:\n- {names}"
        return None

    @api.depends(*(f'do_stage_{i}' for i in range(1, 51)),
                 *(f'planning_screen_id.do_{i}_status' for i in range(1, 51)), 'quantity')
    def _compute_total_available_qty(self):

        for line in self:
            # Collect all fields that start with "do_stage_"
            stage_fields = [f for f in line._fields if f.startswith("do_stage_")]
            # Sum their values (default to 0 if False/None)
            total_stages = sum(getattr(line, f) or 0 for f in stage_fields)
            # Compute available quantity
            if line.quantity and total_stages:
                line.total_available_quantity = line.quantity - total_stages

            else:
                line.total_available_quantity = line.quantity
            # Validation
            if line.total_available_quantity < 0:
                raise ValidationError(
                    f"You Cannot Enter more Quantity than the Original Quantity in Planning Screen Line!"
                )
