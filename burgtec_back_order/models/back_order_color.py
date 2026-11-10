# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BackOrderColor(models.Model):
    _name = 'back.order.color'
    _description = 'BackOrderColor'

    name = fields.Char('Name')
    color = fields.Char()
    back_order_count = fields.Integer()

    @api.constrains('back_order_count')
    def check_back_order_count(self):
        count = 0
        for record in self:
            if record.back_order_count < 1:
                raise UserError(_('Back Order Count must be a positive integer.'))
            count = record.search_count([('back_order_count','=',record.back_order_count)])
            if count > 1:
                raise UserError(_('Record for the back order count => %s <= already exists.',record.back_order_count))
    
    def set_color(self,record_color):
        self.sudo().write({
            'color':record_color
        })
    
    def get_color(self):
        return self.color
    


