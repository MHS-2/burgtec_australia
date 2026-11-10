# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from pytz import timezone, UTC
_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    last_po_weekly_update_date_to_date = fields.Date(compute="compute_last_po_weekly_update_date_to_date")
    date_planned_to_date = fields.Date(compute="compute_date_planned_to_date")
    hubspot_dispatch_date_to_date = fields.Date(compute="compute_hubspot_dispatched_date_to_date")

    is_po_not_going_to_bv = fields.Boolean(string="PO Not Going To BV")
    bo_number = fields.Char(string="BO#")
    bo_notes = fields.Char(string="BO Notes")
    bo_dispatch_date = fields.Date(string="BO Dispatch Date")

    @api.depends('last_po_weekly_update_date')
    def compute_last_po_weekly_update_date_to_date(self):
        for record in self:
            if record.last_po_weekly_update_date:
                user_tz = timezone(self.env.user.tz or 'UTC')
                local_dt = UTC.localize(record.last_po_weekly_update_date).astimezone(user_tz)
                record.last_po_weekly_update_date_to_date = local_dt.date()
            else:
                record.last_po_weekly_update_date_to_date = False
    
    @api.depends('date_planned')
    def compute_date_planned_to_date(self):
        for record in self:
            if record.date_planned:
                user_tz = timezone(self.env.user.tz or 'UTC')
                local_dt = UTC.localize(record.date_planned).astimezone(user_tz)
                record.date_planned_to_date = local_dt.date()
            else:
                record.date_planned_to_date = False
    
    @api.depends('hubspot_dispatch_date')    
    def compute_hubspot_dispatched_date_to_date(self):
        for record in self:
            if record.hubspot_dispatch_date:
                user_tz = timezone(self.env.user.tz or 'UTC')
                local_dt = UTC.localize(record.hubspot_dispatch_date).astimezone(user_tz)
                record.hubspot_dispatch_date_to_date = local_dt.date()
            else:
                record.hubspot_dispatch_date_to_date = False


                


