import logging
from pytz import timezone, UTC
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests

_logger = logging.getLogger(__name__)


class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    hubspot_ticket_id = fields.Many2one('hubspot.ticket.data', string="Hubspot Ticket Reference")
    hubspot_ticket_schedule_dispatch = fields.Datetime(string='Schedule Dispatch',
                                                       compute="_compute_hubspot_ticket_fields", store=True)
    hubspot_ticket_status = fields.Char(related='hubspot_ticket_id.ticket_status', string='Ticket Status', store=True)

    latest_eta_dispatch_date_diff = fields.Float(compute="_compute_latest_eta_dispatch_date_diff", store=True)

    delay_risk = fields.Char(compute="_compute_delay_risk", store=True)
    is_delay_risk = fields.Boolean(compute="_compute_delay_risk", store=True)

    scheduled_delivers_date = fields.Datetime(string='Schedule Delivers Date', compute="_compute_hubspot_ticket_fields",
                                              store=True)
    scheduled_install_date = fields.Datetime(string='Schedule Install Date', compute="_compute_hubspot_ticket_fields",
                                             store=True)
    scheduled_install_complete_date = fields.Datetime(string='Schedule Install Complete Date',
                                                      compute="_compute_hubspot_ticket_fields", store=True)
    ticket_status = fields.Char(string='Hubspot Ticket Status', compute="_compute_hubspot_ticket_fields", store=True)
    is_backorder_registered = fields.Boolean(string='Backorder Registered', compute="_compute_hubspot_ticket_fields",
                                             store=True)
    qr_url = fields.Char('HubSpot URL')

    delivery_status_tracking = fields.Selection(selection=[
        ('unscheduled', 'Un-scheduled'),
        ('on_track', 'On Track'),
        ('caution', 'Caution'),
        ('off_track', 'Off Track'),
        ('fully_received', 'Fully Received'),
    ],
        compute='_compute_delivery_status_tracking',
        help="""
    Un-scheduled ➔ Either Schedule Dispatch or Latest ETA Date field is Not Set or Burgtec Po status is not set in any of the purchase order apart from delivery.
    On Track ➔ ETA vs Dispatch date difference is 2 days or greater than 2 days AND all POs Last Weekly Update Date is within 7 days or less of the current moment.
    Caution ➔ ETA vs Dispatch date difference is 0 or 1 days.
    Off Track ➔ ETA vs Dispatch date difference is Negative OR any PO(s) Last Weekly Update Date is greater than 7 days of the current moment.
    Fully Received ➔ If child pos other than delivery po, are fully received or advance stages from fully received inclusive.
    """
    )

    since_earliest_po_weekly_update = fields.Integer(compute="compute_since_earliest_po_weekly_update")

    # @api.depends('latest_eta_dispatch_date_diff', 'latest_eta_date', 'hubspot_ticket_schedule_dispatch','purchase_order_id.child_purchase_order_ids.last_po_weekly_update_date')
    def _compute_delivery_status_tracking(self):
        fully_received = False
        today = fields.Date.today()
        for record in self:
            if record.quote_type != 'delivery_stage' or not record.purchase_order_id.child_purchase_order_ids:
                record.delivery_status_tracking = False
                continue
            overdue = False
            child_pos = record.purchase_order_id.child_purchase_order_ids
            child_pos = child_pos.filtered(
                lambda po: po.partner_id.name != 'Burgtec Delivery' and po.burgtec_po_status in ('draft_to_approve',
                                                                                                'draft_to_sent', 'sent',
                                                                                                'await_receipt',
                                                                                                'received_partial') or po.partner_id.name != 'Burgtec Delivery' and not po.burgtec_po_status)
            if False in child_pos.mapped('burgtec_po_status'):
                record.delivery_status_tracking = 'unscheduled'
                continue
            days = record.latest_eta_dispatch_date_diff
            if not child_pos:
                record.delivery_status_tracking = 'fully_received'
                continue
            if child_pos:
                # fully_received = all(
                #     po.burgtec_po_status not in ('draft_to_approve', 'draft_to_sent', 'sent', 'await_receipt',
                #                                  'received_partial') for po in child_pos)
                all_pos_have_update_date = all(
                    po.last_po_weekly_update_date
                    for po in child_pos)
                if not all_pos_have_update_date:
                    overdue = True
                else:
                    largest_weekly_date = min(
                        child_pos.mapped('last_po_weekly_update_date')
                    )
                    if (today - largest_weekly_date.date()).days > 7:
                        overdue = True
            # if fully_received:
            #     record.delivery_status_tracking = 'fully_received'
            if not record.latest_eta_date or not record.hubspot_ticket_schedule_dispatch:
                record.delivery_status_tracking = 'unscheduled'  # blank
            elif days < 0 or overdue:
                record.delivery_status_tracking = 'off_track'  # negative → red
            elif days < 2:
                record.delivery_status_tracking = 'caution'  # 0 or 1 → orange
            else:
                record.delivery_status_tracking = 'on_track'  # >= 2 → green
            # record.action_update_hubspot_ticket()

    @api.onchange('hubspot_ticket_id')
    def onchange_ticket_id(self):
        for rec in self:
            rec.hubspot_ticket_schedule_dispatch = rec.hubspot_ticket_id.scheduled_dispatch if rec.hubspot_ticket_id else False

    def action_attach_hubspot_ticket_and_dispatch_date(self):
        for quote in self:
            # Restrict action usage
            if quote.quote_type in ['sales_quote', 'project_quote']:
                raise ValidationError('You can only run this action on Delivery Stage')

            if quote.quote_type == 'delivery_stage':

                # Decide which field to use
                stage_value = False
                # if quote.burgtec_quote_reference and not quote.is_old_data:
                if quote.new_sale_order_number and not quote.is_old_data:
                    # stage_value = quote.burgtec_quote_reference
                    stage_value = quote.new_sale_order_number
                elif quote.delivery_stage and quote.is_old_data:
                    split_parts = quote.delivery_stage.split("-")
                    stage_value = '-'.join(split_parts[:2]).strip() if len(split_parts) > 1 else split_parts[0].strip()
                # If no stage value, nothing to process
                if not stage_value:
                    continue
                # Search ticket
                matching_ticket = self.env['hubspot.ticket.data'].search([
                    ('delivery_stage_number', '=', stage_value)
                ], limit=1)
                # Ticket found
                if matching_ticket:
                    _logger.info("Matching Ticket Found For Delivery Stage %s ", stage_value)
                    quote.sudo().write({
                        'hubspot_ticket_id': matching_ticket.id,
                    })
                    # if quote.purchase_order_id:
                    #     quote.purchase_order_id.sudo().write({
                    #         'hubspot_dispatch_date': matching_ticket.scheduled_dispatch
                    #     })
                    #     if quote.purchase_order_id.child_purchase_order_ids:
                    #         quote.purchase_order_id.child_purchase_order_ids.sudo().write({
                    #             'hubspot_dispatch_date': matching_ticket.scheduled_dispatch
                    #         })
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    }
                # Ticket NOT found
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Note',
                        'message': f"No Matching HubSpot Ticket with Delivery Stage Number# {stage_value}",
                    }
                }

        return True

    def action_attach_hubspot_ticket_and_dispatch_date_cron(self):
        _logger.info("Assign Ticket Cron Executed")
        delivery_quotes = self.env['sale.order'].sudo().search(
            [('quote_type', '=', 'delivery_stage'), ('hubspot_ticket_id', '=', False)])
        # delivery_quotes = self.env['sale.order'].sudo().search([('quote_type','=','delivery_stage')])
        if not delivery_quotes:
            _logger.info("No Delivery Quotes Found !!!")
        for quote in delivery_quotes:
            # Decide which field to use
            stage_value = False
            # if quote.burgtec_quote_reference and not quote.is_old_data:
            # stage_value = quote.burgtec_quote_reference
            if quote.new_sale_order_number and not quote.is_old_data:
                stage_value = quote.new_sale_order_number
            elif quote.delivery_stage and quote.is_old_data:
                split_parts = quote.delivery_stage.split("-")
                stage_value = '-'.join(split_parts[:2]).strip() if len(split_parts) > 1 else split_parts[0].strip()

            # If no stage value, nothing to process
            if not stage_value:
                continue
            # Search ticket
            matching_ticket = self.env['hubspot.ticket.data'].search([
                ('delivery_stage_number', '=', stage_value)
            ], limit=1)
            if not matching_ticket:
                _logger.info("No Hubspot Ticket Found For %s Delivery stage", stage_value)
            # Ticket found
            if matching_ticket:
                _logger.info("Matching Ticket Found For Delivery Stage %s ", stage_value)
                quote.sudo().write({
                    'hubspot_ticket_id': matching_ticket.id,
                })
                # if quote.purchase_order_id:
                #     quote.purchase_order_id.sudo().write({
                #         'hubspot_dispatch_date': matching_ticket.scheduled_dispatch
                #     })
                #     if quote.purchase_order_id.child_purchase_order_ids:
                #         quote.purchase_order_id.child_purchase_order_ids.sudo().write({
                #             'hubspot_dispatch_date': matching_ticket.scheduled_dispatch
                #         })
                # _logger.info("Hubspot Ticket Assigned Successfully!!! for  %s Delivery stage", stage_value)
                quote.message_post(body=_('Hubspot Ticket Assigned Successfully!'), message_type='comment',
                                   subtype_xmlid='mail.mt_comment')

    @api.depends('latest_eta_date', 'hubspot_ticket_schedule_dispatch')
    def _compute_latest_eta_dispatch_date_diff(self):
        for record in self:
            if record.hubspot_ticket_schedule_dispatch and record.latest_eta_date:
                delta = record.hubspot_ticket_schedule_dispatch - record.latest_eta_date
                record.latest_eta_dispatch_date_diff = delta.days
            else:
                record.latest_eta_dispatch_date_diff = False  # or False

    @api.depends('latest_eta_dispatch_date_diff')
    def _compute_delay_risk(self):
        for record in self:
            if record.latest_eta_dispatch_date_diff < 0.0:
                record.delay_risk = f"ETA is later than Dispatch Date (Delay Risk)"
                record.is_delay_risk = True
            else:
                record.delay_risk = False
                record.is_delay_risk = False

    def correct_parent_and_child_po_dispatch_date(self):
        for record in self:
            if record.hubspot_ticket_schedule_dispatch:
                if record.purchase_order_id:
                    record.purchase_order_id.sudo().write({
                        'hubspot_dispatch_date': record.hubspot_ticket_schedule_dispatch
                    })
                    _logger.info("Hubspot Dispatch Date Assigned Successfully!!! for Parent PO of %s Delivery stage",
                                 record.name)
                    if record.purchase_order_id.child_purchase_order_ids:
                        record.purchase_order_id.child_purchase_order_ids.sudo().write({
                            'hubspot_dispatch_date': record.hubspot_ticket_schedule_dispatch
                        })
                        _logger.info("Hubspot Dispatch Date Assigned Successfully!!! for Child PO of %s Delivery stage",
                                     record.name)

    @api.depends('hubspot_ticket_id', 'hubspot_ticket_id.scheduled_dispatch',
                 'hubspot_ticket_id.scheduled_delivers_date', 'hubspot_ticket_id.scheduled_install_date',
                 'hubspot_ticket_id.scheduled_install_complete_date', 'hubspot_ticket_id.is_backorder_registered',
                 'hubspot_ticket_id.hubspot_ticket_url')
    def _compute_hubspot_ticket_fields(self):
        for record in self:
            hubspot_ticket_obj = record.hubspot_ticket_id
            if not hubspot_ticket_obj:
                record.hubspot_ticket_schedule_dispatch = False
                record.scheduled_delivers_date = False
                record.scheduled_install_date = False
                record.scheduled_install_complete_date = False
                record.ticket_status = False
                record.is_backorder_registered = False
                record.qr_url = False
            if hubspot_ticket_obj:
                record.hubspot_ticket_schedule_dispatch = hubspot_ticket_obj.scheduled_dispatch
                record.scheduled_delivers_date = hubspot_ticket_obj.scheduled_delivers_date
                record.scheduled_install_date = hubspot_ticket_obj.scheduled_install_date
                record.scheduled_install_complete_date = hubspot_ticket_obj.scheduled_install_complete_date
                record.is_backorder_registered = hubspot_ticket_obj.is_backorder_registered

    def _get_hubspot_config(self):
        """Retrieve HubSpot configuration from system parameters."""
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('burgtec_hubspot_customization.hubspot_integrations_token')
        base_url = params.get_param('burgtec_hubspot_customization.hubspot_base_url')
        return base_url, token

    def action_update_hubspot_ticket(self):
        delivery_stages = self.env['sale.order'].search(
            [('hubspot_ticket_id', '!=', False), ('quote_type', '=', 'delivery_stage')]).filtered(
            lambda ds: not ds.delivery_status_tracking == 'fully_received')
        for rec in delivery_stages:
            base_url, token = rec._get_hubspot_config()
            if not base_url or not token:
                _logger.warning("HubSpot API Url or token not configured")
                return {
                    "success": False,
                    "error": "HubSpot API token not configured",
                }
            url = f"{base_url}/crm/v3/objects/tickets/{rec.hubspot_ticket_id.hubspot_ticket_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            properties = {}
            params = self.env['ir.config_parameter'].sudo()
            web_url = params.get_param('web.base.url')
            properties["odoo_delivery_stage_url"] = f'{web_url}/odoo/sale.order/{rec.id}'
            if rec.delivery_status_tracking:
                properties["delivery_stage_status"] = rec.delivery_status_tracking
            if rec.latest_eta_date:
                properties["latest_eta_date"] = int(rec.latest_eta_date.timestamp() * 1000)
            if rec.latest_eta_dispatch_date_diff:
                properties["eta_vs_dispatch_datedays"] = rec.latest_eta_dispatch_date_diff
            if not properties:
                continue

            payload = {
                "properties": properties
            }
            try:
                response = requests.patch(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                _logger.info("HubSpot ticket updated for Delivery Stage %s", rec.burgtec_quote_reference)
            except Exception:
                _logger.warning("HubSpot ticket update failed for Delivery Stage %s", rec.burgtec_quote_reference)

    # @api.depends('purchase_order_id','purchase_order_id.child_purchase_order_ids','purchase_order_id.child_purchase_order_ids.last_po_weekly_update_date')
    def compute_since_earliest_po_weekly_update(self):
        for record in self:
            purchase_order_obj = record.purchase_order_id
            child_po_obj = record.purchase_order_id.child_purchase_order_ids.filtered(
                lambda c: c.last_po_weekly_update_date)
            last_weekly_update_date_list = []
            earliest_date = False
            todays_date_time = fields.Datetime.now()
            days_diff = 0
            if record.quote_type in ('sales_quote', 'project_quote'):
                record.since_earliest_po_weekly_update = 0
            elif record.quote_type == 'delivery_stage':
                if not purchase_order_obj:
                    record.since_earliest_po_weekly_update = 0
                if purchase_order_obj:
                    if not child_po_obj:
                        record.since_earliest_po_weekly_update = 0
                    if child_po_obj:
                        last_weekly_update_date_list = child_po_obj.mapped('last_po_weekly_update_date')
                        earliest_date = min(last_weekly_update_date_list)
                        days_diff = (todays_date_time - earliest_date).days
                        record.since_earliest_po_weekly_update = days_diff
            else:
                record.since_earliest_po_weekly_update = 0
