from odoo import models, fields, api, _

class DealType(models.Model):
    _name='deal.type'
    _description = 'Deal Type'

    name = fields.Char(string="Name")
    active = fields.Boolean(default=True)
    hubspot_value = fields.Char('Hubspot Value')