from odoo import models, fields, api, _


class SplitDOExt(models.Model):
    _inherit = 'split.do'

    freeze_sale_order = fields.Boolean(string='Freeze Sale Order', related='order_id.freeze_sale_order', store=True)