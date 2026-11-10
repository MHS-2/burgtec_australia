# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderBomComponent(models.Model):
    _inherit = 'sale.order.bom.component'

    vendor_component_line_ids = fields.One2many('component.lines.by.vendor','component_id',compute="_compute_vendor_component_line_ids",store=True)



    @api.depends('component_line_ids','component_line_ids.supplier_id','component_line_ids.product_qty')
    def _compute_vendor_component_line_ids(self):
        for record in self:
            line_commands = [(5, 0, 0)]  # Clear existing lines
            component_lines = record.component_line_ids.filtered(lambda c: not c.is_parent)
            
            if component_lines:
                # Sort component lines by supplier_id to group them together
                vendors = component_lines.mapped('supplier_id')
                seq = 10

                for vendor in vendors:
                    # Add section header for vendor
                    line_commands.append((0, 0, {
                        'display_type': 'line_section',
                        'name': vendor.name,
                        'supplier_id': vendor.id,
                        'order_id': record.order_id.id,
                        'partner_shipping_id': record.order_id.partner_shipping_id.id,
                        'currency_id': record.order_id.currency_id.id,
                        'sequence': seq,
                    }))
                    seq += 1
                    
                    # Add vendor's lines
                    vendor_lines = component_lines.filtered(lambda c: c.supplier_id.id == vendor.id)
                    for line in vendor_lines:
                        line_commands.append((0, 0, {
                            'is_parent': line.is_parent,
                            'order_line_id': line.order_line_id.id,
                            'order_id': line.order_line_id.order_id.id,
                            'partner_shipping_id': line.order_line_id.order_id.partner_shipping_id.id,
                            'currency_id': line.order_line_id.order_id.currency_id.id,
                            'product_id': line.product_id.id,
                            'product_qty': line.product_qty,
                            'unit_sale_price': line.unit_sale_price,
                            'is_auto_generated': line.is_auto_generated,
                            'supplier_id': vendor.id,
                            'note': line.note,
                            'is_other_than_bom': line.is_other_than_bom,
                            'total_live_unit_cost': line.live_unit_cost,
                            'manual_live_unit_cost': line.manual_live_unit_cost,
                            'sequence': seq,
                        }))
                        seq += 1
            
            record.vendor_component_line_ids = line_commands
    
    def fetch_component_line_by_vendor(self):
        for record in self:
            record._compute_vendor_component_line_ids()






