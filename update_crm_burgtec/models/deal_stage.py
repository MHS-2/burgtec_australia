from odoo import models, fields, api, _


class DealStage(models.Model):
    _name = 'deal.stage'
    _description = 'Deal Stage'

    name = fields.Char(string="Stage Name")
    probability = fields.Float(string="Probability")
    active = fields.Boolean(default=True)
    deal_stage_id = fields.Char(string='Deal Stage id')
    pipeline_id = fields.Char(string='pipeline id')
    pipeline_name = fields.Char(string='Pipeline Name')
    freeze_project = fields.Boolean(string='Freeze Project', default=False)
