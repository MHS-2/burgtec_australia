from odoo import fields, models, api


class ResPartnerExt(models.Model):
    _inherit = "res.partner"

    is_early_procurement_supplier = fields.Boolean(string="Early Procurement Supplier", default=False)
