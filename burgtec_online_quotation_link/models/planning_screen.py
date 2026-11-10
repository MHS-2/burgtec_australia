from odoo import models, fields, api


class SaleQuotePlanningScreenLineExt(models.Model):
    _inherit = "sale.quote.planning.screen.line"

    public_comment = fields.Char(related="order_line_id.public_comment", store=True)
    user_feedback = fields.Selection(related="order_line_id.user_feedback", store=True)
    customer_finish_preference = fields.Char(related="order_line_id.customer_finish_preference", store=True)


class PlanningScreenLineExt(models.Model):
    _inherit = 'planning.screen.line'

    public_comment = fields.Char(related="order_line_id.public_comment", store=True)
    user_feedback = fields.Selection(related="order_line_id.user_feedback", store=True)
    customer_finish_preference = fields.Char(related="order_line_id.customer_finish_preference", store=True)

