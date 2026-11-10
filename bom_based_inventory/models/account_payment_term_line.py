# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountPaymentTermLine(models.Model):
    _inherit = 'account.payment.term.line'

    delay_type = fields.Selection(selection_add=[
        ('of_the_following_month', 'of the following month'),
        ('days_after_the_bill_date', 'day(s) after the bill date'),
        ('days_after_the_bill_month', 'day(s) after the bill month'),
        ('of_the_current_month', 'of the current month'),
    ], ondelete={'of_the_following_month': 'set default', 'days_after_the_bill_date': 'set default', 'days_after_the_bill_month': 'set default', 'of_the_current_month': 'set default'})
