# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_back_order = fields.Boolean(default=False)

    back_order_qty = fields.Float()

    back_order_date_planned = fields.Datetime(string="Backorder ETA")

    back_order_comments = fields.Text()

    user_id = fields.Many2one('res.users',compute="_compute_user_id",string="Responsible")


    @api.depends('is_back_order')
    def _compute_user_id(self):
        for record in self:
            if not record.is_back_order:
                record.user_id = False
            if record.is_back_order:
                record.user_id = record.env.user.id
