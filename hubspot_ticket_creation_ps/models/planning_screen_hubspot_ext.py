from odoo import api, fields, models, Command, _
import requests
import re
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PlanningScreenExt(models.Model):
    _inherit = 'planning.screen'

    do_1_status = fields.Selection(selection_add=[('new', 'New')])
    do_2_status = fields.Selection(selection_add=[('new', 'New')])
    do_3_status = fields.Selection(selection_add=[('new', 'New')])
    do_4_status = fields.Selection(selection_add=[('new', 'New')])
    do_5_status = fields.Selection(selection_add=[('new', 'New')])
    do_6_status = fields.Selection(selection_add=[('new', 'New')])
    do_7_status = fields.Selection(selection_add=[('new', 'New')])
    do_8_status = fields.Selection(selection_add=[('new', 'New')])
    do_9_status = fields.Selection(selection_add=[('new', 'New')])
    do_10_status = fields.Selection(selection_add=[('new', 'New')])
    do_11_status = fields.Selection(selection_add=[('new', 'New')])
    do_12_status = fields.Selection(selection_add=[('new', 'New')])
    do_13_status = fields.Selection(selection_add=[('new', 'New')])
    do_14_status = fields.Selection(selection_add=[('new', 'New')])
    do_15_status = fields.Selection(selection_add=[('new', 'New')])
    do_16_status = fields.Selection(selection_add=[('new', 'New')])
    do_17_status = fields.Selection(selection_add=[('new', 'New')])
    do_18_status = fields.Selection(selection_add=[('new', 'New')])
    do_19_status = fields.Selection(selection_add=[('new', 'New')])
    do_20_status = fields.Selection(selection_add=[('new', 'New')])
    do_21_status = fields.Selection(selection_add=[('new', 'New')])
    do_22_status = fields.Selection(selection_add=[('new', 'New')])
    do_23_status = fields.Selection(selection_add=[('new', 'New')])
    do_24_status = fields.Selection(selection_add=[('new', 'New')])
    do_25_status = fields.Selection(selection_add=[('new', 'New')])
    do_26_status = fields.Selection(selection_add=[('new', 'New')])
    do_27_status = fields.Selection(selection_add=[('new', 'New')])
    do_28_status = fields.Selection(selection_add=[('new', 'New')])
    do_29_status = fields.Selection(selection_add=[('new', 'New')])
    do_30_status = fields.Selection(selection_add=[('new', 'New')])
    do_31_status = fields.Selection(selection_add=[('new', 'New')])
    do_32_status = fields.Selection(selection_add=[('new', 'New')])
    do_33_status = fields.Selection(selection_add=[('new', 'New')])
    do_34_status = fields.Selection(selection_add=[('new', 'New')])
    do_35_status = fields.Selection(selection_add=[('new', 'New')])
    do_36_status = fields.Selection(selection_add=[('new', 'New')])
    do_37_status = fields.Selection(selection_add=[('new', 'New')])
    do_38_status = fields.Selection(selection_add=[('new', 'New')])
    do_39_status = fields.Selection(selection_add=[('new', 'New')])
    do_40_status = fields.Selection(selection_add=[('new', 'New')])
    do_41_status = fields.Selection(selection_add=[('new', 'New')])
    do_42_status = fields.Selection(selection_add=[('new', 'New')])
    do_43_status = fields.Selection(selection_add=[('new', 'New')])
    do_44_status = fields.Selection(selection_add=[('new', 'New')])
    do_45_status = fields.Selection(selection_add=[('new', 'New')])
    do_46_status = fields.Selection(selection_add=[('new', 'New')])
    do_47_status = fields.Selection(selection_add=[('new', 'New')])
    do_48_status = fields.Selection(selection_add=[('new', 'New')])
    do_49_status = fields.Selection(selection_add=[('new', 'New')])
    do_50_status = fields.Selection(selection_add=[('new', 'New')])

    show_planned_stages = fields.Boolean(
        string="Show Planned Stages",
        copy=False,
        help="When checked, DS columns whose status is Planned are visible.",
    )

    def action_toggle_planned_stages(self):
        self.ensure_one()
        self.show_planned_stages = not self.show_planned_stages
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}

    def _get_hubspot_config(self):
        ICP = self.env['ir.config_parameter'].sudo()
        token = ICP.get_param('burgtec_hubspot_customization.hubspot_integrations_token')
        base_url = ICP.get_param('burgtec_hubspot_customization.hubspot_base_url')

        if not token:
            raise UserError(_('HubSpot Integration Token is not configured.'))

        return {
            'token': token,
            'base_url': base_url.rstrip('/')
        }

    def _hubspot_create_new_ticket(self, properties):
        config = self._get_hubspot_config()
        url = f"{config['base_url']}/crm/v3/objects/tickets"

        payload = {'properties': properties}
        headers = {
            "Authorization": f"Bearer {config['token']}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return {'success': True, 'ticket_id': data.get("id"), 'data': data}
        except requests.exceptions.RequestException as e:
            error_msg = getattr(e.response, 'text', str(e)) if hasattr(e, 'response') else str(e)
            return {'success': False, 'error': error_msg}

    def _hubspot_update_existing_ticket(self, ticket_id, properties):
        config = self._get_hubspot_config()
        url = f"{config['base_url']}/crm/v3/objects/tickets/{ticket_id}"
        headers = {
            'Authorization': f'Bearer {config["token"]}',
            'Content-Type': 'application/json'
        }
        payload = {'properties': properties}

        try:
            response = requests.patch(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return {'success': True, 'ticket_id': data.get('id'), 'data': data}
        except requests.exceptions.RequestException as e:
            error_msg = getattr(e.response, 'text', str(e)) if hasattr(e, 'response') else str(e)
            return {'success': False, 'error': error_msg}

    def _prepare_hubspot_ticket_properties(self, field_name):
        order_ref = ''
        config = self._get_hubspot_config()
        url = f"{config['base_url']}/crm/v3/pipelines/tickets"
        headers = {
            'Authorization': f'Bearer {config["token"]}',
            'Content-Type': 'application/json'
        }
        hs_pipeline = False
        hs_pipeline_stage = False
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            pipelines = data.get("results", [])
            for pipeline in pipelines:
                if pipeline:
                    hs_pipeline = pipeline['id']
                    break
                # print(f"Pipeline ID: {pipeline['id']}, Name: {pipeline['label']}")
            for stage in pipeline.get("stages", []):
                if stage:
                    hs_pipeline_stage = stage['id']
                    break
                    # print(f"  Stage ID: {stage['id']}, Label: {stage['label']}")
            # return None

        if hasattr(self, 'order_id') and self.order_id:
            order_ref = self.order_id.burgtec_quote_reference or self.order_id.name or ''
        if field_name:
            deal_stage_number = f"{int(field_name.split('_')[1]):03d}"

        subject = f"{order_ref}-{deal_stage_number}" if order_ref else f"{self.display_name}-{field_name}"
        indented, early_procurement_supplier = (
            self._get_indented_and_early_procurement_supplier_checks(field_name)
        )
        return {
            'subject': subject,
            'hs_pipeline': hs_pipeline,
            'hs_pipeline_stage': hs_pipeline_stage,
            'in_odoo': True,
            'delivery_stage_number': f'{order_ref}-{deal_stage_number}',
            'indented': indented,
            'early_procurement_supplier': early_procurement_supplier,
        }

    def action_handle_hubspot_ticket_creation(self, selected_value, field_name):
        self.ensure_one()
        sale_order_burgtec_ref = self.order_id.burgtec_quote_reference
        deal_stage_number_second_half = f"{int(field_name.split('_')[1]):03d}"
        delivery_stage_number = f'{sale_order_burgtec_ref}-{deal_stage_number_second_half}'

        HubspotTicket = self.env['hubspot.ticket.data']
        existing_ticket = HubspotTicket.search([
            ('delivery_stage_number', '=', delivery_stage_number)
        ], limit=1)
        properties = self._prepare_hubspot_ticket_properties(field_name)

        if existing_ticket:
            # result = self._hubspot_update_existing_ticket(existing_ticket.hubspot_ticket_id, properties)
            return {
                'success': True,
                'message': _(f'Ticket Already Exists! For Delivery Stage Number {delivery_stage_number}'),
            }

        else:
            result = self._hubspot_create_new_ticket(properties)
            return {
                'success': result['success'],
                'message': _(f'Ticket Created Successfully! For Delivery Stage Number {delivery_stage_number}') if
                result['success'] else result['error'],
                'ticket_id': result.get('ticket_id')
            }

    def action_handle_do_stage(self, selectedValue, fieldName):
        current_user = self.env.user
        try:
            match = re.search(r'do_stage_(\d+)', fieldName)
            stage_number = match.group(1)
            target_field = f"do_{stage_number}_status"

            for rec in self:
                stage_field = f"do_stage_{stage_number}"
                # Get lines with quantity for this specific stage
                if not rec.line_ids:
                    raise UserError(
                        'No Product Lines on Planning Screen !!')
                lines_with_qty = []
                for line in rec.line_ids:
                    stage_qty = getattr(line, stage_field, 0)
                    if stage_qty > 0:
                        lines_with_qty.append(line)
                        # Check if this line is fully approved
                        # if not line.is_fully_approved:
                        #     raise UserError(
                        #         f'Product "{line.product_id.name}" in DO_Stage_{stage_number} is not Fully Approved')
                if not lines_with_qty and not selectedValue == 'draft':
                    raise UserError(f'DO_Stage_{stage_number} has No Quantity Values!')
            if target_field in self._fields:
                current_state = self[target_field]
                existing_ticket = self.check_existing_ticket(target_field)
                if not existing_ticket and current_state == 'draft' and selectedValue == 'planned' and not current_user.has_group(
                        'quotation_type_customization.group_planning_screen_admin'):
                    return {
                        'success': False,
                        'message': _(
                            'Access Denied to move from "Draft" to "Planned" Directly. Please set the status to "New" first to Create the Hubspot Ticket !!.'),
                    }
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
                    if current_value == 'new' and selectedValue == 'new':
                        result = record.action_handle_hubspot_ticket_creation(selectedValue, target_field)
                        return result
                    if current_value == 'draft' and selectedValue == 'draft':
                        return {
                            'success': 'State To Draft',
                            'message': _('State Changed To Draft!'),
                        }
        except UserError:
            # Re-raise UserError as-is to preserve the original message
            raise

    def check_existing_ticket(self, targetField):
        self.ensure_one()
        burgtec_ref_first_6_didgit = self.order_id.burgtec_quote_reference.split("-")[0].strip()

        deal_stage_number_second_half = f"{targetField.split('_')[1].zfill(3)}"
        delivery_stage_number = f'{burgtec_ref_first_6_didgit}-{deal_stage_number_second_half}'

        HubspotTicket = self.env['hubspot.ticket.data']
        existing_ticket = HubspotTicket.search([
            ('delivery_stage_number', '=', delivery_stage_number)
        ], limit=1)
        if existing_ticket:
            return True
        else:
            return False

    def _get_indented_and_early_procurement_supplier_checks(self, field_name):
        """Return indented and early procurement supplier checks for the ticket."""
        indented = False
        early_procurement_supplier = False

        stage_number = int(field_name.split('_')[1])
        quantity_field = f'do_stage_{stage_number}'

        # Check planning screen lines for the current delivery stage.
        stage_lines = self.line_ids.filtered(
            lambda line: (
                    line[quantity_field] > 0
                    and line.is_fully_approved
            )
        )

        # If any approved line with quantity is indented.
        indented = any(
            line.has_indented_components
            for line in stage_lines
        )

        # Get order lines from the planning screen lines.
        order_line_ids = stage_lines.mapped('order_line_id')

        # Check BOM component lines related to those order lines.
        bom_component = self.order_id.bom_component_id
        component_line_ids = bom_component.component_line_ids

        for order_line in order_line_ids:
            bom_lines = component_line_ids.filtered(
                lambda line: (
                        line.order_line_id == order_line
                        and not line.display_type
                )
            )

            if any(line.is_early_procurement_supplier for line in bom_lines):
                early_procurement_supplier = True
                break

        return indented, early_procurement_supplier

