from odoo import fields, models, api, _

class SaleOrderSeriesExt(models.Model):
    _inherit = 'sale.order.series'
    _rec_name = 'display_name'

    name = fields.Char()

    @api.depends('sequence', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.sequence} - {record.name or ''}"
