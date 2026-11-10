from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PlanningScreenExt(models.Model):
    _inherit = 'planning.screen'

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
                        'opportunity_id': rec.order_id.opportunity_id.id if rec.order_id.opportunity_id else False,
                        'system_revision': rec.order_id.system_revision,
                        'hubspot_ticket_id': rec._find_associated_hubspot_ticket(stage_number),
                        'location': rec.order_id.location,
                        'project_name': rec.order_id.project_name,
                        'site_address': rec.order_id.site_address,

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

    def _find_associated_hubspot_ticket(self, stage_number):
        for rec in self:
            project_quote_ref = f"{rec.order_id.new_sale_order_number}-{stage_number.zfill(3)}"
            if project_quote_ref:
                respective_ticket = self.env['hubspot.ticket.data'].search(
                    [('delivery_stage_number', '=', project_quote_ref)], limit=1)
                if respective_ticket:
                    return respective_ticket.id
                else:
                    return None
