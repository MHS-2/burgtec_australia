# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DeliveryStageDeliveryCost(models.Model):
    _name = 'delivery.stage.delivery.cost'
    _description = 'Delivery Stage Delivery Cost'

    name = fields.Char('Name')

    planning_screen_id = fields.Many2one('planning.screen')

    ds_quantity = fields.Float()

    ds_installation_cost = fields.Monetary()

    ds_delivery_cost = fields.Monetary()

    company_id = fields.Many2one('res.company', store=True, copy=False,
                                string="Company",
                                default=lambda self: self.env.user.company_id.id)

    currency_id = fields.Many2one('res.currency', string="Currency",
                                 related='company_id.currency_id',)
    
    

