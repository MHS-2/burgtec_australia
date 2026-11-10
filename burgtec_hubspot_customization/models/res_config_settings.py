from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hubspot_integrations_token = fields.Char(
        'HubSpot Integration Token',
        config_parameter='burgtec_hubspot_customization.hubspot_integrations_token'
    )
    hubspot_base_url = fields.Char(
        'HubSpot Base URL',
        config_parameter='burgtec_hubspot_customization.hubspot_base_url'
    )
