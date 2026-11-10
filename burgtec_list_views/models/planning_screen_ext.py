from odoo import models, fields, api


class PlanningScreen(models.Model):
    _inherit = 'planning.screen'

    view_team = fields.Selection([
        ('default', 'Default'),
        ('prep_view', 'Preparation View'),
        ('approval_view', 'Approval View'),
    ], string='Team View', default='default')

