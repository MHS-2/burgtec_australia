# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    po_deposit_default_product_id = fields.Many2one(
        'product.product',
        'PO Deposit Product',
        domain="[('type', '=', 'service')]",
        config_parameter='purchase_order_down_payment.po_deposit_default_product_id',
        help='Default product used for payment advances in purchase order')
