# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WarehouseDispatchingLine(models.Model):
    _name = 'warehouse.dispatching.line'
    _description = 'Warehouse Dispatching Line'

    warehouse_dispatching_id = fields.Many2one('warehouse.dispatching',ondelete='cascade')
    warehouse_receiving_line_id = fields.Many2one('warehouse.receiving.line', ondelete='cascade')
    supplier_id = fields.Many2one(related="warehouse_receiving_line_id.supplier_id")
    group_code = fields.Char(related="warehouse_receiving_line_id.group_code")
    product_default_code = fields.Char(related="warehouse_receiving_line_id.product_default_code")
    product_id = fields.Many2one(related="warehouse_receiving_line_id.product_id")
    picking_id = fields.Many2one(related="warehouse_receiving_line_id.picking_id")
    product_description = fields.Text(related="warehouse_receiving_line_id.product_description")
    received_qty = fields.Float(related="warehouse_receiving_line_id.received_qty")
    is_dispatched = fields.Boolean(default=False,string="Dispatched")
    is_delivered = fields.Boolean(default=False,string="Delivered")


    def set_is_dispatched(self,value):
        self.write({
            'is_dispatched':value
        })

    def set_is_delivered(self,value):
        if not self.is_dispatched:
            return False
        res = self.write({
            'is_delivered':value
        })
        return res
