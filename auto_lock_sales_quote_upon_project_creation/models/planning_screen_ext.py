from odoo import fields, models

class PlanningScreenExt(models.Model):
    _inherit = 'planning.screen'

    project_name = fields.Char(related="order_id.project_name", store=True)