from odoo import models,fields,api,_,Command

class ZonePostal(models.Model):
    _name = 'zone.postal'
    _description = 'Zone Postal Model For Website API'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'name'

    name= fields.Char()

    # ZONE 1
    delivery_cost_zone_1 = fields.Float(string="Zone 1 Delivery Cost",tracking=True)
    installation_cost_zone_1 = fields.Float(string="Zone 1 Installation Cost",tracking=True)

    # ZONE 2
    delivery_cost_zone_2 = fields.Float(string="Zone 2 Delivery Cost",tracking=True)
    installation_cost_zone_2 = fields.Float(string="Zone 2 Installation Cost",tracking=True)

    # ZONE 3
    delivery_cost_zone_3 = fields.Float(string="Zone 3 Delivery Cost",tracking=True)
    installation_cost_zone_3 = fields.Float(string="Zone 3 Installation Cost",tracking=True)

    #Each zone can have multiple postal codes.

    zone1_postal_code_ids = fields.Many2many(
        'zone.postal.code',
        'zone1_postal_code_rel',
        'zone1_postal_id',
        'zone1_postal_code_id',
        string="Zone 1 Postal Codes"
    )

    zone2_postal_code_ids = fields.Many2many(
        'zone.postal.code',
        'zone2_postal_code_rel',
        'zone2_postal_id',
        'zone2_postal_code_id',
        string="Zone 2 Postal Codes"
    )

    zone3_postal_code_ids = fields.Many2many(
        'zone.postal.code',
        'zone3_postal_code_rel',
        'zone3_postal_id',
        'zone3_postal_code_id',
        string="Zone 3 Postal Codes"
    )




class ZonePostalCode(models.Model):
    _name ='zone.postal.code'
    _description = 'Zone Postal Can have multiple postal codes'
    _rec_name = "name"

    name = fields.Char(string='Postal Code')