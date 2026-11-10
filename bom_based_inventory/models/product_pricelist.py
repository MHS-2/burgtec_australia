# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    pricelist_type = fields.Selection([
        ('burgtec','Burgtec'),
        ('dpg','DPG'),
    ])

    is_preferred = fields.Boolean()

    
