import logging
from odoo import http, _
from odoo.http import request
import requests
import importlib
from dateutil import parser

_logger = logging.getLogger(__name__)
hubspot = importlib.import_module('odoo.addons.burgtec_hubspot_customization')


class HubspotControllerExt(hubspot.controller.main.HubspotController):
    @http.route('/hubspot_ticket_webhook', type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def hubspot_ticket_webhook(self, **kwargs):
        base_url, hubspot_token = self._get_hubspot_config()
        ticket_id = False
        HubSpotTicket = request.env['hubspot.ticket.data'].sudo()
        if request.httprequest.method == 'POST':
            data = request.get_json_data()
            ticket_delete_event = data[0].get('subscriptionType') == 'ticket.deletion'
            ticket_related_event = data[0].get('subscriptionType') == 'ticket.creation' or data[0].get(
                'subscriptionType') == 'ticket.propertyChange' or data[0].get('subscriptionType') == 'ticket.restore'
            deal_related_event = data[0].get('subscriptionType') == 'deal.propertyChange'
            # Handeling Deleting Ticket Issue.
            if ticket_delete_event:
                ticket_id = data[0].get('objectId')
                HubSpotTicket.search([('hubspot_ticket_id', '=', str(ticket_id))]).unlink()

            if ticket_related_event:
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
                        existing_ticket.message_post(body=_('Hubspot Ticket Updated Successfully From Webhook!'),
                                                     message_type='comment',
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
            if deal_related_event:
                deal_id = data[0].get('objectId')
                existing_crm_lead = request.env['crm.lead'].sudo().search([('id_of_hubspot_deal', '=', deal_id)],
                                                                          limit=1)
                if existing_crm_lead:
                    properties = [
                        'dealname',
                        'amount',
                        'createdate',
                        'closedate',
                        'dealname',
                        'dealstage',
                        'hubspot_owner_id',
                        'quoted_by',
                        'dealtype',
                        'deal_number',
                        'pipeline_stage',
                        'dated_quoted',
                        'gppercent',
                        'gp__',
                        'project_location',
                        'hs_projected_amount_in_home_currency',
                        'score_100',
                        'site_install_address',
                        'hubspot_site_contact_url',
                        'install_start_date',
                        'deadline_10__feedback_required',
                    ]
                    headers = {
                        'Authorization': f'Bearer {hubspot_token}',
                        'Content-Type': 'application/json'
                    }
                    url = f"{base_url}/crm/v3/objects/deals/{deal_id}"
                    params = {"properties": ','.join(properties),
                              'associations': 'companies'}

                    try:
                        # Fetch the deal from HubSpot
                        response = requests.get(url, params=params, headers=headers, timeout=30)
                        if response.status_code != 200:
                            _logger.error(f"HubSpot API error: {response.status_code} - {response.text}")
                        data = response.json()
                        properties_data = data.get('properties', {})
                        # Map HubSpot values to Odoo records
                        deal_stage_id = False
                        deal_stage_record = False
                        deal_type_id = False
                        pipeline_stage_id = False
                        project_location_id = False
                        hubspot_owner_id = False
                        user = False
                        quoted_by_name = ''
                        deal_owner_name = ''
                        odoo_deal_owner = False
                        dealname = properties_data.get('dealname')
                        amount = properties_data.get('amount')
                        createdate = self._parse_hubspot_date(properties_data.get('createdate'))
                        close_date = self._parse_hubspot_date(properties_data.get('closedate'))
                        dated_quoted = self._parse_hubspot_date(properties_data.get('dated_quoted'))
                        deal_type = properties_data.get('dealtype')
                        deal_stage = properties_data.get('dealstage')
                        pipeline_stage = properties_data.get('pipeline_stage')
                        project_location = properties_data.get('project_location')
                        hubspot_owner_id = properties_data.get('hubspot_owner_id')
                        quoted_by_id = properties_data.get('quoted_by')
                        site_address = (properties_data.get('site_install_address') or '')
                        required_installation_date = self._parse_hubspot_date_only(properties_data.get('install_start_date'))
                        required_completion_date = self._parse_hubspot_date_only(
                            properties_data.get('deadline_10__feedback_required'))
                        site_contact_name, site_contact_mobile = self.get_site_contact_details(
                            properties_data.get('hubspot_site_contact_url'), base_url, hubspot_token)
                        # if hubspot_owner_id:
                        #     odoo_deal_owner = self.fetch_odoo_deal_owner(hubspot_owner_id)
                            # deal_owner_name = self.fetch_deal_owner_name(hubspot_owner_id, base_url, hubspot_token)
                        if quoted_by_id:
                            quoted_by_name = self.fetch_quoted_by_name(quoted_by_id, base_url, hubspot_token)
                        if deal_stage:
                            deal_stage_record = request.env['deal.stage'].search([('deal_stage_id', '=', deal_stage)],
                                                                                 limit=1)
                            deal_stage_id = deal_stage_record.id if deal_stage_record else False

                        if deal_type:
                            deal_type_record = request.env['deal.type'].search([('hubspot_value', '=', deal_type)],
                                                                               limit=1)
                            deal_type_id = deal_type_record.id if deal_type_record else False

                        if pipeline_stage:
                            pipeline_stage_record = request.env['deal.pipeline.stage'].search(
                                [('hubspot_internal_name', '=', pipeline_stage)], limit=1)
                            pipeline_stage_id = pipeline_stage_record.id if pipeline_stage_record else False

                        if project_location:
                            project_location_record = request.env['deal.location'].search(
                                [('hubspot_internal_name', '=', project_location)], limit=1)
                            project_location_id = project_location_record.id if project_location_record else False

                        # Prepare CRM lead values
                        lead_vals = {
                            'name': dealname,
                            # 'partner_id': company_id.id if company_id else False,
                            # 'phone': company_id.phone if company_id else False,
                            'expected_revenue': float(amount) if amount else 0.0,
                            'deal_create_date': createdate or False,
                            'deal_close_date': close_date or False,
                            'deal_stage_id': deal_stage_id or False,
                            'deal_type_id': deal_type_id or False,
                            'deal_pipeline_and_stage_id': pipeline_stage_id or False,
                            'deal_date_quoted': dated_quoted or False,
                            'quoted_by': quoted_by_name or '',
                            'deal_probability': deal_stage_record.probability if deal_stage_record else False,
                            'deal_quoted_gp_percentage': properties_data.get('gppercent'),
                            'deal_quoted_gp_value': properties_data.get('gp__'),
                            'deal_territory_id': project_location_id or False,
                            'is_deal_imported': True,
                            'weighted_amount': properties_data.get('hs_projected_amount_in_home_currency'),
                            'deal_score': properties_data.get('score_100'),
                            'site_address': site_address,
                            'required_installation_date': required_installation_date,
                            'required_completion_date': required_completion_date,
                            'site_contact_name': site_contact_name or False,
                            'site_contact_mobile': site_contact_mobile or False,
                        }
                        # Update this CRM lead with HubSpot data
                        existing_crm_lead.sudo().write(lead_vals)

                        _logger.info(
                            f"✓ Successfully Updated HubSpot deal {existing_crm_lead.id_of_hubspot_deal} to CRM Lead {existing_crm_lead.id}")
                        existing_crm_lead.sudo().message_post(body=_('Hubspot Deal Updated Successfully From Webhook!'),
                                                              message_type='comment',
                                                              subtype_xmlid='mail.mt_note')
                    except Exception as e:
                        _logger.error(f"✗ Exception Updating deal from HubSpot: {str(e)}")
                        return False
        else:
            _logger.warning("Invalid request method. Expected POST.")

    # BELOW ARE ALL THE HELPER METHOD

    def _parse_hubspot_date(self, date_string):
        """Parse HubSpot date string to Odoo compatible format."""
        if not date_string:
            return False
        try:
            dt = parser.isoparse(date_string)
            return dt.replace(tzinfo=None)
        except Exception as e:
            _logger.warning(f"Failed to parse date {date_string}: {str(e)}")
            return False

    def fetch_odoo_deal_owner(self, owner_id):
        """Fetch HubSpot deal owner and map to Odoo user."""
        res_user_obj = request.env['res.users'].sudo()
        res_user = res_user_obj.search([('hubspot_owner_id', '=', owner_id)], limit=1)
        return res_user if res_user else False

    def fetch_deal_owner_name(self, owner_id, url, token):
        """Fetch HubSpot deal owner and map to Odoo user."""
        url = f"{url}/crm/v3/owners/{owner_id}"

        headers = {
            'Authorization': f'Bearer {token}',
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            _logger.warning("Failed to fetch HubSpot owner")
            return False
        data = response.json()
        first_name = data.get('firstName')
        last_name = data.get('lastName')
        full_name = ''
        if first_name and last_name:
            full_name = f"{first_name} {last_name}"
        elif first_name:
            full_name = first_name
        elif last_name:
            full_name = last_name
        else:
            return False
        return full_name

    def fetch_quoted_by_name(self, owner_id, url, token):
        """Fetch HubSpot deal quoted by namer and map to Crm Lead."""
        url = f"{url}/crm/v3/owners/{owner_id}"
        headers = {
            'Authorization': f'Bearer {token}',
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            _logger.warning("Failed to fetch HubSpot Quoted by owner")
            return False
        data = response.json()
        first_name = data.get('firstName')
        last_name = data.get('lastName')
        full_name = ''
        if first_name and last_name:
            full_name = f"{first_name} {last_name}"
        elif first_name:
            full_name = first_name
        elif last_name:
            full_name = last_name
        else:
            return False
        return full_name

    def associated_company_with_deal(self, hubspot_company_id, token):

        if hubspot_company_id:
            url = f"https://api.hubapi.com/crm/v3/objects/companies/{hubspot_company_id}"
            headers = {
                "Authorization": f"Bearer {token}"
            }
            query_params = {
                "properties": ["name", "email", "domain", "country", "phone", "city", "industry", "address", "state",
                               "zip"],
                "archived": "false"
            }
            response = requests.get(url, headers=headers, params=query_params)
            company_data = response.json()
            company_id = company_data.get('id')  # '3169092150'
            # Extract properties object
            properties = company_data.get('properties', {})

            # Map HubSpot properties to Odoo fields
            partner_vals = {
                'name': properties.get('name'),
                'is_company': True,
                'company_type': 'company',
                'phone': properties.get('phone'),
                'website': properties.get('domain'),
                'street': properties.get('address'),
                'city': properties.get('city'),
                'zip': properties.get('zip'),
                'id_of_hubspot_company': company_id,
                'state_id': self._get_state_id(properties.get('state'), properties.get('country')),
                'country_id': self._get_country_id(properties.get('country')),
            }
            Respartner = request.env['res.partner'].sudo()
            existing_partner = Respartner.search(
                ["|", "|", "|", "|", "|", ("complete_name", "ilike", properties.get('name')),
                 ("ref", "ilike", properties.get('name')),
                 ("email", "ilike", properties.get('name')), ("vat", "ilike", properties.get('name')),
                 ("company_registry", "ilike", properties.get('name')), ("name", "ilike", properties.get('name'))],
                limit=1)
            # existing_partner = Respartner.search([
            #     ('id_of_hubspot_company', '=', company_id)
            # ], limit=1)
            if not existing_partner:
                return False
                # new_contact = Respartner.create(partner_vals)
                # return new_contact

            else:
                return existing_partner

    def _get_state_id(self, state, country):
        country = request.env['res.country'].search([('name', '=', country)], limit=1)
        if country:
            state = request.env['res.country.state'].search([('country_id', '=', country.id), ('code', "=", state)],
                                                            limit=1)
            if state:
                return state.id

    def _get_country_id(self, country):
        country = request.env['res.country'].search([('name', '=', country)], limit=1)
        if country:
            return country.id

    def get_site_contact_details(self, contact_url, base_url, hubspot_token):
        try:
            if not contact_url:
                return '', ''

            contact_id = contact_url.split('/record/0-1/')[1].split('?')[0]

            url = f"{base_url}/crm/v3/objects/contacts/{contact_id}"

            headers = {
                'Authorization': f'Bearer {hubspot_token}',
                'Content-Type': 'application/json',
            }

            params = {
                'properties': 'firstname,lastname,mobilephone'
            }

            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=30
            )

            if response.status_code != 200:
                return '', ''

            properties = response.json().get('properties', {})

            first_name = properties.get('firstname') or ''
            last_name = properties.get('lastname') or ''
            mobile = properties.get('mobilephone') or ''

            return f"{first_name} {last_name}".strip(), mobile

        except Exception as e:
            _logger.warning("Could not fetch site contact: %s", e)
            return '', ''

    def _parse_hubspot_date_only(self, date_string):
        """Parse HubSpot date string to Odoo Date."""
        if not date_string:
            return False

        try:
            return parser.isoparse(date_string).date()
        except Exception as e:
            _logger.warning(
                f"Failed to parse date {date_string}: {str(e)}"
            )
            return False
