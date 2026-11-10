from odoo import models, fields, api, _

class DealPipelineStage(models.Model):
    _name = "deal.pipeline.stage"
    _description = "Deal Pipeline Stage"

    active = fields.Boolean(default=True)
    name = fields.Char()
    hubspot_internal_name = fields.Char()
