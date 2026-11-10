from odoo import models, fields, api, _
from odoo.osv import expression
import logging
from dateutil import parser
import base64
import io
import xlsxwriter
from odoo import fields, models
from odoo.tools.misc import format_date
from datetime import datetime
import ast
import math
import re
import requests
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)



def normalize_name(name):
    # Remove punctuation, lowercase, strip whitespace
    return re.sub(r'[^a-z0-9 ]', '', name.lower()).strip()


class CrmLeadExt(models.Model):
    _inherit = 'crm.lead'

    name = fields.Char(
        'Opportunity', index='trigram', required=False,
        compute='_compute_name', readonly=False, store=True)

    # ------------------------------------> New Fields For Hubspot Deal Linking To Odoo CRM   <------------------------------------------------------
    deal_create_date = fields.Datetime(tracking=True)
    deal_close_date = fields.Datetime(tracking=True)
    deal_stage_id = fields.Many2one('deal.stage', string="Deal Stage", tracking=True)
    id_of_hubspot_deal = fields.Char(string="HubSpot Deal ID")
    odoo_deal_number_6digit = fields.Char(string="Deal Number")
    deal_territory_id = fields.Many2one('deal.location', string="Territory/Location", tracking=True)
    deal_pipeline_and_stage_id = fields.Many2one('deal.pipeline.stage', string="Pipeline & Stage", tracking=True)
    deal_date_quoted = fields.Date(string="Date 1st Quoted", tracking=True)
    quoted_by = fields.Char(string="Quoted By", tracking=True)
    deal_owner = fields.Char(string="Deal Owner Name", tracking=True)
    odoo_deal_owner_id = fields.Many2one('res.users', string='Deal Owner ID')
    deal_quoted_gp_value = fields.Float(string="Quoted GP Value", tracking=True)
    deal_quoted_gp_percentage = fields.Float(string="Quoted GP %", tracking=True)
    deal_type_id = fields.Many2one('deal.type', string="Deal Type", tracking=True)
    project_quotation_count = fields.Integer(compute='_compute_sale_data', string="Number of Project Quotes")
    delivery_stage_count = fields.Integer(compute='_compute_sale_data', string="Number of Delivery Stages")
    sale_amount_total = fields.Monetary(compute='_compute_sale_data', string="Sum of Project Quote",
                                        help="Untaxed Total of Project Quote", currency_field='company_currency')
    company_currency = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True
    )
    latest_quote_sent_amount = fields.Monetary(
        compute='_compute_latest_quote_fields',
        currency_field='company_currency',
        string="Latest Odoo Quote Sent Amount",
        store=True,
        tracking=True
    )
    latest_odoo_quote_gp_amount = fields.Monetary(
        compute='_compute_latest_quote_fields',
        currency_field='company_currency',
        string="Latest Odoo Quote GP$ Amount",
        store=True,
        tracking=True
    )

    latest_odoo_quote_gp_percentage = fields.Float(
        compute='_compute_latest_odoo_quote_gp_percentage',
        string="Latest Odoo Quote GP%",
        store=True,
        tracking=True
    )
    latest_odoo_quote_number_of_item_lines = fields.Integer(string="Latest Odoo Quote Number of Item Lines",
                                                            compute='_compute_latest_quote_fields', tracking=True,
                                                            store=True)

    series_sequence_id = fields.Many2one('sale.order.series', string="Series Sequence")

    deal_probability = fields.Float(
        'Deal Probability', aggregator="avg", copy=False,
        related='deal_stage_id.probability', readonly=True, store=True, tracking=True)

    is_deal_imported = fields.Boolean(default=False, copy=False, tracking=True)
    is_deal_exported = fields.Boolean(default=False, copy=False, tracking=True)
    is_old_deal = fields.Boolean(default=False, copy=False)
    is_closed_won = fields.Boolean(default=False, copy=False, tracking=True)
    is_closed_lost = fields.Boolean(default=False, copy=False, tracking=True)
    hubspot_deal_url = fields.Char(string="HubSpot Deal URL")

    is_fixed = fields.Boolean(default=False)
    fixed_description = fields.Text()

    project_name = fields.Char(tracking=True)

    # additional fields for dashboard
    weighted_amount = fields.Float('Weighted Amount')
    deal_score = fields.Float('Deal Score')
    deal_pipeline = fields.Char(related='deal_stage_id.pipeline_name', tracking=True, store=True)

    line_item_status_ids = fields.One2many('line.item.status', 'crm_lead_id')

    is_project_name_changed = fields.Boolean(default=False)

    location = fields.Selection([
        ('nsw', 'New South Wales'),
        ('act', 'Australian Capital Territory'),
        ('vic', 'Victoria'),
        ('qld', 'Queensland'),
        ('other', 'Other')
    ], string="Location", copy=False, default=None)

    # All the fields for Site Address Page on Crm Lead

    site_address = fields.Char("Site Address")

    # Contact & schedule
    site_contact_name = fields.Char("Site Contact - Name")
    site_contact_mobile = fields.Char("Site Contact - Mobile No")
    required_installation_date = fields.Date()
    required_completion_date = fields.Date()
    access_times = fields.Char()
    final_furniture_plan = fields.Char()

    # Loading dock
    loading_dock_available = fields.Selection([("yes", "Yes"), ("no", "No")], "Loading Dock Available")
    loading_dock_notes = fields.Text('Loading Dock Notes')
    loading_dock_booking_required = fields.Selection([("yes", "Yes"), ("no", "No")], "Loading Dock Booking Required")
    loading_dock_height_clearance = fields.Char("Loading Dock Height Clearance")
    alternate_unloading_area = fields.Text("Alternate Unloading Area")

    # Vehicle / equipment access
    forklift_available = fields.Selection([("yes", "Yes"), ("no", "No")])
    semi_trailer_access = fields.Selection([("yes", "Yes"), ("no", "No")], "Semi-trailer Access")

    # Lift / stairs
    lift_available = fields.Text(
        "Lift Available", help="Include any time restrictions."
    )
    lift_dimensions = fields.Text(
        help="Opening & internal dimensions."
    )
    stairs_flights = fields.Text("No Lift - Flights of Stairs")

    # Compliance
    permits_inductions = fields.Text("Permits/Inductions Required")
    ppe_requirement = fields.Text("PPE Requirement", help="Provide specific details.")
    # swms_insurance_om = fields.Text("SWMS, Insurances, O&M Required")

    swms_required = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="SWMS Required")
    swms_submitted_date = fields.Date(string="SWMS Submitted")
    swms_approved_date = fields.Date(string="SWMS Approved")

    insurance_required = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Insurances Required")
    insurance_submitted_date = fields.Date(string="Insurances Submitted")

    om_required = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="O&M Required")
    om_submitted_date = fields.Date(string="O&M Submitted")


    # Documentation
    access_photos_provided = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        help="e.g. loading area, building entrance, access route, "
             "lift/stairs and installation area.",
    )
    site_other_notes = fields.Text(
        "Other Instructions/Notes",
        help="e.g. distance from unloading area to install area, storage or "
             "staging area available onsite, noise restrictions.",
    )

    @api.depends(
        'order_ids',
        'order_ids.state',
        'order_ids.order_line',
        'order_ids.amount_untaxed',
        'order_ids.live_unit_cost',
        'expected_revenue',
    )
    def _compute_latest_quote_fields(self):
        for rec in self:
            sent_quotes = rec.order_ids.filtered(
                lambda q: q.quote_type == 'sales_quote')
            project_quote = rec.order_ids.filtered(
                lambda o: o.quote_type == 'project_quote'
            )

            if project_quote:
                quote = project_quote[0]
                rec.latest_quote_sent_amount = quote.amount_untaxed
                rec.latest_odoo_quote_gp_amount = quote.live_unit_cost
                rec.latest_odoo_quote_number_of_item_lines = len(
                    quote.order_line.filtered(lambda l: not l.display_type)
                )
            elif sent_quotes:
                latest_sent = sent_quotes.sorted(
                    key=lambda q: q.create_date, reverse=True
                )[0]
                rec.latest_quote_sent_amount = latest_sent.amount_untaxed
                rec.latest_odoo_quote_gp_amount = latest_sent.live_unit_cost
                rec.latest_odoo_quote_number_of_item_lines = len(
                    latest_sent.order_line.filtered(lambda l: not l.display_type)
                )
            else:
                rec.latest_quote_sent_amount = 0.0
                rec.latest_odoo_quote_gp_amount = 0.0
                rec.latest_odoo_quote_number_of_item_lines = 0

            rec.latest_odoo_quote_gp_percentage = (
                rec.latest_odoo_quote_gp_amount / rec.expected_revenue
                if rec.expected_revenue
                else 0.0
            )

            if project_quote or sent_quotes:
                rec._export_computed_fields_in_hubspot()
                rec.message_post(
                    body=(_('Deal Updated in Hubspot Only With (Compute Latest Fields)')),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note'
                )
    def _inverse_email_from(self):
        for lead in self:
            if lead._get_partner_email_update(force_void=False):
                lead.partner_id.sudo().email = lead.email_from

    def _inverse_phone(self):
        for lead in self:
            if lead._get_partner_phone_update(force_void=False):
                lead.partner_id.sudo().phone = lead.phone

    def _inverse_email_from(self):
        for lead in self:
            if lead._get_partner_email_update(force_void=False):
                lead.partner_id.sudo().email = lead.email_from

    def _inverse_phone(self):
        for lead in self:
            if lead._get_partner_phone_update(force_void=False):
                lead.partner_id.sudo().phone = lead.phone

    def _set_project_name_on_crm_lead_from_sale_quotes(self):
        for rec in self:
            if not rec.project_name and rec.order_ids:
                related_sales_quotes = rec.order_ids.filtered(
                    lambda o: o.quote_type == 'sales_quote' and o.project_name
                )
                if related_sales_quotes:
                    latest_sale_quote = related_sales_quotes.sorted(
                        key=lambda q: q.create_date, reverse=True
                    )[0]
                    rec.project_name = latest_sale_quote.project_name
                    rec.is_project_name_changed = True
                    print(
                        f"CRM Lead [{rec.name}] project name set to '{rec.project_name}'"
                    )

    def create(self, vals_list):
        records = super(CrmLeadExt, self).create(vals_list)
        for record in records:
            if not record.location:
                raise ValidationError(_('Please select a location'))
        return records

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'deal_close_date' in fields_list:
            today = fields.Date.today()
            first_next_month = today.replace(day=1) + relativedelta(months=3)
            end_next_month = first_next_month + relativedelta(months=1, days=-1)
            res['deal_close_date'] = end_next_month

        if 'odoo_deal_owner_id' in fields_list:
            res['odoo_deal_owner_id'] = self.env.user.id

        if 'deal_stage_id' in fields_list:
            stage = self.env['deal.stage'].search(
                [('name', '=', 'S - 0. New')],
                limit=1
            )
            if stage:
                res['deal_stage_id'] = stage.id
                res['deal_pipeline'] = stage.pipeline_name
        return res

    @api.depends('latest_odoo_quote_gp_amount', 'expected_revenue')
    def _compute_latest_odoo_quote_gp_percentage(self):
        for rec in self:
            if rec.expected_revenue:
                rec.latest_odoo_quote_gp_percentage = rec.latest_odoo_quote_gp_amount / rec.expected_revenue
            else:
                rec.latest_odoo_quote_gp_percentage = 0.0

    @api.depends('odoo_deal_number_6digit', 'project_name')
    def _compute_name(self):
        for lead in self:
            # if not lead.odoo_deal_number_6digit and not lead.name and lead.partner_id and lead.partner_id.name:
            #     lead.name = _("%s's opportunity") % lead.partner_id.name
            if lead.odoo_deal_number_6digit and lead.project_name:
                lead.name = f'{lead.odoo_deal_number_6digit} - {lead.project_name}'
            elif lead.odoo_deal_number_6digit and not lead.project_name:
                lead.name = f'{lead.odoo_deal_number_6digit}'
            else:
                lead.name = False

    def _prepare_opportunity_quotation_context(self):
        """ Prepares the context for a new quotation (sale.order) by sharing the values of common fields """
        self.ensure_one()
        quotation_context = {
            'default_opportunity_id': self.id,
            'default_partner_id': self.partner_id.id,
            'default_campaign_id': self.campaign_id.id,
            'default_medium_id': self.medium_id.id,
            'default_origin': self.name,
            'default_source_id': self.source_id.id,
            'default_company_id': self.company_id.id or self.env.company.id,
            'default_tag_ids': [(6, 0, self.tag_ids.ids)],
            'default_new_sale_order_number': self.odoo_deal_number_6digit,
            'default_project_name': self.project_name,
            'default_location': self.location,
        }
        if self.team_id:
            quotation_context['default_team_id'] = self.team_id.id
        if self.user_id:
            quotation_context['default_user_id'] = self.user_id.id
        return quotation_context

    def action_generate_deal_number(self):
        for record in self:
            if not record.series_sequence_id:
                raise UserError("Please select a Sequence Number before generating the sale order number.")
            series_record = record.series_sequence_id
            series_starting_value = series_record.starting_value
            series_ending_value = series_record.ending_value
            if series_starting_value > series_ending_value:
                raise UserError("Sale Order Series has Ended.")
            while record._check_duplicate_deal_number(series_starting_value):
                series_starting_value += 1
                if series_starting_value > series_ending_value:
                    raise UserError("No available numbers in this series range.")
            record.odoo_deal_number_6digit = series_starting_value
            # record.name = series_starting_value This field is computed.
            series_record.starting_value = series_starting_value + 1

            # EXPORT CRM RECORD TO HUBSPOT DEAL
            record.export_deal_in_hubspot()
            record.message_post(
                body=(_('Deal Export Automatically to Hubspot (Deal Number Generated)')),
                message_type='comment',
                subtype_xmlid='mail.mt_note'
            )

    def _check_duplicate_deal_number(self, series_starting_value):
        base_url, hubspot_token = self._get_hubspot_config()
        if not hubspot_token:
            _logger.error("HubSpot API token not configured")
            return False
        headers = {
            'Authorization': f'Bearer {hubspot_token}',
            'Content-Type': 'application/json'
        }
        if series_starting_value:
            url = f"{base_url}/crm/v3/objects/deals/search"
            payload = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "odoo_deal_number_6digit",
                                "operator": "EQ",
                                "value": str(series_starting_value)
                            }
                        ]
                    }
                ],
                "properties": ["odoo_deal_number_6digit"],
                "limit": 1
            }
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                total_results = data.get('total', 0)
                if total_results > 0:
                    return True

    @api.depends('order_ids.state', 'order_ids.currency_id', 'order_ids.amount_total', 'order_ids.date_order',
                 'order_ids.company_id')
    def _compute_sale_data(self):
        for lead in self:
            company_currency = lead.company_currency or self.env.company.currency_id
            sale_orders = lead.order_ids.filtered_domain(
                self._get_action_view_project_quotation_domain())  # fetching the project qoute only
            lead.sale_amount_total = sum(
                order.currency_id._convert(
                    order.amount_untaxed, company_currency, order.company_id, order.date_order or fields.Date.today()
                )
                for order in sale_orders
            )
            lead.quotation_count = len(
                lead.order_ids.filtered_domain(self._get_action_view_sale_quotes_domain()))  # Using Custom Domain Here
            lead.sale_order_count = len(sale_orders)
            lead.project_quotation_count = len(
                lead.order_ids.filtered_domain(self._get_action_view_project_quotation_domain()))
            lead.delivery_stage_count = len(
                lead.order_ids.filtered_domain(self._get_action_view_delivery_stage_domain()))

    def action_view_sale_quotation(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale_custom_report.action_quotations_with_sale_quote_type")
        action['context'] = self._prepare_opportunity_quotation_context()
        action['context']['search_default_draft'] = 1
        action['domain'] = expression.AND(
            [[('opportunity_id', '=', self.id)], self._get_action_view_sale_quotes_domain()])
        quotations = self.order_ids.filtered_domain(self._get_action_view_sale_quotes_domain())
        if len(quotations) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = quotations.id
        return action

    def action_view_project_quotation(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale_custom_report.action_quotations_with_project_quote_type")
        action['context'] = self._prepare_opportunity_quotation_context()
        action['context']['search_default_draft'] = 1
        action['domain'] = expression.AND(
            [[('opportunity_id', '=', self.id)], self._get_action_view_project_quotation_domain()])
        quotations = self.order_ids.filtered_domain(self._get_action_view_project_quotation_domain())
        if len(quotations) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = quotations.id
        return action

    def action_view_delivery_stages(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale_custom_report.action_quotations_with_delivery_stage_quote_type")
        action['context'] = self._prepare_opportunity_quotation_context()
        action['context']['search_default_draft'] = 1
        action['domain'] = expression.AND(
            [[('opportunity_id', '=', self.id)], self._get_action_view_delivery_stage_domain()])
        quotations = self.order_ids.filtered_domain(self._get_action_view_delivery_stage_domain())
        if len(quotations) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = quotations.id
        return action

    def _get_action_view_project_quotation_domain(self):
        return [('quote_type', '=', 'project_quote')]

    def _get_action_view_sale_quotes_domain(self):
        return [('quote_type', '=', 'sales_quote')]

    def _get_action_view_delivery_stage_domain(self):
        return [('quote_type', '=', 'delivery_stage')]

    # Hubspot Deals Fetch and Process it to create the crm.Lead Record

    def _get_hubspot_config(self):
        """Retrieve HubSpot configuration from system parameters."""
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('burgtec_hubspot_customization.hubspot_integrations_token')
        base_url = params.get_param('burgtec_hubspot_customization.hubspot_base_url')
        return base_url, token

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

    def fetch_deal_owner(self, owner_id, url, token):
        """Fetch HubSpot deal owner and map to Odoo user."""
        res_user_obj = self.env['res.users'].sudo()

        url = f"{url}/crm/v3/owners/{owner_id}"

        headers = {
            'Authorization': f'Bearer {token}',
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            _logger.warning("Failed to fetch HubSpot owner")
            return False
        data = response.json()
        email = data.get('email')
        if not email:
            _logger.warning("HubSpot owner has no email: %s", data)
            return False
        res_user = res_user_obj.search([('email', '=', email)], limit=1)
        return res_user if res_user else False

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

    def associated_company_with_deal(self, deal_id, url, token):

        url = f"{url}/crm/v3/objects/deals/{deal_id}"
        params = {'associations': "companies"}
        headers = {
            'Authorization': f'Bearer {token}',
        }
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            # hubspot_company_id = data.get('associations').get('companies').get('results')[0].get('id')
            associations = data.get('associations')
            if not associations:
                _logger.warning(f"Deal {deal_id} has no associations")
                return False

            companies = associations.get('companies')
            if not companies:
                _logger.warning(f"Deal {deal_id} has no associated companies")
                return False

            results = companies.get('results', [])
            if not results:
                _logger.warning(f"Deal {deal_id} has empty company results")
                return False

            hubspot_company_id = results[0].get('id')
            if hubspot_company_id:
                url = f"https://api.hubapi.com/crm/v3/objects/companies/{hubspot_company_id}"
                headers = {
                    "Authorization": f"Bearer {token}"
                }
                query_params = {
                    "properties": ["name", "domain", "country", "phone", "city", "industry", "address", "state", "zip"],
                    "archived": "false"
                }
                response = requests.get(url, headers=headers, params=query_params)
                company_data = response.json()
                company_id = company_data.get('id')  # '3169092150'
                # Extract properties object
                properties = company_data.get('properties', {})

                # Map HubSpot properties to Odoo fields
                partner_vals = {
                    'name': properties.get('name') or properties.get('website'),
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
                Respartner = self.env['res.partner'].sudo()
                existing_partner = Respartner.search(
                    ["|", "|", "|", "|", "|", ("complete_name", "ilike", properties.get('name')),
                     ("ref", "ilike", properties.get('name')),
                     ("email", "ilike", properties.get('name')), ("vat", "ilike", properties.get('name')),
                     ("company_registry", "ilike", properties.get('name')), ("name", "ilike", properties.get('name'))],
                    limit=1)
                if not existing_partner:
                    # new_contact = Respartner.create(partner_vals)
                    # _logger.info(f"New contact Created. {new_contact.name}")

                    return False
                else:
                    _logger.info(f"Assigned Existing Contact. {existing_partner.name}")
                    return existing_partner

    def _get_state_id(self, state, country):
        country = self.env['res.country'].search([('name', '=', country)], limit=1)
        if country:
            state = self.env['res.country.state'].search([('country_id', '=', country.id), ('code', "=", state)],
                                                         limit=1)
            if state:
                return state.id

    def _get_country_id(self, country):
        country = self.env['res.country'].search([('name', '=', country)], limit=1)
        if country:
            return country.id

    def export_deal_in_hubspot(self):

        base_url, hubspot_token = self._get_hubspot_config()
        if not hubspot_token:
            _logger.error("HubSpot API token not configured")
            return False
        if not self.partner_id:
            raise ValidationError('First Assign the Contact to Crm Lead!')
        deal_number = self.odoo_deal_number_6digit
        if not deal_number:
            raise ValidationError("Please Generate the Deal Number!")
        # Get or create company
        # company_id = self.create_or_get_hubspot_company(self.partner_id, base_url, hubspot_token)
        headers = {
            'Authorization': f'Bearer {hubspot_token}',
            'Content-Type': 'application/json'
        }
        properties = {}
        params = self.env['ir.config_parameter'].sudo()
        web_url = params.get_param('web.base.url')
        if self:
            properties["odoo_crm_lead_url"] = f'{web_url}/odoo/crm/{self.id}'
            properties["in_odoo"] = True
        if deal_number:
            properties["odoo_deal_number_6digit"] = deal_number
        if self.name:
            properties["dealname"] = self.name

        if self.onedrive_folder_url:
            properties["onedrive_folder_url"] = self.onedrive_folder_url

        if self.deal_close_date:
            properties["closedate"] = int(self.deal_close_date.timestamp() * 1000)

        # if self.odoo_deal_owner_id.hubspot_owner_id:
        #     properties['hubspot_owner_id'] = int(self.odoo_deal_owner_id.hubspot_owner_id)
        if self.deal_stage_id:
            properties["dealstage"] = self.deal_stage_id.deal_stage_id
            properties['pipeline'] = self.get_pipeline_from_stage(self.deal_stage_id, hubspot_token)

        try:
            # update existing deal
            if self.id_of_hubspot_deal:
                url = f"{base_url}/crm/v3/objects/deals/{self.id_of_hubspot_deal}"
                payload = {"properties": properties}
                response = requests.patch(url, json=payload, headers=headers, timeout=30)
                if response.status_code == 200:
                    # if company_id:
                    #     self._associate_company_to_deal(self.id_of_hubspot_deal, company_id, base_url, headers)
                    _logger.info(f"✓ Updated HubSpot deal {self.id_of_hubspot_deal} for Lead {self.id} ({self.name})")
                    return {
                        'effect': {
                            'fadeout': 'slow',
                            'message': 'Deal Successfully Updated on HubSpot!',
                            'type': 'rainbow_man',
                        }
                    }
                else:
                    _logger.error(f"✗ Failed to update deal: {response.status_code}")
                    _logger.error(f"Response: {response.text}")
                    return False
            # create new deal in hubspot
            else:
                url = f"{base_url}/crm/v3/objects/deals"
                payload = {
                    "properties": properties,
                }
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                if response.status_code == 201:
                    data = response.json()
                    hubspot_deal_id = data.get("id")
                    hubspot_deal_url = data.get("url")
                    if not hubspot_deal_id:
                        _logger.error("No deal ID found in HubSpot response")
                        return False
                    self.write({"id_of_hubspot_deal": hubspot_deal_id,
                                'hubspot_deal_url': hubspot_deal_url,
                                'is_deal_exported': True})
                    # if company_id:
                    #     self._associate_company_to_deal(hubspot_deal_id, company_id, base_url, headers)
                    _logger.info(f"✓ Created HubSpot deal {hubspot_deal_id} for Lead {self.id} ({self.name})")
                    return {
                        'effect': {
                            'fadeout': 'slow',
                            'message': 'Deal Successfully Exported to HubSpot!',
                            'type': 'rainbow_man',
                        }
                    }
                else:
                    _logger.error(f"✗ Failed to create deal: {response.status_code}")
                    _logger.error(f"Response: {response.text}")
                    return False
        except Exception as e:
            _logger.error(f"✗ Exception syncing deal: {str(e)}")
            return False

    def _export_computed_fields_in_hubspot(self):

        base_url, hubspot_token = self._get_hubspot_config()
        if not hubspot_token:
            _logger.error("HubSpot API token not configured")
            return False
        headers = {
            'Authorization': f'Bearer {hubspot_token}',
            'Content-Type': 'application/json'
        }
        properties = {}
        if self.latest_quote_sent_amount:
            properties["last_quotation_sent_amount"] = self.latest_quote_sent_amount
        if self.latest_odoo_quote_gp_amount:
            properties["latest_odoo_quote_gp_amount"] = self.latest_odoo_quote_gp_amount
        if self.latest_odoo_quote_number_of_item_lines:
            properties['latest_quote__line_items'] = self.latest_odoo_quote_number_of_item_lines
        try:
            if self.id_of_hubspot_deal:
                url = f"{base_url}/crm/v3/objects/deals/{self.id_of_hubspot_deal}"
                payload = {"properties": properties}
                response = requests.patch(url, json=payload, headers=headers, timeout=30)
                if response.status_code == 200:
                    _logger.info(
                        f"✅ Updated HubSpot Deal Latest Computed Fields {self.id_of_hubspot_deal} for Lead {self.id} ({self.name})")

                    return True
                else:
                    _logger.error(f"❎ Failed to Updated HubSpot Deal Latest Computed Fields: {response.status_code}")
                    _logger.error(f"Response: {response.text}")
                    return False
        except Exception as e:
            _logger.error(f"HubSpot Exception: {str(e)}")
            return False

    def get_pipeline_from_stage(self, stage_id, hubspot_token):
        url = "https://api.hubapi.com/crm/v3/pipelines/deals"

        headers = {
            "Authorization": f"Bearer {hubspot_token}"
        }
        response = requests.get(url, headers=headers)
        data = response.json()
        for pipeline in data.get("results", []):
            for stage in pipeline.get("stages", []):
                if stage.get("id") == stage_id.deal_stage_id:
                    return pipeline.get("id")

        return None

    def import_deal_from_hubspot(self):
        """Import/sync deal data from HubSpot to this CRM Lead"""
        base_url, hubspot_token = self._get_hubspot_config()
        if not hubspot_token:
            _logger.error("HubSpot API token not configured")
            return False
        if not self.id_of_hubspot_deal:
            _logger.warning(f"CRM Lead {self.id} has no HubSpot deal ID to import from")
            return False
        headers = {
            'Authorization': f'Bearer {hubspot_token}',
            'Content-Type': 'application/json'
        }
        # Properties to fetch from HubSpot
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
            'project_location'
        ]

        try:
            # Fetch the deal from HubSpot
            url = f"{base_url}/crm/v3/objects/deals/{self.id_of_hubspot_deal}"
            params = {"properties": ','.join(properties)}
            response = requests.get(url, params=params, headers=headers, timeout=30)
            if response.status_code != 200:
                _logger.error(f"HubSpot API error: {response.status_code} - {response.text}")
                return False
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
            # Extract deal properties
            deal_id = self.id_of_hubspot_deal
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
            if hubspot_owner_id:
                deal_owner_name = self.fetch_deal_owner_name(hubspot_owner_id, base_url, hubspot_token)
            if quoted_by_id:
                quoted_by_name = self.fetch_quoted_by_name(quoted_by_id, base_url, hubspot_token)

            if deal_stage:
                deal_stage_record = self.env['deal.stage'].search([('deal_stage_id', '=', deal_stage)],
                                                                  limit=1)
                deal_stage_id = deal_stage_record.id if deal_stage_record else False

            if deal_type:
                deal_type_record = self.env['deal.type'].search([('hubspot_value', '=', deal_type)],
                                                                limit=1)
                deal_type_id = deal_type_record.id if deal_type_record else False

            if pipeline_stage:
                pipeline_stage_record = self.env['deal.pipeline.stage'].search(
                    [('hubspot_internal_name', '=', pipeline_stage)], limit=1)
                pipeline_stage_id = pipeline_stage_record.id if pipeline_stage_record else False

            if project_location:
                project_location_record = self.env['deal.location'].search(
                    [('hubspot_internal_name', '=', project_location)], limit=1)
                project_location_id = project_location_record.id if project_location_record else False

            # Prepare CRM lead values
            lead_vals = {
                'name': dealname,
                'expected_revenue': float(amount) if amount else 0.0,
                'deal_create_date': createdate or False,
                'deal_close_date': close_date or False,
                # 'deal_stage_id': deal_stage_id or False,
                # 'deal_type_id': deal_type_id or False,
                # 'deal_pipeline_and_stage_id': pipeline_stage_id or False,
                'deal_date_quoted': dated_quoted or False,
                # 'quoted_by': quoted_by_name or '',
                'deal_probability': deal_stage_record.probability if deal_stage_record else False,
                'deal_quoted_gp_percentage': properties_data.get('gppercent'),
                'deal_quoted_gp_value': properties_data.get('gp__'),
                # 'deal_territory_id': project_location_id or False,
                'is_deal_imported': True,
                # 'deal_owner': deal_owner_name or '',
            }
            # Update this CRM lead with HubSpot data
            self.write(lead_vals)
            _logger.info(f"✓ Successfully imported HubSpot deal {self.id_of_hubspot_deal} to CRM Lead {self.id}")
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Deal Successfully Imported from HubSpot!',
                    'type': 'rainbow_man',
                }
            }
        except Exception as e:
            _logger.error(f"✗ Exception importing deal from HubSpot: {str(e)}")
            return False

    def create_or_get_hubspot_company(self, partner, base_url, token):
        """Check if HubSpot company exists. If not, create it."""

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # CHECK IF COMPANY ID EXISTS IN ODOO RECORD
        if partner.id_of_hubspot_company:
            url = f"{base_url}/crm/v3/objects/companies/{partner.id_of_hubspot_company}"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return partner.id_of_hubspot_company

        # SEARCH HUBSPOT BY COMPANY NAME
        if partner.name:
            search_url = f"{base_url}/crm/v3/objects/companies/search"
            search_payload = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "name",
                                "operator": "EQ",
                                "value": partner.name,
                            }
                        ]
                    }
                ],
                "properties": ["name", "hs_object_id"],
                "associations": ["companies"],
                "limit": 1,
            }
            search_response = requests.post(search_url, headers=headers, json=search_payload)

            if search_response.status_code == 200:
                results = search_response.json().get("results", [])
                if results:
                    # Try top-level id first
                    existing_company_id = results[0].get("id")
                    if existing_company_id:
                        partner.sudo().id_of_hubspot_company = existing_company_id
                        return existing_company_id

            # CREATE NEW COMPANY IN HUBSPOT
            create_url = f"{base_url}/crm/v3/objects/companies"
            payload = {
                "properties": {
                    "name": partner.name,
                    "address": partner.street or "",
                    "city": partner.city or "",
                    "state": partner.state_id.name if partner.state_id else "",
                    "country": partner.country_id.name if partner.country_id else "",
                    "phone": partner.phone or "",
                    "website": partner.website or "",
                }
            }
            create_response = requests.post(create_url, headers=headers, json=payload)
            if create_response.status_code == 201:
                new_company_id = create_response.json().get("id")
                partner.sudo().id_of_hubspot_company = new_company_id
                return new_company_id

            raise Exception(f"Failed to create company in HubSpot: {create_response.text}")

        raise Exception(f"Cannot sync company to HubSpot: partner '{partner.id}' has no name.")

    def _associate_company_to_deal(self, deal_id, company_id, base_url, headers):
        """Associate a HubSpot company to a deal using v4 Associations API."""
        url = f"{base_url}/crm/v4/objects/deals/{deal_id}/associations/companies/{company_id}"
        payload = [
            {
                "associationCategory": "HUBSPOT_DEFINED",
                "associationTypeId": 341
            }
        ]
        response = requests.put(url, json=payload, headers=headers, timeout=30)
        if response.status_code in (200, 201):
            _logger.info(f"✓ Associated company {company_id} to deal {deal_id}")
        else:
            _logger.warning(
                f"✗ Failed to associate company {company_id} to deal {deal_id}: {response.status_code} - {response.text}")

    # SCHEDULE ACTION THAT WILL RUN DAILY TO UPDATE THE ALL CRM LEAD FROM HUBSPOT --> ODOO

    def sync_deals_from_hubspot(self):
        """
        Fetch deals from HubSpot and create/update CRM leads one by one.
        This method can be called from a scheduled action or manually.
        """
        _logger.info("Starting HubSpot deals synchronization...")
        properties = [
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
            'odoo_deal_number_6digit',
            'hs_is_closed_won',
            'hs_is_closed_lost',
        ]

        base_url, hubspot_token = self._get_hubspot_config()

        if not hubspot_token:
            _logger.error("HubSpot API token not configured")
            return

        url = f"{base_url}/crm/v3/objects/deals/search"
        headers = {
            'Authorization': f'Bearer {hubspot_token}',
            'Content-Type': 'application/json'
        }

        CrmLead = self.env['crm.lead'].sudo()
        after = None
        batch_size = 100
        batch_count = 0
        total_processed = 0
        total_created = 0
        total_updated = 0
        total_errors = 0

        try:
            while True:
                batch_count += 1
                _logger.info(f"Fetching batch {batch_count} of deals from HubSpot...")
                cutoff_date = datetime(2020, 12, 31)
                cutoff_timestamp_ms = int(cutoff_date.timestamp() * 1000)  # Convert to milliseconds

                payload = {
                    "filterGroups": [
                        {
                            "filters": [
                                # Filter 1: Check if the date is AFTER 31/12/2020.
                                # This also implicitly ensures the date is not null/empty.
                                {
                                    "propertyName": "in_odoo",
                                    "operator": "NEQ",
                                    "value": "true"
                                },
                                # {
                                #     "propertyName": "in_odoo",
                                #     "operator": "HAS_PROPERTY",
                                # },
                                {
                                    "propertyName": "odoo_deal_number_6digit",
                                    "operator": "HAS_PROPERTY"
                                }
                            ]
                        }
                    ],
                    "properties": properties,
                    "limit": batch_size,
                    "after": after
                }

                response = requests.post(url, json=payload, headers=headers, timeout=30)

                if response.status_code != 200:
                    _logger.error(f"HubSpot API error: {response.status_code} - {response.text}")
                    break

                data = response.json()
                results = data.get('results', [])

                if not results:
                    _logger.info("No more deals to fetch")
                    break

                _logger.info(f"Processing {len(results)} deals from batch {batch_count}...")

                # Process each deal immediately
                for deal in results:
                    try:
                        deal_type_id = False
                        pipeline_stage_id = False
                        project_location_id = False
                        deal_owner_name = ""
                        quoted_by_name = ""
                        deal_id = deal.get('id')
                        properties_data = deal.get('properties', {})
                        # Extract deal properties
                        dealname = properties_data.get('dealname', f'Deal {deal_id}')
                        amount = properties_data.get('amount')
                        createdate = self._parse_hubspot_date(properties_data.get('createdate'))
                        close_date = self._parse_hubspot_date(properties_data.get('closedate'))
                        dated_quoted = self._parse_hubspot_date(properties_data.get('dated_quoted'))
                        deal_type = properties_data.get('dealtype')
                        deal_stage = properties_data.get('dealstage')
                        odoo_deal_number_6digit = properties_data.get('odoo_deal_number_6digit')
                        pipeline_stage = properties_data.get('pipeline_stage')
                        project_location = properties_data.get('project_location')
                        is_closed_won = properties_data.get('hs_is_closed_won')
                        is_closed_lost = properties_data.get('hs_is_closed_lost')
                        hubspot_deal_url = deal.get('url')
                        hubspot_owner_id = properties_data.get('hubspot_owner_id')
                        quoted_by_id = properties_data.get('quoted_by')
                        if hubspot_owner_id:
                            user = self.fetch_deal_owner(hubspot_owner_id, base_url, hubspot_token)
                            deal_owner_name = self.fetch_deal_owner_name(hubspot_owner_id, base_url, hubspot_token)
                        if quoted_by_id:
                            quoted_by_name = self.fetch_quoted_by_name(quoted_by_id, base_url, hubspot_token)

                        if deal_id:
                            company = self.associated_company_with_deal(deal_id, base_url, hubspot_token)
                        if deal_stage:
                            deal_stage_record = self.env['deal.stage'].search([('deal_stage_id', '=', deal_stage)],
                                                                              limit=1)
                            deal_stage_id = deal_stage_record.id if deal_stage_record else False

                        if deal_type:
                            deal_type_record = self.env['deal.type'].search([('hubspot_value', '=', deal_type)],
                                                                            limit=1)
                            deal_type_id = deal_type_record.id if deal_type_record else False

                        if pipeline_stage:
                            pipeline_stage_record = self.env['deal.pipeline.stage'].search(
                                [('hubspot_internal_name', '=', pipeline_stage)], limit=1)
                            pipeline_stage_id = pipeline_stage_record.id if pipeline_stage_record else False

                        if project_location:
                            project_location_record = self.env['deal.location'].search(
                                [('hubspot_internal_name', '=', project_location)], limit=1)
                            project_location_id = project_location_record.id if project_location_record else False

                        # Prepare CRM lead values
                        lead_vals = {
                            'name': dealname,
                            'partner_id': company.id if company else False,
                            'phone': company.phone if company else False,
                            'id_of_hubspot_deal': deal_id,
                            'expected_revenue': float(amount) if amount else 0.0,
                            'deal_create_date': createdate or False,
                            'deal_close_date': close_date or False,
                            'deal_stage_id': deal_stage_id,
                            'deal_type_id': deal_type_id,
                            'deal_pipeline_and_stage_id': pipeline_stage_id,
                            'deal_date_quoted': dated_quoted,
                            'quoted_by': quoted_by_name or '',
                            'deal_probability': deal_stage_record.probability if deal_stage_record else False,
                            'deal_quoted_gp_percentage': properties_data.get('gppercent'),
                            'deal_quoted_gp_value': properties_data.get('gp__'),
                            'deal_territory_id': project_location_id,
                            'odoo_deal_number_6digit': odoo_deal_number_6digit,
                            'is_old_deal': True,
                            'is_closed_won': False if is_closed_won == 'false' else True,
                            'is_closed_lost': False if is_closed_lost == 'false' else True,
                            'user_id': user.id if user else False,
                            'deal_owner': deal_owner_name or '',
                            'hubspot_deal_url': hubspot_deal_url
                        }

                        # Check if CRM lead with this hubspot_deal_id already exists
                        existing_lead = CrmLead.search([
                            ('id_of_hubspot_deal', '=', deal_id)
                        ], limit=1)

                        if existing_lead:
                            # Update existing lead
                            existing_lead.write(lead_vals)
                            total_updated += 1
                            _logger.info(
                                f"Updated CRM Lead for HubSpot Deal {deal_id} (Lead ID: {existing_lead.id})")
                        else:
                            # Create new lead
                            new_lead = CrmLead.create(lead_vals)
                            total_created += 1
                            _logger.info(f"Created CRM Lead for HubSpot Deal {deal_id} (Lead ID: {new_lead.id})")

                        total_processed += 1
                        _logger.info(f"Total Processed Hubspot Deals So Far. {total_processed}")

                    except Exception as e:
                        total_errors += 1
                        _logger.error(f"Error processing deal {deal.get('id')}: {str(e)}")
                        continue

                # Commit after each batch
                self.env.cr.commit()
                _logger.info(
                    f"Batch {batch_count} committed. Processed: {total_processed}, Created: {total_created}, Updated: {total_updated}, Errors: {total_errors}")
                # break
                # Check for pagination
                paging = data.get('paging', {})
                after = paging.get('next', {}).get('after')

                if not after:
                    break

            _logger.info(
                f"HubSpot deals synchronization completed. Total - Processed: {total_processed}, Created: {total_created}, Updated: {total_updated}, Errors: {total_errors}")

        except Exception as e:
            _logger.error(f"Unexpected error during synchronization: {str(e)}")
            self.env.cr.rollback()

    def fetch_hubspot_deals_stages_to_odoo(self):
        url = "https://api.hubapi.com/crm/v3/pipelines/deals"
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('burgtec_hubspot_customization.hubspot_integrations_token')
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(url, headers=headers)
        pipelines = response.json()
        stage_model = self.env['deal.stage']
        for pipeline in pipelines.get('results', []):
            for stage in pipeline.get('stages', []):
                vals = {
                    'name': stage['label'],
                    'deal_stage_id': stage['id'],
                    'pipeline_id': pipeline['id'],
                    'pipeline_name': pipeline['label'],
                    'probability': stage.get('metadata', {}).get('probability', 0),
                }
                existing = stage_model.search([('deal_stage_id', '=', stage['id'])], limit=1)
                if existing:
                    existing.write(vals)
                else:
                    stage_model.create(vals)

    def fetch_hubspot_deals_types_to_odoo(self):
        url = "https://api.hubapi.com/crm/v3/properties/deal/dealtype"
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('burgtec_hubspot_customization.hubspot_integrations_token')
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(url, headers=headers)
        resp_json = response.json()

        deal_type_model = self.env['deal.type']

        for opt in resp_json.get('options', []):
            vals = {
                'name': opt.get('label'),
                'hubspot_value': opt.get('value'),
            }

            existing = deal_type_model.search([('hubspot_value', '=', opt.get('value'))], limit=1)

            if existing:
                existing.write(vals)
            else:
                deal_type_model.create(vals)

    def fetch_hubspot_deals_project_locations(self):
        url = "https://api.hubapi.com/crm/v3/properties/deal/project_location"
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('burgtec_hubspot_customization.hubspot_integrations_token')
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(url, headers=headers)
        data = response.json()

        loc_model = self.env['deal.location']

        for opt in data.get('options', []):
            vals = {
                'name': opt.get('label'),
                'hubspot_internal_name': opt.get('value'),
            }

            existing = loc_model.search([('hubspot_internal_name', '=', opt.get('value'))], limit=1)

            if existing:
                existing.write(vals)
            else:
                loc_model.create(vals)

    def fetch_hubspot_deals_pipeline_stage(self):

        url = "https://api.hubapi.com/crm/v3/properties/deal/pipeline_stage"
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('burgtec_hubspot_customization.hubspot_integrations_token')
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(url, headers=headers)
        data = response.json()

        loc_model = self.env['deal.pipeline.stage']

        for opt in data.get('options', []):
            vals = {
                'name': opt.get('label'),
                'hubspot_internal_name': opt.get('value'),
            }

            existing = loc_model.search([('hubspot_internal_name', '=', opt.get('value'))], limit=1)

            if existing:
                existing.write(vals)
            else:
                loc_model.create(vals)

        # BELOW IS THE CODE THAT WILL EXPORT THE NEW CRM LEAD TO THE HUBSPOT AS A DEAL

    def _automatic_sync_leads_data_from_hubspot_to_odoo(self):
        base_url, hubspot_token = self._get_hubspot_config()
        if not hubspot_token:
            _logger.error("HubSpot API token not configured")
            return False

        headers = {
            'Authorization': f'Bearer {hubspot_token}',
            'Content-Type': 'application/json'
        }

        # Properties to fetch from HubSpot
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
            'project_location'
        ]
        create_date_last_7_days = fields.Datetime.now() - timedelta(days=7)
        crm_lead_of_last_7_days = self.env['crm.lead'].search(
            [('create_date', '>=', create_date_last_7_days), ('is_old_deal', '=', False)])
        filtered_crm = crm_lead_of_last_7_days.filtered(lambda l: l.id_of_hubspot_deal)
        for lead in filtered_crm:
            crm_lead_hubspot_id = int(lead.id_of_hubspot_deal)
            try:
                # Fetch the deal from HubSpot
                url = f"{base_url}/crm/v3/objects/deals/{crm_lead_hubspot_id}"
                params = {"properties": ','.join(properties)}

                response = requests.get(url, params=params, headers=headers, timeout=30)

                if response.status_code != 200:
                    _logger.error(f"HubSpot API error: {response.status_code} - {response.text}")
                    return False

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

                # Extract deal properties
                deal_id = lead.id_of_hubspot_deal
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
                if hubspot_owner_id:
                    deal_owner_name = self.fetch_deal_owner_name(hubspot_owner_id, base_url, hubspot_token)
                if quoted_by_id:
                    quoted_by_name = self.fetch_quoted_by_name(quoted_by_id, base_url, hubspot_token)

                # Get associated company
                company_id = self.associated_company_with_deal(deal_id, base_url, hubspot_token)

                if deal_stage:
                    deal_stage_record = self.env['deal.stage'].search([('deal_stage_id', '=', deal_stage)],
                                                                      limit=1)
                    deal_stage_id = deal_stage_record.id if deal_stage_record else False

                if deal_type:
                    deal_type_record = self.env['deal.type'].search([('hubspot_value', '=', deal_type)],
                                                                    limit=1)
                    deal_type_id = deal_type_record.id if deal_type_record else False

                if pipeline_stage:
                    pipeline_stage_record = self.env['deal.pipeline.stage'].search(
                        [('hubspot_internal_name', '=', pipeline_stage)], limit=1)
                    pipeline_stage_id = pipeline_stage_record.id if pipeline_stage_record else False

                if project_location:
                    project_location_record = self.env['deal.location'].search(
                        [('hubspot_internal_name', '=', project_location)], limit=1)
                    project_location_id = project_location_record.id if project_location_record else False

                # Prepare CRM lead values
                lead_vals = {
                    'name': dealname,
                    'partner_id': company_id.id if company_id else False,
                    'phone': company_id.phone if company_id else False,
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
                    'deal_owner': deal_owner_name or '',
                }

                # Update this CRM lead with HubSpot data
                lead.write(lead_vals)
                _logger.info(f"✓ Successfully Updated CRM Lead with Respective Hubspot deal Data")
            except Exception as e:
                _logger.error(f"✗ Exception Updated deal from HubSpot: {str(e)}")
                return False

    def _automatic_sync_deals_data_from_odoo_to_hubspot(self):

        base_url, hubspot_token = self._get_hubspot_config()
        if not hubspot_token:
            _logger.error("HubSpot API token not configured")
            return False

        headers = {
            'Authorization': f'Bearer {hubspot_token}',
            'Content-Type': 'application/json'
        }
        properties = {}
        create_date_last_7_days = fields.Datetime.now() - timedelta(days=7)
        crm_lead_of_last_7_days = self.env['crm.lead'].search(
            [('create_date', '>=', create_date_last_7_days), ('is_old_deal', '=', False)])
        filtered_crm = crm_lead_of_last_7_days.filtered(lambda l: l.id_of_hubspot_deal)
        for lead_record in filtered_crm:
            if lead_record.name:
                properties["dealname"] = lead_record.name
            if lead_record.latest_quote_sent_amount:
                properties["last_quotation_sent_amount"] = lead_record.latest_quote_sent_amount
            try:
                # -----------------------------
                # UPDATE EXISTING DEAL
                # -----------------------------
                if lead_record.id_of_hubspot_deal:
                    url = f"{base_url}/crm/v3/objects/deals/{lead_record.id_of_hubspot_deal}"
                    payload = {"properties": properties}

                    response = requests.patch(url, json=payload, headers=headers, timeout=30)
                    if response.status_code == 200:
                        _logger.info(
                            f"✓ Updated HubSpot deal {lead_record.id_of_hubspot_deal} for Lead {lead_record.id} ({lead_record.name})")
                        return {
                            'effect': {
                                'fadeout': 'slow',
                                'message': 'Deal Successfully Updated on HubSpot!',
                                'type': 'rainbow_man',
                            }
                        }
                    else:
                        _logger.error(f"✗ Failed to update deal: {response.status_code}")
                        _logger.error(f"Response: {response.text}")
                        return False
            except Exception as e:
                _logger.error(f"✗ Exception syncing deal: {str(e)}")
                return False

    def fix_contacts_crm_deals(self):
        total_processed = 0
        total_fixed = 0
        for record in self:
            total_processed += 1
            current_contact = record.partner_id
            current_contact_name = current_contact.name
            exact_matched_record = record.env['res.partner'].sudo().search([
                "|", "|", "|", "|", "|",
                ("complete_name", "ilike", current_contact_name),
                ("ref", "ilike", current_contact_name),
                ("email", "ilike", current_contact_name),
                ("vat", "ilike", current_contact_name),
                ("company_registry", "ilike", current_contact_name),
                ("name", "ilike", current_contact_name),
            ])
            odoo_cont = exact_matched_record.filtered(lambda l: not l.id_of_hubspot_company)
            if not odoo_cont:
                words = re.split(r'[^a-z0-9]+', current_contact_name.lower())
                words = [w for w in words if w]  # Remove empty strings

                # Build dynamic domain for each word
                domain = []
                for word in words:
                    domain += [
                        "|", "|", "|", "|", "|",
                        ("complete_name", "ilike", word),
                        ("ref", "ilike", word),
                        ("email", "ilike", word),
                        ("vat", "ilike", word),
                        ("company_registry", "ilike", word),
                        ("name", "ilike", word),
                    ]

                # Combine multiple words with OR
                if len(words) > 1:
                    for _ in range(len(words) - 1):
                        domain = ["|"] + domain

                existing_conts = record.env['res.partner'].sudo().search(domain)

                odoo_cont = existing_conts.filtered(lambda l: not l.id_of_hubspot_company)

            if len(odoo_cont) == 1:
                total_fixed += 1
                _logger.info(f"✓ Successfully Fixed CRM Deal Contact {total_fixed}")
                self.write(
                    {
                        'partner_id': odoo_cont.id,
                        'is_fixed': True,
                        'fixed_description': f"OLD Partner Data: ({self.partner_id.id}, {self.partner_id.name}) -----> New Partner Data: ({odoo_cont.id}, {odoo_cont.name})",
                    }
                )
            total_processed += 1
            _logger.info(f"✓ Successfully Processed Deals So Far{total_processed}")

    def set_partner_from_sale_quote(self):
        total_processed = 0
        for record in self:
            orders = record.order_ids
            sale_partner = False
            if orders:
                sale_partner = orders[0].partner_id
            if sale_partner:
                record.sudo().write({
                    'partner_id': sale_partner.id,
                    'fixed_description': f"Changed OLD Partner Data From Sale Quote: ({self.partner_id.id}, {self.partner_id.name}) -----> New Partner Data From Sale Quote: ({sale_partner.id}, {sale_partner.name})",
                })
            total_processed += 1
            _logger.info(f"✓ Successfully Processed Deals So Far {total_processed}")

            # ________________________________________________________

    def action_sync_quote_fields_to_hubspot(self):
        base_url, hubspot_token = self._get_hubspot_config()
        if not hubspot_token:
            _logger.error("HubSpot API token not configured")
            return False

        headers = {
            'Authorization': f'Bearer {hubspot_token}',
            'Content-Type': 'application/json',
        }

        for lead in self:
            if not lead.id_of_hubspot_deal:
                _logger.warning("Lead %s (%s) has no HubSpot deal ID — skipping", lead.id, lead.name)
                continue

            properties = {}
            if lead.latest_quote_sent_amount:
                properties["last_quotation_sent_amount"] = lead.latest_quote_sent_amount
            if lead.latest_odoo_quote_gp_amount:
                properties["latest_odoo_quote_gp_amount"] = lead.latest_odoo_quote_gp_amount
            # if lead.latest_odoo_quote_gp_percentage:
            #     properties["latest_odoo_quote_gp"] = lead.latest_odoo_quote_gp_percentage
            if lead.latest_odoo_quote_number_of_item_lines:
                properties["latest_quote__line_items"] = lead.latest_odoo_quote_number_of_item_lines

            if not properties:
                _logger.info("Lead %s (%s) has no quote data — skipping", lead.id, lead.name)
                continue

            try:
                url = f"{base_url}/crm/v3/objects/deals/{lead.id_of_hubspot_deal}"
                response = requests.patch(url, json={"properties": properties}, headers=headers, timeout=30)
                if response.status_code == 200:
                    _logger.info("Updated HubSpot deal %s for lead %s (%s)", lead.id_of_hubspot_deal, lead.id,
                                 lead.name)
                else:
                    _logger.error("Failed to update deal %s — HTTP %s: %s", lead.id_of_hubspot_deal,
                                  response.status_code, response.text)
            except Exception as exc:
                _logger.exception("Exception on deal %s for lead %s: %s", lead.id_of_hubspot_deal, lead.id, exc)

    def action_site_details_xlsx(self):
        self.ensure_one()
        record = self
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Site Details")

        # Formats (1 = thin, 2 = thick, 0 = none)
        base = {"text_wrap": True, "valign": "vcenter", "border_color": "#000000"}
        title = {**base, "bold": True, "font_size": 16, "bg_color": "#B7DEE8", "align": "center",
                 "top": 2, "bottom": 2}
        label = {**base, "bold": True, "bg_color": "#B7DEE8", "align": "left", "indent": 1,
                 "top": 1, "bottom": 1, "left": 2, "right": 1}
        value = {**base, "align": "left", "indent": 1, "top": 1, "bottom": 1, "left": 1}
        value_mid = {**base, "top": 1, "bottom": 1}
        value_end = {**base, "top": 1, "bottom": 1, "right": 2}
        grid = {**base, "align": "center", "top": 1, "bottom": 1, "left": 1, "right": 1}

        title_fmt = workbook.add_format({**title, "left": 2})
        title_mid_fmt = workbook.add_format(title)
        title_end_fmt = workbook.add_format({**title, "right": 2})

        label_fmt = workbook.add_format(label)
        label_first_fmt = workbook.add_format({**label, "top": 2})
        label_last_fmt = workbook.add_format({**label, "bottom": 2})

        value_fmt = workbook.add_format(value)
        value_first_fmt = workbook.add_format({**value, "top": 2})
        value_last_fmt = workbook.add_format({**value, "bottom": 2})

        value_mid_fmt = workbook.add_format(value_mid)
        value_mid_first_fmt = workbook.add_format({**value_mid, "top": 2})
        value_mid_last_fmt = workbook.add_format({**value_mid, "bottom": 2})

        value_end_fmt = workbook.add_format(value_end)
        value_end_first_fmt = workbook.add_format({**value_end, "top": 2})
        value_end_last_fmt = workbook.add_format({**value_end, "bottom": 2})

        grid_hdr_fmt = workbook.add_format({**grid, "bold": True, "bg_color": "#B7DEE8"})
        grid_hdr_end_fmt = workbook.add_format({**grid, "bold": True, "bg_color": "#B7DEE8", "right": 2})
        grid_fmt = workbook.add_format(grid)
        grid_end_fmt = workbook.add_format({**grid, "right": 2})
        grid_na_end_fmt = workbook.add_format({**grid, "right": 2, "font_color": "#A6A6A6"})

        # Column widths: A = spacer, B = labels, C:E = values (merged)
        sheet.set_column(0, 0, 2)
        sheet.set_column(1, 1, 35)
        sheet.set_column(2, 4, 24)

        # Row 1: spacer
        sheet.set_row(0, 10)

        # Row 2: title
        sheet.set_row(1, 35)
        sheet.merge_range(1, 1, 1, 4, "Burgtec Site Details", title_fmt)
        sheet.write_blank(1, 2, None, title_mid_fmt)
        sheet.write_blank(1, 3, None, title_mid_fmt)
        sheet.write_blank(1, 4, None, title_end_fmt)

        # Row 3+: label (col B) and value (merged C:E)
        yes_no = {"yes": "Yes", "no": "No"}
        install_date = record.required_installation_date
        complete_date = record.required_completion_date

        def fmt_date(d, empty=""):
            return d.strftime("%d/%m/%Y") if d else empty

        sheet.write(2, 1, "Report Date", label_first_fmt)
        sheet.merge_range(2, 2, 2, 4, fields.Date.context_today(self).strftime("%d/%m/%Y"), value_first_fmt)
        sheet.write(3, 1, "Site Address", label_fmt)
        sheet.merge_range(3, 2, 3, 4, record.site_address or "", value_fmt)
        sheet.write(4, 1, "Site Contact - Name", label_fmt)
        sheet.merge_range(4, 2, 4, 4, record.site_contact_name or "", value_fmt)
        sheet.write(5, 1, "Site Contact - Mobile No", label_fmt)
        sheet.merge_range(5, 2, 5, 4, record.site_contact_mobile or "", value_fmt)
        sheet.write(6, 1, "Required Installation Date", label_fmt)
        sheet.merge_range(6, 2, 6, 4, fmt_date(install_date), value_fmt)
        sheet.write(7, 1, "Required Completion Date", label_fmt)
        sheet.merge_range(7, 2, 7, 4, fmt_date(complete_date), value_fmt)
        sheet.write(8, 1, "Access Times", label_fmt)
        sheet.merge_range(8, 2, 8, 4, record.access_times or "", value_fmt)
        sheet.write(9, 1, "Final Furniture Plan", label_fmt)
        sheet.merge_range(9, 2, 9, 4, record.final_furniture_plan or "", value_fmt)
        sheet.write(10, 1, "Loading Dock Available", label_fmt)
        sheet.merge_range(10, 2, 10, 4, yes_no.get(record.loading_dock_available, ""), value_fmt)
        sheet.write(11, 1, "Loading Dock Booking Required", label_fmt)
        sheet.merge_range(11, 2, 11, 4, yes_no.get(record.loading_dock_booking_required, ""), value_fmt)
        sheet.write(12, 1, "Loading Dock Height Clearance", label_fmt)
        sheet.merge_range(12, 2, 12, 4, record.loading_dock_height_clearance or "", value_fmt)
        sheet.write(13, 1, "Loading Dock Notes", label_fmt)
        sheet.merge_range(13, 2, 13, 4, record.loading_dock_notes or "", value_fmt)
        sheet.write(14, 1, "Alternate Unloading Area", label_fmt)
        sheet.merge_range(14, 2, 14, 4, record.alternate_unloading_area or "", value_fmt)
        sheet.write(15, 1, "Forklift Available", label_fmt)
        sheet.merge_range(15, 2, 15, 4, yes_no.get(record.forklift_available, ""), value_fmt)
        sheet.write(16, 1, "Semi-trailer Access", label_fmt)
        sheet.merge_range(16, 2, 16, 4, yes_no.get(record.semi_trailer_access, ""), value_fmt)
        sheet.write(17, 1, "Lift Available", label_fmt)
        sheet.merge_range(17, 2, 17, 4, record.lift_available or "", value_fmt)
        sheet.write(18, 1, "Lift Dimensions", label_fmt)
        sheet.merge_range(18, 2, 18, 4, record.lift_dimensions or "", value_fmt)
        sheet.write(19, 1, "No Lift - Flights of Stairs", label_fmt)
        sheet.merge_range(19, 2, 19, 4, record.stairs_flights or "", value_fmt)
        sheet.write(20, 1, "Permits/Inductions Required", label_fmt)
        sheet.merge_range(20, 2, 20, 4, record.permits_inductions or "", value_fmt)
        sheet.write(21, 1, "PPE Requirement", label_fmt)
        sheet.merge_range(21, 2, 21, 4, record.ppe_requirement or "", value_fmt)

        # Compliance documents grid: header + SWMS / Insurances / O&M (C, D, E not merged)
        sheet.write(22, 1, "Document", label_fmt)
        sheet.write(22, 2, "Required", grid_hdr_fmt)
        sheet.write(22, 3, "Submitted Date", grid_hdr_fmt)
        sheet.write(22, 4, "Approved Date", grid_hdr_end_fmt)

        sheet.write(23, 1, "SWMS", label_fmt)
        sheet.write(23, 2, yes_no.get(record.swms_required, ""), grid_fmt)
        sheet.write(23, 3, fmt_date(record.swms_submitted_date, "-"), grid_fmt)
        sheet.write(23, 4, fmt_date(record.swms_approved_date, "-"), grid_end_fmt)

        sheet.write(24, 1, "Insurances", label_fmt)
        sheet.write(24, 2, yes_no.get(record.insurance_required, ""), grid_fmt)
        sheet.write(24, 3, fmt_date(record.insurance_submitted_date, "-"), grid_fmt)
        sheet.write(24, 4, "N/A", grid_na_end_fmt)

        sheet.write(25, 1, "O&M", label_fmt)
        sheet.write(25, 2, yes_no.get(record.om_required, ""), grid_fmt)
        sheet.write(25, 3, fmt_date(record.om_submitted_date, "-"), grid_fmt)
        sheet.write(25, 4, "N/A", grid_na_end_fmt)

        sheet.write(26, 1, "Access Photos Provided", label_fmt)
        sheet.merge_range(26, 2, 26, 4, yes_no.get(record.access_photos_provided, ""), value_fmt)
        sheet.write(27, 1, "Other Instructions/Notes", label_last_fmt)
        sheet.merge_range(27, 2, 27, 4, record.site_other_notes or "", value_last_fmt)

        # Borders of merged value cells: no inner lines in D/E, thick outer edge on E
        first_row, last_row = 2, 27
        grid_rows = range(22, 26)
        for row in range(first_row, last_row + 1):
            if row in grid_rows:
                continue
            if row == first_row:
                mid_fmt, end_fmt = value_mid_first_fmt, value_end_first_fmt
            elif row == last_row:
                mid_fmt, end_fmt = value_mid_last_fmt, value_end_last_fmt
            else:
                mid_fmt, end_fmt = value_mid_fmt, value_end_fmt
            sheet.write_blank(row, 3, None, mid_fmt)
            sheet.write_blank(row, 4, None, end_fmt)

        # Row height: fit wrapped text (min 30)
        texts = {
            3: record.site_address,
            4: record.site_contact_name,
            5: record.site_contact_mobile,
            8: record.access_times,
            9: record.final_furniture_plan,
            12: record.loading_dock_height_clearance,
            13: record.loading_dock_notes,
            14: record.alternate_unloading_area,
            17: record.lift_available,
            18: record.lift_dimensions,
            19: record.stairs_flights,
            20: record.permits_inductions,
            21: record.ppe_requirement,
            27: record.site_other_notes,
        }
        chars_per_line = 24 * 3 - 3
        for row in range(first_row, last_row + 1):
            text = texts.get(row) or ""
            lines = sum(max(math.ceil(len(part) / chars_per_line), 1) for part in text.split("\n"))
            sheet.set_row(row, max(30, lines * 15 + 6))

        sheet.set_portrait()
        sheet.set_paper(9)  # A4
        sheet.fit_to_pages(1, 0)
        workbook.close()

        # Download
        attachment = self.env["ir.attachment"].create({
            "name": "Burgtec Site Details - %s.xlsx" % (record.name or ""),
            "type": "binary",
            "datas": base64.b64encode(output.getvalue()),
            "res_model": self._name,
            "res_id": record.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    def action_site_details_pdf(self):
        return self.env.ref(
            "update_crm_burgtec.action_report_site_details"
        ).report_action(self)
