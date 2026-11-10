import json
import logging
from odoo import http, _
from odoo.http import request
import requests
from dateutil import parser

_logger = logging.getLogger(__name__)


class HubspotController(http.Controller):
    def _get_hubspot_config(self):
        """Retrieve HubSpot configuration from system parameters."""

        params = request.env['ir.config_parameter'].sudo()
        token = params.get_param('burgtec_hubspot_customization.hubspot_integrations_token')
        base_url = params.get_param('burgtec_hubspot_customization.hubspot_base_url')
        return base_url, token

    @http.route('/hubspot_ticket_webhook', type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def hubspot_ticket_webhook(self, **kwargs):
        base_url, hubspot_token = self._get_hubspot_config()
        if request.httprequest.method == 'POST':
            data = request.get_json_data()
            event = data[0].get('subscriptionType') == 'ticket.creation' or data[0].get(
                'subscriptionType') == 'ticket.propertyChange'
            if event:
                ticket_id = data[0].get('objectId')
                url = f"{base_url}/crm/v3/objects/tickets/{ticket_id}"
                headers = {'Authorization': f'Bearer {hubspot_token}'}
                params = {
                    'properties': [
                        'scheduled_dispatch',
                        'subject',
                        'delivery_stage_number',
                        'backorder_registered',
                        'scheduled_delivery',
                        'scheduled_install_start',
                        'scheduled_install_complete',
                        'hs_pipeline_stage'
                    ]
                }
                response = requests.get(url, headers=headers, params=params)

                if response.status_code == 200:
                    ticket_data = response.json()
                    hubspot_ticket_id = ticket_data.get('id')
                    ticket_url = ticket_data.get('url')
                    subject = ticket_data.get('properties', {}).get('subject')
                    properties = ticket_data.get('properties', {})

                    # Get additional properties

                    schedule_dispatch_raw = properties.get('scheduled_dispatch')
                    delivery_stage_number = properties.get('delivery_stage_number')
                    backorder_registered = properties.get('backorder_registered')
                    scheduled_delivery = properties.get('scheduled_delivery')
                    scheduled_install_start = properties.get('scheduled_install_start')
                    scheduled_install_complete = properties.get('scheduled_install_complete')
                    ticket_status = properties.get('hs_pipeline_stage')
                    ticket_status_id = int(properties.get('hs_pipeline_stage'))
                    scheduled_dispatch_dt = False
                    ticket_status_name = False
                    if ticket_status:
                        ticket_status_name = self.get_stage_name_by_id(ticket_status_id)
                    if schedule_dispatch_raw:
                        scheduled_dispatch_dt = self._change_date_time_formate(schedule_dispatch_raw)
                    if scheduled_delivery:
                        scheduled_delivery = self._change_date_time_formate(scheduled_delivery)
                    if scheduled_install_start:
                        scheduled_install_start = self._change_date_time_formate(scheduled_install_start)
                    if scheduled_install_complete:
                        scheduled_install_complete = self._change_date_time_formate(scheduled_install_complete)

                    HubSpotTicket = request.env['hubspot.ticket.data'].sudo()

                    # Check if ticket already exists
                    existing_ticket = HubSpotTicket.search([
                        ('hubspot_ticket_id', '=', int(hubspot_ticket_id))
                    ], limit=1)

                    ticket_vals = {
                        'hubspot_ticket_id': int(hubspot_ticket_id),
                        'subject': subject,
                        'ticket_status': ticket_status_name,
                        'scheduled_dispatch': scheduled_dispatch_dt,
                        'delivery_stage_number': delivery_stage_number,
                        'hubspot_ticket_url': ticket_url,
                        'scheduled_install_complete_date': scheduled_install_complete,
                        'scheduled_install_date': scheduled_install_start,
                        'scheduled_delivers_date': scheduled_delivery,
                        'is_backorder_registered': backorder_registered,
                    }

                    if existing_ticket:
                        # Update existing ticket
                        existing_ticket.write(ticket_vals)
                        _logger.info(f"Ticket {hubspot_ticket_id} updated successfully")
                        existing_ticket.message_post(body=_('Hubspot Ticket Updated Successfully From Webhook!'), message_type='comment',
                                           subtype_xmlid='mail.mt_note')
                    else:
                        # Create new ticket
                        new_ticket = HubSpotTicket.create(ticket_vals)
                        _logger.info(f"New ticket {hubspot_ticket_id} created successfully")
                        new_ticket.message_post(body=_('Hubspot Ticket Created Successfully From Webhook!'),
                                                     message_type='comment',
                                                     subtype_xmlid='mail.mt_note')

                else:
                    _logger.error(f"Failed to fetch ticket data. Status code: {response.status_code}")
        else:
            _logger.warning("Invalid request method. Expected POST.")

    def _change_date_time_formate(self,date):
        dt = parser.isoparse(date)  # tz-aware datetime
        datetime_in_corrected_formate = dt.replace(tzinfo=None)
        return datetime_in_corrected_formate


    def get_stage_name_by_id(self, stage_id):
        """
        Get HubSpot ticket stage name by stage ID.
        Returns the stage name or 'Unknown' if not found.
        """
        base_url, hubspot_token = self._get_hubspot_config()

        headers = {'Authorization': f'Bearer {hubspot_token}'}
        url = f"{base_url}/crm/v3/pipelines/tickets"

        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code != 200:
                _logger.error(f"Failed to fetch pipelines. Status: {response.status_code}")
                return f"Unknown ({stage_id})"

            data = response.json()

            # Loop through all pipelines and stages to find the matching stage ID
            for pipeline in data.get('results', []):
                for stage in pipeline.get('stages', []):
                    if stage['id'] == str(stage_id):
                        return stage['label']

            return f"Unknown ({stage_id})"

        except Exception as e:
            _logger.error(f"Error fetching stage name: {str(e)}")
            return f"Unknown ({stage_id})"




