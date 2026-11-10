# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_xero_contact = fields.Boolean(related="partner_id.is_xero_contact", store=True)

    is_export_xero_contact = fields.Boolean(related="partner_id.is_export_contact", store=True)

