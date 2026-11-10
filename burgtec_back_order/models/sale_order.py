# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends_context('burgtec_ds_reference')
    def _compute_display_name(self):
        for record in self:
            if record.env.context.get('burgtec_ds_reference'):
                if record.burgtec_quote_reference:
                    record.display_name = record.burgtec_quote_reference
                else:
                    return super()._compute_display_name()

            else:
                return super()._compute_display_name()
