from odoo import models, fields, api, _

class DealTerritory(models.Model):
    _name = 'deal.location'
    _description = 'Deal Territory'

    name = fields.Char()
    hubspot_internal_name = fields.Char()
    active = fields.Boolean(default=True)