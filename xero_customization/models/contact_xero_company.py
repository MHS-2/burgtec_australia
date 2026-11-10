# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ContactXeroCompany(models.Model):
    _inherit = 'contact.xero.company'

    def _compute_display_name(self):
        if self.env.context.get("xero_contact_id"):
            for contact in self:
                contact.display_name = f"{contact.partner_id.name} - {contact.xero_contact_id}"
        else:
            super()._compute_display_name()
