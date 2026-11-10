from odoo import api, fields, models, _
import requests
import logging
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class ResPartnerExt(models.Model):
    _inherit = 'res.partner'

    id_of_hubspot_company = fields.Char(string="HubSpot ID")
    hubspot_contact_url = fields.Char(string="HubSpot Contact Url")
    business_name = fields.Char()
    tax_number = fields.Char('Tax Number', compute='_compute_tax_number', store=True)

    @api.depends('vat')
    def _compute_tax_number(self):
        for rec in self:
            rec.tax_number = rec.vat or False

    def _get_first_two_words(self, name):
        """Return the first two words of a name, case-insensitive."""
        return ' '.join((name or '').lower().split()[:2])

    def _normalize_vat(self, vat):
        """Remove all whitespace from VAT."""
        return ''.join((vat or '').split())

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ResPartnerExt, self).create(vals_list)
        # Duplicate checks
        for rec in records:
            normalized_vat = self._normalize_vat(rec.vat)
            # Company duplicate check
            if normalized_vat and rec.company_type == 'company':
                existing_companies = self.search([
                    ('id', '!=', rec.id),
                    ('is_company', '=', True),
                    ('vat', '!=', False),
                ])
                existing_company = existing_companies.filtered(
                    lambda partner: self._normalize_vat(partner.vat) == normalized_vat
                )[:1]

                if existing_company:
                    raise ValidationError(_(
                        'A company with this VAT already exists: %s',
                        existing_company.display_name,
                    ))

            # Individual duplicate check
            if normalized_vat and rec.company_type == 'person':
                rec_name = self._get_first_two_words(rec.name)

                existing_individuals = self.search([
                    ('id', '!=', rec.id),
                    ('is_company', '=', False),
                    ('vat', '!=', False),
                ])

                for partner in existing_individuals:
                    # Same VAT after removing all whitespace
                    if self._normalize_vat(partner.vat) != normalized_vat:
                        continue

                    # Same first two words of name
                    same_name = (
                            self._get_first_two_words(partner.name) == rec_name
                    )

                    # Both individuals belong to the same parent company
                    same_company = (
                            partner.parent_id
                            and rec.parent_id
                            and partner.parent_id == rec.parent_id
                    )

                    # Same VAT + same name = duplicate
                    if same_name:
                        raise ValidationError(_(
                            'A contact with this VAT already exists: %s',
                            partner.display_name,
                        ))

                    # Same VAT + different name + different company = duplicate
                    if not same_name and not same_company:
                        raise ValidationError(_(
                            'A contact with this VAT already exists under another company: %s',
                            partner.display_name,
                        ))

        # Export only after duplicate checks pass
        # for record in records.filtered('is_company'):
        #     record.export_company_to_hubspot()
        #     record.action_export_contact()
        return records

    def action_open_hubspot_contact(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.hubspot_contact_url,
            'target': 'new',
        }

    def _get_hubspot_config(self):
        """Retrieve HubSpot configuration from system parameters."""
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('burgtec_hubspot_customization.hubspot_integrations_token')
        base_url = params.get_param('burgtec_hubspot_customization.hubspot_base_url')
        return base_url, token

    def export_company_to_hubspot(self):
        """Check if HubSpot company exists. If not, create it."""
        params = self.env['ir.config_parameter'].sudo()
        web_url = params.get_param('web.base.url')
        base_url, hubspot_token = self._get_hubspot_config()
        if not hubspot_token:
            _logger.error("HubSpot API token not configured")
            return False

        headers = {"Authorization": f"Bearer {hubspot_token}", "Content-Type": "application/json"}

        # SEARCH HUBSPOT BY WEBSITE URL
        if self.website:
            search_url = f"{base_url}/crm/v3/objects/companies/search"
            search_payload = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "website",
                                "operator": "EQ",
                                "value": self.website,
                            }
                        ]
                    },
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
                    contact_url = results[0].get("url")
                    if existing_company_id:
                        self.sudo().id_of_hubspot_company = existing_company_id
                        self.sudo().hubspot_contact_url = contact_url
                        return existing_company_id

            # CREATE NEW COMPANY IN HUBSPOT
            create_url = f"{base_url}/crm/v3/objects/companies"
            payload = {
                "properties": {
                    "name": self.name,
                    "address": self.street or "",
                    "city": self.city or "",
                    "state": self.state_id.name if self.state_id else "",
                    "country": self.country_id.name if self.country_id else "",
                    "phone": self.phone or "",
                    "website": self.website or "",
                    "odoo_contact_url": f'{web_url}/odoo/contacts/{self.id}'
                }
            }
            create_response = requests.post(create_url, headers=headers, json=payload)
            if create_response.status_code == 201:
                new_company_id = create_response.json().get("id")
                self.sudo().id_of_hubspot_company = new_company_id
                self.sudo().hubspot_contact_url = create_response.json().get("url")
                return new_company_id

            raise Exception(f"Failed to create company in HubSpot: {create_response.text}")

        raise Exception(f"Cannot sync company to HubSpot: self '{self.id}' has no name.")

        # ________________________________________Contact Export To HubSpot Using Button___________________________________________

    def export_contact_to_hubspot(self):
        """Check if HubSpot contact exists. If not, create it."""
        params = self.env['ir.config_parameter'].sudo()
        web_url = params.get_param('web.base.url')
        base_url, hubspot_token = self._get_hubspot_config()
        if not hubspot_token:
            _logger.error("HubSpot API token not configured")
            return False

        headers = {
            "Authorization": f"Bearer {hubspot_token}",
            "Content-Type": "application/json",
        }

        # SEARCH HUBSPOT BY EMAIL
        if self.email:
            search_url = f"{base_url}/crm/v3/objects/contacts/search"

            search_payload = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": self.email,
                            }
                        ]
                    },
                ],
                "properties": ["firstname", "lastname", "email"],
                "limit": 1,
            }

            search_response = requests.post(
                search_url,
                headers=headers,
                json=search_payload,
            )

            if search_response.status_code == 200:
                results = search_response.json().get("results", [])
                if results:
                    existing_contact_id = results[0].get("id")
                    contact_url = results[0].get("url")

                    if existing_contact_id:
                        self.sudo().id_of_hubspot_company = existing_contact_id
                        self.sudo().hubspot_contact_url = contact_url

                        # Associate with Company
                        if self.parent_id and self.parent_id.id_of_hubspot_company:
                            associate_url = (
                                f"{base_url}/crm/v4/objects/contacts/"
                                f"{existing_contact_id}/associations/default/"
                                f"companies/{self.parent_id.id_of_hubspot_company}"
                            )

                            requests.put(associate_url, headers=headers)

                        return existing_contact_id

            # CREATE NEW CONTACT
            create_url = f"{base_url}/crm/v3/objects/contacts"

            payload = {
                "properties": {
                    "firstname": self.name or "",
                    "lastname": "",
                    "email": self.email or "",
                    "phone": self.phone or "",
                    "mobilephone": self.mobile or "",
                    "odoo_contact_ur": f'{web_url}/odoo/contacts/{self.id}'

                }
            }

            create_response = requests.post(
                create_url,
                headers=headers,
                json=payload,
            )

            if create_response.status_code == 201:
                new_contact_id = create_response.json().get("id")
                self.sudo().id_of_hubspot_company = new_contact_id
                self.sudo().hubspot_contact_url = create_response.json().get("url")

                # Associate with Company
                if self.parent_id and self.parent_id.id_of_hubspot_company:
                    associate_url = (
                        f"{base_url}/crm/v4/objects/contacts/"
                        f"{new_contact_id}/associations/default/"
                        f"companies/{self.parent_id.id_of_hubspot_company}"
                    )

                    requests.put(associate_url, headers=headers)

                return new_contact_id

            raise Exception(f"Failed to create contact in HubSpot: {create_response.text}")

        raise Exception(
            f"Cannot sync contact to HubSpot: Partner '{self.id}' has no name or email."
        )

    # Server Action to Export the Existing Comapny/Contact to HubSpot in Bulk

    def _export_existing_companies_to_hubspot(self):
        base_url, hubspot_token = self._get_hubspot_config()
        if not hubspot_token:
            _logger.error("HubSpot API token not configured")
            return False
        headers = {"Authorization": f"Bearer {hubspot_token}", "Content-Type": "application/json"}
        for contact in self:
            if not contact.id_of_hubspot_company:
                if contact.is_company:
                    if not contact.website:
                        raise ValidationError(_("Website is not set for company %s", contact.name))
                    search_url = f"{base_url}/crm/v3/objects/companies/search"
                    search_payload = {
                        "filterGroups": [
                            {
                                "filters": [
                                    {
                                        "propertyName": "website",
                                        "operator": "EQ",
                                        "value": contact.website,
                                    }
                                ]
                            },
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
                                contact.sudo().id_of_hubspot_company = existing_company_id
                                continue

                                # CREATE NEW COMPANY IN HUBSPOT
                    create_url = f"{base_url}/crm/v3/objects/companies"
                    payload = {
                        "properties": {
                            "name": contact.name,
                            "address": contact.street or "",
                            "city": contact.city or "",
                            "state": contact.state_id.name if contact.state_id else "",
                            "country": contact.country_id.name if contact.country_id else "",
                            "phone": contact.phone or "",
                            "website": contact.website or "",
                        }
                    }
                    create_response = requests.post(create_url, headers=headers, json=payload)
                    if create_response.status_code == 201:
                        new_company_id = create_response.json().get("id")
                        contact.sudo().id_of_hubspot_company = new_company_id
                        continue

    def _export_existing_contact_to_hubspot(self):
        base_url, hubspot_token = self._get_hubspot_config()
        if not hubspot_token:
            _logger.error("HubSpot API token not configured")
            return False
        headers = {"Authorization": f"Bearer {hubspot_token}", "Content-Type": "application/json"}
        for contact in self:
            if not contact.id_of_hubspot_company:
                if not contact.is_company:
                    if not contact.parent_id:
                        raise ValidationError(_("Parent Company is not set for contact %s", contact.name))
                    if not contact.parent_id.id_of_hubspot_company:
                        raise ValidationError(
                            _("First Export the Parent Company %s of the Contact %s To HubSpot", contact.parent_id.name,
                              contact.name))
                    if not contact.email:
                        raise ValidationError(_("Email is not set for contact %s", contact.name))
                    #     # SEARCH HUBSPOT BY EMAIL
                    search_url = f"{base_url}/crm/v3/objects/contacts/search"
                    search_payload = {
                        "filterGroups": [
                            {
                                "filters": [
                                    {
                                        "propertyName": "email",
                                        "operator": "EQ",
                                        "value": contact.email,
                                    }
                                ]
                            },
                        ],
                        "properties": ["firstname", "lastname", "email"],
                        "limit": 1,
                    }
                    search_response = requests.post(
                        search_url,
                        headers=headers,
                        json=search_payload,
                    )
                    if search_response.status_code == 200:
                        results = search_response.json().get("results", [])
                        if results:
                            existing_contact_id = results[0].get("id")
                            if existing_contact_id:
                                contact.sudo().id_of_hubspot_company = existing_contact_id
                                # Associate with Company
                                if contact.parent_id and contact.parent_id.id_of_hubspot_company:
                                    associate_url = (
                                        f"{base_url}/crm/v4/objects/contacts/"
                                        f"{existing_contact_id}/associations/default/"
                                        f"companies/{contact.parent_id.id_of_hubspot_company}"
                                    )

                                    requests.put(associate_url, headers=headers)
                                    continue
                    # CREATE NEW CONTACT
                    create_url = f"{base_url}/crm/v3/objects/contacts"
                    payload = {
                        "properties": {
                            "firstname": contact.name or "",
                            "lastname": "",
                            "email": contact.email or "",
                            "phone": contact.phone or "",
                            "mobilephone": contact.mobile or "",
                        }
                    }

                    create_response = requests.post(
                        create_url,
                        headers=headers,
                        json=payload,
                    )
                    if create_response.status_code == 201:
                        new_contact_id = create_response.json().get("id")
                        contact.sudo().id_of_hubspot_company = new_contact_id
                        # Associate with Company
                        if contact.parent_id and contact.parent_id.id_of_hubspot_company:
                            associate_url = (
                                f"{base_url}/crm/v4/objects/contacts/"
                                f"{new_contact_id}/associations/default/"
                                f"companies/{contact.parent_id.id_of_hubspot_company}"
                            )

                            requests.put(associate_url, headers=headers)
                            continue
