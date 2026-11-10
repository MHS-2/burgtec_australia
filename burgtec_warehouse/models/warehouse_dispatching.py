# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WarehouseDispatching(models.Model):
    _name = 'warehouse.dispatching'
    _description = 'Warehouse Dispatching for warehouse receiving'

    name = fields.Char('Reference', copy=False)
    warehouse_receiving_id = fields.Many2one('warehouse.receiving',ondelete='cascade')
    warehouse_dispatching_line_ids = fields.One2many('warehouse.dispatching.line','warehouse_dispatching_id')


    @api.model_create_multi
    def create(self, vals_list):
        """ Create a sequence for the student model """
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = (self.env['ir.sequence'].
                next_by_code('burgtec.dispatching'))
        return super().create(vals_list)
    

    def action_view_receiving(self):
        return {
            'name': _('Warehouse Receiving'),
            'type': 'ir.actions.act_window',
            'res_model': 'warehouse.receiving',
            'view_mode': 'form',
            'res_id': self.warehouse_receiving_id.id,
        }
