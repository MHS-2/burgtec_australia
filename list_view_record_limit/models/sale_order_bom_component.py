# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderBomComponent(models.Model):
    _inherit = 'sale.order.bom.component'

    record_limit = fields.Integer(default=40)

    min_limit = fields.Integer(default=0)
    max_limit = fields.Integer(default=100)

    is_reset = fields.Boolean()

    def set_record_limit(self,limit):
        for record in self:
            record.record_limit = limit
    
    def get_record_limit(self):
        return self.record_limit

    
    def set_reset_true(self):
        self.is_reset = True
    
    def set_reset_false(self):
        self.is_reset = False
    
    def get_is_reset_check(self):
        return self.is_reset
    
    def set_min_max_limits(self,min_limit, max_limit):
        # min is fetced from offset. It must subtract by 1.
        # max limit is now added in offset.
        offset = min_limit
        # min_limit-=1
        # max_limit = offset + max_limit
        self.write({
            'min_limit': min_limit,
            'max_limit': max_limit,
        })
    
    def get_min_max_limits(self):
        return {
            'offset': self.min_limit,
            'limit': self.max_limit,
        }
