from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    onedrive_tenant_id = fields.Char(
        string='Tenant ID',
        config_parameter='crm_onedrive_integration.tenant_id',
    )
    onedrive_client_id = fields.Char(
        string='Client ID',
        config_parameter='crm_onedrive_integration.client_id',
    )
    onedrive_client_secret = fields.Char(
        string='Client Secret',
        config_parameter='crm_onedrive_integration.client_secret',
    )
    onedrive_sharepoint_site_url = fields.Char(
        string='SharePoint Site URL',
        config_parameter='crm_onedrive_integration.sharepoint_site_url',
        help='Full URL of the SharePoint site where lead folders will be created.\n'
             'Example: https://burgtecfurniture.sharepoint.com/sites/OdooTest',
    )
    onedrive_root_folder = fields.Char(
        string='Root Folder Name',
        config_parameter='crm_onedrive_integration.root_folder',
        default='CRM Leads',
        help='Optional sub-folder inside the SharePoint document library where '
             'lead folders are created. Leave empty to create them at the library root.',
    )
