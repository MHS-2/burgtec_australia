import logging
from odoo import models, fields, api
_logger = logging.getLogger(__name__)


class LineItemStatus(models.Model):
    _name = 'line.item.status'
    _description = 'Line Item Status'

    status_name = fields.Char('Line Item Status')
    status_quantity = fields.Integer('Total Items')

    planning_screen_id = fields.Many2one('planning.screen', ondelete='cascade')

    crm_lead_id = fields.Many2one('crm.lead',ondelete='cascade')


