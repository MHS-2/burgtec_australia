from odoo import api, fields, models


class PlanningScreenLine(models.Model):
    _inherit = 'planning.screen.line'

    sale_quote_planning_screen_line_id = fields.Many2one('sale.quote.planning.screen.line')