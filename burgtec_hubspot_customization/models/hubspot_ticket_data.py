from odoo import models, fields, api
import logging
import requests
from dateutil import parser
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HubspotTicketData(models.Model):
    _name = 'hubspot.ticket.data'
    _description = 'Hubspot Ticket Data'
    _rec_name = 'delivery_stage_number'
    _inherit = ['mail.thread']
    _order = 'create_date desc, id desc'

    hubspot_ticket_id = fields.Char(
        string='HubSpot Ticket ID',
        required=True,
        index=True,
        help='The unique ID from HubSpot'
    )

    subject = fields.Char(
        string='Subject',
        required=True,
        help='Ticket subject from HubSpot', tracking=True)
    delivery_stage_number = fields.Char(string='Delivery Stage Number', tracking=True)
    due_date = fields.Date(string='Due Date')
    last_po_date_due = fields.Date(string='Last PO date due')
    hs_last_closed_date = fields.Date(string='Last closed date')
    scheduled_dispatch = fields.Datetime(string='Schedule Dispatch Date', tracking=True)
    scheduled_delivers_date = fields.Datetime(string='Schedule Delivers Date', tracking=True)
    scheduled_install_date = fields.Datetime(string='Schedule Install Date', tracking=True)
    scheduled_install_complete_date = fields.Datetime(string='Schedule Install Complete Date', tracking=True)
    ticket_status = fields.Char(string='Ticket Status', tracking=True)
    is_backorder_registered = fields.Boolean(string='Backorder Registered', tracking=True)
    hubspot_ticket_url = fields.Char(string='HubSpot Ticket URL', tracking=True)

    is_dupe_record_exist = fields.Boolean()

    def _get_hubspot_config(self):
        """Retrieve HubSpot configuration from system parameters."""
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('burgtec_hubspot_customization.hubspot_integrations_token')
        base_url = params.get_param('burgtec_hubspot_customization.hubspot_base_url')

        if not token or not base_url:
            raise UserError(_("HubSpot configuration is missing. Please configure the API token and base URL."))

        return base_url, token

    def _parse_date(self, date_string):
        """
        Parse date string from HubSpot and return date object.
        HubSpot typically returns dates as 'YYYY-MM-DD' or timestamps.
        Returns False if parsing fails or date_string is empty.
        """
        if not date_string:
            return False

        try:
            if isinstance(date_string, str):
                # Parse the date string and return date object only
                dt = parser.parse(date_string)
                return dt.date()
            return False
        except (ValueError, TypeError, parser.ParserError) as e:
            _logger.warning(f"Failed to parse date '{date_string}': {str(e)}")
            return False

    def sync_all_hubspot_tickets(self):
        """
        Fetch all tickets from HubSpot and create/update them in Odoo.
        This method can be called from a server action.
        """
        base_url, hubspot_token = self._get_hubspot_config()

        headers = {'Authorization': f'Bearer {hubspot_token}'}
        properties = [
            'scheduled_dispatch',
            'due_date',
            'last_po_date_due',
            'hs_last_closed_date',
            'subject',
            'delivery_stage_number',
            'backorder_registered',
            'scheduled_delivery',
            'scheduled_install_start',
            'scheduled_install_complete',
            'hs_pipeline_stage'
        ]

        # HubSpot API endpoint for fetching all tickets
        url = f"{base_url}/crm/v3/objects/tickets"
        params = {
            'properties': ','.join(properties),
            'limit': 100  # Maximum per page
        }

        created_count = 0
        updated_count = 0
        error_count = 0
        error_details = []

        try:
            while True:
                response = requests.get(url, headers=headers, params=params, timeout=30)

                if response.status_code != 200:
                    _logger.error(
                        f"Failed to fetch tickets. Status code: {response.status_code}, Response: {response.text}")
                    raise UserError(_(f"Failed to fetch tickets from HubSpot. Status code: {response.status_code}"))

                data = response.json()
                tickets = data.get('results', [])

                _logger.info(f"Fetched {len(tickets)} tickets from HubSpot")

                # Process each ticket with savepoint protection
                for ticket in tickets:
                    ticket_id = ticket.get('id', 'unknown')
                    ticket_url = ticket.get('url')
                    try:
                        # Create a savepoint before processing each ticket
                        savepoint_name = f'sp_ticket_{ticket_id}'
                        self.env.cr.execute(f'SAVEPOINT {savepoint_name}')

                        result = self._process_ticket(ticket, ticket_url)

                        # Release savepoint on success
                        self.env.cr.execute(f'RELEASE SAVEPOINT {savepoint_name}')

                        if result == 'created':
                            created_count += 1
                        elif result == 'updated':
                            updated_count += 1

                    except Exception as e:
                        # Rollback to savepoint on error
                        try:
                            self.env.cr.execute(f'ROLLBACK TO SAVEPOINT {savepoint_name}')
                        except:
                            pass

                        error_count += 1
                        error_msg = f"Ticket {ticket_id}: {str(e)}"
                        error_details.append(error_msg)
                        _logger.error(f"Error processing ticket {ticket_id}: {str(e)}", exc_info=True)

                # Commit after each batch
                self.env.cr.commit()

                # Check for pagination
                paging = data.get('paging', {})
                next_link = paging.get('next', {}).get('link')

                if not next_link:
                    break  # No more pages

                # Update URL for next page
                url = next_link
                params = {}  # Clear params as next_link contains everything

        except requests.exceptions.RequestException as e:
            _logger.error(f"Request exception while fetching tickets: {str(e)}")
            raise UserError(_(f"Failed to connect to HubSpot: {str(e)}"))

        # Log summary
        message = f"HubSpot Sync Complete - Created: {created_count}, Updated: {updated_count}, Errors: {error_count}"
        _logger.info(message)

        # Log sample errors if any
        if error_details:
            _logger.error(f"Sample errors: {error_details[:3]}")

        # Return a user-friendly message
        notification_type = 'success' if error_count == 0 else 'warning'
        full_message = message
        if error_count > 0 and error_details:
            full_message += f"\n\nSample error: {error_details[0]}"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('HubSpot Sync Complete'),
                'message': full_message,
                'type': notification_type,
                'sticky': True if error_count > 0 else False,
            }
        }

    def _process_ticket(self, ticket_data, ticket_url):
        """
        Process a single ticket: create if new, update if exists.
        Returns 'created' or 'updated'
        """
        hubspot_ticket_id = ticket_data.get('id')

        if not hubspot_ticket_id:
            raise ValueError("Ticket has no ID")

        properties = ticket_data.get('properties', {})

        # Parse properties with proper type conversion and defaults
        subject = properties.get('subject')
        if not subject or str(subject).strip() == '':
            subject = f'Ticket {hubspot_ticket_id}'  # Default for required field

        # Parse date fields - convert strings to date objects
        due_date = self._parse_date(properties.get('due_date'))
        last_po_date_due = self._parse_date(properties.get('last_po_date_due'))
        hs_last_closed_date = self._parse_date(properties.get('hs_last_closed_date'))

        delivery_stage_number = properties.get('delivery_stage_number') or False
        backorder_registered = properties.get('backorder_registered') or False
        scheduled_delivery_date = self._parse_date(properties.get('scheduled_delivery'))
        scheduled_install_complete_date = self._parse_date(properties.get('scheduled_install_complete'))
        scheduled_install_date = self._parse_date(properties.get('scheduled_install_start'))
        ticket_status_id = int(properties.get('hs_pipeline_stage'))
        ticket_status_name = self.get_stage_name_by_id(ticket_status_id)
        hubspot_ticket_url = ticket_url

        # Parse scheduled_dispatch (datetime field)
        scheduled_dispatch_dt = False
        schedule_dispatch_raw = properties.get('scheduled_dispatch')
        if schedule_dispatch_raw:
            try:
                dt = parser.isoparse(schedule_dispatch_raw)
                scheduled_dispatch_dt = dt.replace(tzinfo=None)
            except Exception as e:
                _logger.warning(f"Failed to parse scheduled_dispatch for ticket {hubspot_ticket_id}: {str(e)}")

        # Prepare values with CORRECT data types
        ticket_vals = {
            'hubspot_ticket_id': str(hubspot_ticket_id),
            'subject': subject,
            'due_date': due_date,
            'last_po_date_due': last_po_date_due,
            'hs_last_closed_date': hs_last_closed_date,
            'scheduled_dispatch': scheduled_dispatch_dt,
            'is_backorder_registered': backorder_registered,
            'scheduled_delivers_date': scheduled_delivery_date,
            'scheduled_install_complete_date': scheduled_install_complete_date,
            'scheduled_install_date': scheduled_install_date,
            'ticket_status': ticket_status_name,
            'hubspot_ticket_url': hubspot_ticket_url,
            'delivery_stage_number': delivery_stage_number,
        }

        # Check if ticket exists
        existing_ticket = self.search([
            ('hubspot_ticket_id', '=', str(hubspot_ticket_id))
        ], limit=1)

        if existing_ticket:
            existing_ticket.write(ticket_vals)
            _logger.info(f"✅ Ticket {hubspot_ticket_id} updated successfully")
            return 'updated'
        else:
            new_ticket = self.create(ticket_vals)
            _logger.info(f"✅ Ticket {hubspot_ticket_id} created successfully (Odoo ID: {new_ticket.id})")
            return 'created'

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

    def _update_ticket_not_having_url(self):
        base_url, hubspot_token = self._get_hubspot_config()
        total_process_ticket = 0
        ticket_without_url = self.search([('hubspot_ticket_url','=',False)])
        for ticket in ticket_without_url:
            if ticket.hubspot_ticket_id:
                url = f"{base_url}/crm/v3/objects/tickets/{ticket.hubspot_ticket_id}"
                headers = {'Authorization': f'Bearer {hubspot_token}'}
                payload = {
                    "properties": {
                        "in_odoo": True,
                    }
                }
                response = requests.patch(url, headers=headers, json=payload)
                if response.status_code in (200, 201):
                    total_process_ticket += 1
                    _logger.info(f"In Odoo Check Updated on Tickets and total Processed tickets: {total_process_ticket}")
    

    def find_duplicated_tickets(self):
        for record in self:
            seen2 = set()
            my_list_2 = record.env['hubspot.ticket.data'].sudo().search([('delivery_stage_number','!=',False)]).mapped('delivery_stage_number')
            all_duplicates_2 = [x for x in my_list_2 if x in seen2 or seen2.add(x)]
            record.env['hubspot.ticket.data'].sudo().search([('delivery_stage_number','in',all_duplicates_2)]).is_dupe_record_exist = True



