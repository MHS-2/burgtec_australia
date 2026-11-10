# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WarehouseReceivingLine(models.Model):
    _name = 'warehouse.receiving.line'
    _description = 'Warehouse Receiving Line'

    name = fields.Char('Name')
    warehouse_receiving_id = fields.Many2one('warehouse.receiving', ondelete='cascade')
    purchase_id = fields.Many2one('purchase.order', ondelete='cascade')
    purchase_order_line_id = fields.Many2one('purchase.order.line', ondelete='cascade')
    supplier_id = fields.Many2one('res.partner')
    group_code = fields.Char()
    product_default_code = fields.Char(string="Product Code")
    product_id = fields.Many2one('product.product')
    picking_id = fields.Many2one('stock.picking')
    product_description = fields.Text()
    product_qty = fields.Float()
    received_qty = fields.Float()
    back_order_qty = fields.Float(compute="_compute_back_order_qty", store=True)
    is_received = fields.Boolean(default=False,string="Received")
    is_staged = fields.Boolean(default=False,string="Staged")
    is_dispatched = fields.Boolean(default=False,string="Dispatched")
    is_delivered = fields.Boolean(default=False,string="Delivered")
    is_backorder_created = fields.Boolean(default=False, string="Back Order Created")
    
    def set_is_received(self,value):
        self.write({
            'is_received':value
        })
        
    
    def set_is_staged(self,value):
        self.write({
            'is_staged':value
        })
    
    def set_is_dispatched(self,value):
        self.write({
            'is_dispatched':value
        })

    def set_is_delivered(self,value):
        self.write({
            'is_delivered':value
        })
    
    def set_received_qty(self,value):
        self.write({
            'received_qty': value
        })
    
    @api.depends('product_qty','received_qty')
    def _compute_back_order_qty(self):
        for record in self:
            if record.received_qty > 0.0:
                record.back_order_qty = (record.product_qty - record.received_qty)
            else:
                record.back_order_qty = 0.0
            

