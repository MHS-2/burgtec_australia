from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    burgtec_warehouse_url = fields.Char(
        string="Wh Instance Url", config_parameter="burgtec_warehouse_integration.burgtec_warehouse_url"
    )
    burgtec_warehouse_db = fields.Char(
        string="Wh Instance Db", config_parameter="burgtec_warehouse_integration.burgtec_warehouse_db"
    )
    burgtec_warehouse_api_key = fields.Char(
        string="Wh Instance Key", config_parameter="burgtec_warehouse_integration.burgtec_warehouse_api_key"
    )

    burgtec_webhook_authentication_token = fields.Char(
        string="Webhook Authentication Token", config_parameter="burgtec_warehouse_integration.burgtec_webhook_authentication_token")