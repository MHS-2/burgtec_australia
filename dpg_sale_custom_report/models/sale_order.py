# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    custom_po_no = fields.Char(string="Custom PO No #")
    customer_address = fields.Char(string="Customer Address")


    @api.onchange('partner_id')
    def onchange_partner_id(self):
        for rec in self:
            if rec.partner_id:
                rec.customer_address = rec.partner_id.contact_address_complete
