from odoo import api, fields, models, tools

class ResPartnerExt(models.Model):
    _inherit = "res.partner"


    short_name = fields.Char(string="Short Name")