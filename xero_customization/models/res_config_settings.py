# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    xero_webhook_key = fields.Char(
        string="Xero Webhook Key",
        config_parameter='xero_customization.xero_webhook_key'
    )
