# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    latest_back_order_date_planned = fields.Datetime(string="Latest Backorder ETA", compute="_compute_latest_back_order_date_planned")
    latest_back_order_date_planned_dashboard = fields.Datetime(string="Latest Backorder ETA Dashboard")
    purchase_comments = fields.Text()

    @api.depends('order_line.back_order_date_planned')
    def _compute_latest_back_order_date_planned(self):
        for record in self:
            order_lines = record.order_line.filtered('back_order_date_planned')
            if not order_lines:
                record.latest_back_order_date_planned = False
                record.latest_back_order_date_planned_dashboard = False
            if order_lines:
                record.latest_back_order_date_planned = max(order_lines.mapped('back_order_date_planned'))
                record.latest_back_order_date_planned_dashboard = record.latest_back_order_date_planned

    @api.depends_context('burgtec_po_reference')
    def _compute_display_name(self):
        for record in self:
            if record.env.context.get('burgtec_po_reference'):
                if record.burgtec_purchase_reference:
                    record.display_name = record.burgtec_purchase_reference
                else:
                    return super()._compute_display_name()

            else:
                return super()._compute_display_name()

