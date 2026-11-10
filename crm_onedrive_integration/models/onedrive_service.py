import json
import logging
import re
from urllib.parse import urlparse
from markupsafe import Markup
import requests
from odoo import _, models, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

GRAPH_BASE = 'https://graph.microsoft.com/v1.0'
TOKEN_URL = 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'
DEFAULT_TIMEOUT = 20


class OneDriveService(models.AbstractModel):
    _name = 'onedrive.service'
    _description = 'OneDrive / SharePoint Integration Service'

    def _get_settings(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'tenant_id': (ICP.get_param('crm_onedrive_integration.tenant_id') or '').strip(),
            'client_id': (ICP.get_param('crm_onedrive_integration.client_id') or '').strip(),
            'client_secret': (ICP.get_param('crm_onedrive_integration.client_secret') or '').strip(),
            'sharepoint_site_url': (ICP.get_param('crm_onedrive_integration.sharepoint_site_url') or '').strip(),
            'root_folder': (ICP.get_param('crm_onedrive_integration.root_folder') or '').strip(),
        }

    def _get_access_token(self):
        settings = self._get_settings()
        missing = [k for k in ('tenant_id', 'client_id', 'client_secret') if not settings[k]]
        if missing:
            raise UserError(_(
                'OneDrive/SharePoint integration is not fully configured. Missing: %s.\n'
                'Please complete the setup in Settings.'
            ) % ', '.join(missing))
        url = TOKEN_URL.format(tenant=settings['tenant_id'])
        data = {
            'client_id': settings['client_id'],
            'client_secret': settings['client_secret'],
            'scope': 'https://graph.microsoft.com/.default',
            'grant_type': 'client_credentials',
        }
        try:
            resp = requests.post(url, data=data, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            _logger.exception('Token request failed')
            raise UserError(_('Failed to authenticate with Microsoft Graph: %s') % e)
        token = resp.json().get('access_token')
        if not token:
            raise UserError(_('Microsoft Graph did not return an access token.'))
        return token

    # ------------------------------------------------------------------
    # SharePoint helpers
    # ------------------------------------------------------------------

    def _get_site_id(self, token, site_url):
        """Resolve a SharePoint site URL to its Graph site ID.

        Accepts full URLs such as:
            https://burgtecfurniture.sharepoint.com/sites/OdooTest
        """
        parsed = urlparse(site_url)
        hostname = parsed.hostname
        path = parsed.path.rstrip('/')
        if not hostname or not path:
            raise UserError(_(
                'Invalid SharePoint Site URL: %s\n'
                'Expected: https://<tenant>.sharepoint.com/sites/<site-name>'
            ) % site_url)
        url = '%s/sites/%s:%s' % (GRAPH_BASE, hostname, path)
        headers = {'Authorization': 'Bearer %s' % token}
        try:
            resp = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        except requests.RequestException as e:
            raise UserError(_('Failed to resolve SharePoint site: %s') % e)
        if resp.status_code != 200:
            _logger.error('SharePoint site lookup failed: %s %s', resp.status_code, resp.text)
            raise UserError(_(
                'Could not find SharePoint site at %s.\n'
                'HTTP %s: %s\n\n'
                'Make sure the Azure app has the Sites.ReadWrite.All '
                'application permission granted in Azure AD.'
            ) % (site_url, resp.status_code, resp.text))
        return resp.json().get('id')

    def _ensure_root_folder_in_site(self, token, site_id, root_folder):
        """Return the item-ID of root_folder inside the site drive.

        Creates the folder if it does not exist. Returns None when root_folder
        is empty (lead folders go directly to the document library root).
        """
        if not root_folder:
            return None
        headers = {'Authorization': 'Bearer %s' % token}
        url = '%s/sites/%s/drive/root:/%s' % (GRAPH_BASE, site_id, root_folder)
        try:
            resp = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        except requests.RequestException as e:
            raise UserError(_('Failed to query SharePoint root folder: %s') % e)
        if resp.status_code == 200:
            return resp.json().get('id')
        if resp.status_code == 404:
            return self._create_folder_in_site(token, site_id, None, root_folder).get('id')
        _logger.error('SharePoint root folder lookup: %s %s', resp.status_code, resp.text)
        raise UserError(_('Failed to access SharePoint root folder: %s') % resp.text)

    def _create_folder_in_site(self, token, site_id, parent_id, name):
        """Create a folder inside the SharePoint site's document library.

        parent_id=None  -> creates under drive root.
        """
        headers = {
            'Authorization': 'Bearer %s' % token,
            'Content-Type': 'application/json',
        }
        if parent_id:
            url = '%s/sites/%s/drive/items/%s/children' % (GRAPH_BASE, site_id, parent_id)
        else:
            url = '%s/sites/%s/drive/root/children' % (GRAPH_BASE, site_id)
        payload = {
            'name': name,
            'folder': {},
            '@microsoft.graph.conflictBehavior': 'rename',
        }
        try:
            resp = requests.post(
                url, headers=headers, data=json.dumps(payload), timeout=DEFAULT_TIMEOUT
            )
        except requests.RequestException as e:
            raise UserError(_('Failed to call Microsoft Graph: %s') % e)
        if resp.status_code not in (200, 201):
            _logger.error('SharePoint folder create failed: %s %s', resp.status_code, resp.text)
            raise UserError(_('Failed to create SharePoint folder: %s') % resp.text)
        return resp.json()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_lead_folder(self, crm_lead):
        """Create a SharePoint folder named after the lead.

        Returns a dict with id, name and web_url.
        """
        settings = self._get_settings()
        if not settings['sharepoint_site_url']:
            raise UserError(_(
                'SharePoint Site URL is not configured.\n'
                'Go to Settings -> CRM -> OneDrive / SharePoint Integration '
                'and enter the Site URL.'
            ))
        token = self._get_access_token()
        crm_lead_reference = crm_lead.odoo_deal_number_6digit
        site_id = self._get_site_id(token, settings['sharepoint_site_url'])
        parent_id = self._ensure_root_folder_in_site(token, site_id, settings['root_folder'])
        result = self._create_folder_in_site(token, site_id, parent_id, crm_lead_reference)
        share_url = self._create_share_link(token, site_id, result.get('id'))
        crm_lead.write({
            'onedrive_folder_id': result.get('id'),
            'onedrive_folder_url': share_url or result.get('webUrl'),
            'onedrive_folder_name': result.get('name'),
        })
        message_body = Markup(f"""
        <div style="padding: 10px;">
        <h4 style="margin: 0 0 10px 0; font-weight: bold;">
                <span style="font-size:18px; color:#00A4EF;">🗁</span>
                <span style="color:#F25022;">O</span><span style="color:#7FBA00;">n</span><span style="color:#00A4EF;">e</span><span style="color:#FFB900;">D</span><span style="color:#F25022;">r</span><span style="color:#7FBA00;">i</span><span style="color:#00A4EF;">v</span><span style="color:#FFB900;">e</span>
                Folder Created Successfully — {result.get('name')}</h4></div>
        """)
        crm_lead.message_post(
            body=message_body,
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )

    def _create_share_link(self, token, site_id, item_id):
        """Create an org-scoped 'view' sharing link for a folder.

        Uses a random token instead of the folder path, so the link
        KEEPS WORKING even after the folder is renamed. Idempotent:
        calling again with same type+scope returns the existing link.
        """
        url = '%s/sites/%s/drive/items/%s/createLink' % (GRAPH_BASE, site_id, item_id)
        headers = {
            'Authorization': 'Bearer %s' % token,
            'Content-Type': 'application/json',
        }
        payload = {'type': 'view', 'scope': 'organization'}
        try:
            resp = requests.post(
                url, headers=headers, data=json.dumps(payload), timeout=DEFAULT_TIMEOUT
            )
        except requests.RequestException as e:
            _logger.warning('OneDrive createLink failed: %s', e)
            return None
        if resp.status_code not in (200, 201):
            _logger.warning('OneDrive createLink failed: %s %s', resp.status_code, resp.text)
            return None
        return resp.json().get('link', {}).get('webUrl')
