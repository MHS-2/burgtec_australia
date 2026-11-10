from odoo import _, api, fields, models
import logging
import requests
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

HUBSPOT_OWNERS_PAGE_SIZE = 100
HUBSPOT_REQUEST_TIMEOUT = 30
HUBSPOT_PORTAL_ID = '5690985'


class ResUserExt(models.Model):
    _inherit = 'res.users'

    hubspot_user_id = fields.Char(
        string="HubSpot User ID",
        copy=False
    )
    hubspot_user_url = fields.Char('HubSpot User URL')
    hubspot_owner_id = fields.Char('HubSpot owner ID')

    def _get_hubspot_config(self):
        """Same keys as burgtec_hubspot_customization."""
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('burgtec_hubspot_customization.hubspot_integrations_token')
        base_url = params.get_param('burgtec_hubspot_customization.hubspot_base_url') or 'https://api.hubapi.com'
        return base_url.rstrip('/'), token

    def _fetch_active_hubspot_owners(self):
        """Return a list of every *active* HubSpot owner (handles pagination)."""
        base_url, hubspot_token = self._get_hubspot_config()
        if not hubspot_token:
            _logger.error("HubSpot API token not configured")
            raise UserError(_("HubSpot API token not configured!"))

        headers = {
            'Authorization': f'Bearer {hubspot_token}',
            'Content-Type': 'application/json',
        }

        owners = []
        after = None
        url = f"{base_url}/crm/v3/owners/"

        while True:
            params = {'limit': HUBSPOT_OWNERS_PAGE_SIZE, 'archived': 'false'}
            if after:
                params['after'] = after
            try:
                response = requests.get(url, headers=headers, params=params, timeout=HUBSPOT_REQUEST_TIMEOUT)
            except requests.RequestException as exc:
                _logger.exception("HubSpot owners request failed: %s", exc)
                raise UserError(_("Could not reach HubSpot: %s") % exc)

            if response.status_code != 200:
                _logger.error("HubSpot owners HTTP %s: %s", response.status_code, response.text)
                raise UserError(_(
                    "HubSpot returned HTTP %(status)s.\n%(body)s",
                    status=response.status_code,
                    body=response.text[:500],
                ))

            payload = response.json()
            owners.extend(payload.get('results', []))
            after = payload.get('paging', {}).get('next', {}).get('after')
            if not after:
                break

        _logger.info("HubSpot: fetched %d active owners", len(owners))
        return owners

    def _sync_hubspot_user_ids(self):
        owners = self._fetch_active_hubspot_owners()
        email_to_hs_id = {}
        for owner in owners:
            email = (owner.get('email') or '').strip().lower()
            hubspot_user_id = owner.get('userId')
            hubspot_owner_id = owner.get('id')  # ← store per owner in dict
            if email and hubspot_user_id:
                email_to_hs_id[email] = {
                    'user_id': str(hubspot_user_id),
                    'owner_id': str(hubspot_owner_id) if hubspot_owner_id else '',
                }

        users = self.env['res.users'].sudo().search([])
        matched = 0
        unchanged = 0
        unmatched_logins = []

        for user in users:
            login = (user.login or '').strip().lower()
            partner_email = (user.email or '').strip().lower()
            owner_data = email_to_hs_id.get(login) or email_to_hs_id.get(partner_email)

            if owner_data:
                hs_id = owner_data['user_id']
                hs_owner_id = owner_data['owner_id']
                if user.hubspot_user_id != hs_id or not user.hubspot_user_url or not user.hubspot_owner_id:
                    user.hubspot_user_id = hs_id
                    user.hubspot_owner_id = hs_owner_id
                    user.hubspot_user_url = (
                        f"https://app.hubspot.com/settings/{HUBSPOT_PORTAL_ID}"
                        f"/users/user/{hs_id}?tab=overviewTab"
                    )
                    matched += 1
                else:
                    unchanged += 1
            else:
                unmatched_logins.append(user.login)

        _logger.info(
            "HubSpot user sync — fetched: %d, updated: %d, already correct: %d, no match: %d",
            len(owners), matched, unchanged, len(unmatched_logins),
        )
        return {
            'fetched': len(owners),
            'matched': matched,
            'unchanged': unchanged,
            'unmatched_users': unmatched_logins,
        }

    def _cron_sync_hubspot_user_ids(self):
        """Cron entry point."""
        self._sync_hubspot_user_ids()

    def action_sync_hubspot_user_ids(self):
        """Button handler ? syncs and shows a notification."""
        result = self._sync_hubspot_user_ids()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('HubSpot User Sync'),
                'message': _(
                    "Fetched: %(fetched)s active HubSpot owners.\n"
                    "Updated: %(matched)s\n"
                    "Already correct: %(unchanged)s\n"
                    "No HubSpot match: %(missing)s",
                    fetched=result['fetched'],
                    matched=result['matched'],
                    unchanged=result['unchanged'],
                    missing=len(result['unmatched_users']),
                ),
                'type': 'success',
                'sticky': True,
            },
        }
