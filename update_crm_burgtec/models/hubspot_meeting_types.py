from odoo import fields, api, models


class HubspotMeetingTypes(models.Model):
    _name = 'hubspot.meeting.types'
    _description = 'Hubspot Meeting Types'

    name = fields.Char('Meeting Type')
    hubspot_internal_name = fields.Char()
