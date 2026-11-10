from odoo import fields, models

import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class LineItemStatusExt(models.Model):
    _inherit = 'line.item.status'

    sale_quote_planning_screen_id = fields.Many2one('sale.quote.planning.screen', ondelete='cascade')

    crm_lead_id = fields.Many2one('crm.lead', compute='compute_crm_lead_id', store=True)

    @api.depends('sale_quote_planning_screen_id', 'planning_screen_id')
    def compute_crm_lead_id(self):
        for line in self:
            sale_quote_planning_screen_id = line.sale_quote_planning_screen_id
            planning_screen_id = line.planning_screen_id
            order = False
            if sale_quote_planning_screen_id and not planning_screen_id:
                order = sale_quote_planning_screen_id.order_id
                if order:
                    if order.is_frozen_due_to_project_creation:
                        crm_lead_id = False
                    else:
                        crm_lead_id = order.opportunity_id.id
                if not crm_lead_id:
                    line.crm_lead_id = False
                if crm_lead_id:
                    line.crm_lead_id = crm_lead_id
            elif planning_screen_id:
                crm_lead_id = planning_screen_id.order_id.opportunity_id.id
                if not crm_lead_id:
                    line.crm_lead_id = False
                if crm_lead_id:
                    line.crm_lead_id = crm_lead_id
