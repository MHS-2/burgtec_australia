from odoo import http

from odoo.http import request

PURCHASE_ORDER_STATES = {
    'draft':      ('RFQ',            'bg-info'),
    'sent':       ('RFQ Sent',       'bg-info text-dark'),
    'to approve': ('To Approve',     'bg-warning text-dark'),
    'purchase':   ('Purchase Order', 'bg-success'),
    'done':       ('Locked',         'bg-success'),
    'cancel':     ('Cancelled',      'bg-danger'),
}

class BurgtecWarehouse(http.Controller):
    @http.route('/burgtec_warehouse/fetch_stage_items', auth='user', type='json')
    def fetch_warehouse_complete_data(self,warehouse_receiving_id, **kw):
        complete_data = []
        warehouse_receiving_obj = self._get_warehouse_receiving_record(warehouse_receiving_id)
        if warehouse_receiving_obj:
            complete_data = self._warehouse_receiving_data_maker(warehouse_receiving_obj)
        
        # Safely extract related field values
        project_quote = warehouse_receiving_obj.project_quote_id.burgtec_quote_reference if warehouse_receiving_obj.project_quote_id else ''
        delivery_quote = warehouse_receiving_obj.delivery_quote_id.burgtec_quote_reference if warehouse_receiving_obj.delivery_quote_id else ''
        delivery_code = warehouse_receiving_obj.delivery_quote_code if warehouse_receiving_obj.delivery_quote_code else ''
        delivery_location = warehouse_receiving_obj.delivery_quote_location
        client_name = warehouse_receiving_obj.delivery_quote_id.partner_id.name if warehouse_receiving_obj.delivery_quote_id and warehouse_receiving_obj.delivery_quote_id.partner_id else ''
        stock_warehouse = warehouse_receiving_obj.stock_warehouse_id.name if warehouse_receiving_obj.stock_warehouse_id else ''
        
        return {
            'warehouse_id':warehouse_receiving_id,
            'name':warehouse_receiving_obj.name if warehouse_receiving_obj else '',
            'project_quote': project_quote,
            'delivery_quote': delivery_quote,
            'delivery_code': delivery_code,
            'delivery_location':delivery_location,
            'client_name': client_name,
            'stock_warehouse_id': stock_warehouse,
            'date': warehouse_receiving_obj.date if warehouse_receiving_obj else '',
            'complete_data': complete_data,
        }
    
    def _get_warehouse_receiving_record(self, warehouse_receiving_id):
        return request.env['warehouse.receiving'].browse(warehouse_receiving_id)
    
    def _warehouse_receiving_data_maker(self,record):
        data_list = []
        values = {}
        line_list = []
        line_values = {}
        warehouse_lines = record.warehouse_receiving_line_ids
        child_purchase_orders = warehouse_lines.mapped('purchase_id')
        filtered_warehouse_lines = False
        if child_purchase_orders:
            for child_po in child_purchase_orders:
                state_label, state_class = PURCHASE_ORDER_STATES.get(child_po.state, ('Unknown', 'bg-secondary'))
                values['warehouse_id'] = record.id
                values['purchase_id'] = child_po.id
                values['purchase_order_state'] = state_label
                values['purchase_order_state_badge_class'] = state_class
                values['purchase_order_name'] = child_po.burgtec_purchase_reference
                values['supplier_name'] = child_po.partner_id.name
                filtered_warehouse_lines = warehouse_lines.filtered(lambda l:l.purchase_id.id == child_po.id)
                if filtered_warehouse_lines:
                    for line in filtered_warehouse_lines:
                        line_values['line_id'] = line.id
                        line_values['warehouse_id'] = line.warehouse_receiving_id.id
                        line_values['purchase_order_id'] = line.purchase_id.id
                        line_values['group_code'] = line.group_code
                        line_values['product_default_code'] = line.product_default_code
                        line_values['product_name'] = line.product_id.name
                        line_values['product_description'] = line.product_description
                        line_values['picking_id'] = line.picking_id.name
                        line_values['product_qty'] = line.product_qty
                        line_values['received_qty'] = line.received_qty
                        line_values['back_order_qty'] = line.back_order_qty
                        line_values['is_received'] = line.is_received
                        line_values['is_staged'] = line.is_staged
                        line_values['is_dispatched'] = line.is_dispatched
                        line_values['is_delivered'] = line.is_delivered
                        line_values['is_backorder_created'] = line.is_backorder_created
                        line_list.append(line_values)
                        line_values={}
                    values['purchase_lines'] = line_list
                    data_list.append(values)
                    line_list = []
                    values = {}
            return data_list
        else:
            return data_list
    

    #  For Warehouse Dispatching Widget.

    @http.route('/burgtec_warehouse/fetch_dispatch_data', auth='user', type='json')
    def fetch_warehouse_dispatch_complete_data(self,warehouse_dispatching_id, **kw):
        complete_data = []
        warehouse_dispatching_obj = self._get_warehouse_dispatching_record(warehouse_dispatching_id)
        if warehouse_dispatching_obj:
            complete_data = self._warehouse_dispatching_data_maker(warehouse_dispatching_obj)
        
        return {
            'complete_data': complete_data,
        }
    
    def _get_warehouse_dispatching_record(self, warehouse_dispatching_id):
        return request.env['warehouse.dispatching'].browse(warehouse_dispatching_id)
    

    def _warehouse_dispatching_data_maker(self,record):
        data_list = []
        values = {}
        line_list = []
        line_values = {}
        warehouse_dispatching_lines = record.warehouse_dispatching_line_ids
        for line in warehouse_dispatching_lines:
            line_values['line_id'] = line.id
            line_values['warehouse_dispatching_id'] = line.warehouse_dispatching_id.id
            line_values['warehouse_receiving_line_id'] = line.warehouse_receiving_line_id.id
            # line_values['purchase_order_id'] = line.purchase_id.id
            line_values['group_code'] = line.group_code
            line_values['product_default_code'] = line.product_default_code
            line_values['product_name'] = line.product_id.name
            line_values['product_description'] = line.product_description
            line_values['picking_id'] = line.picking_id.name
            # line_values['product_qty'] = line.product_qty
            line_values['received_qty'] = line.received_qty
            # line_values['back_order_qty'] = line.back_order_qty
            # line_values['is_received'] = line.is_received
            # line_values['is_staged'] = line.is_staged
            line_values['is_dispatched'] = line.is_dispatched
            line_values['is_delivered'] = line.is_delivered
            # line_values['is_backorder_created'] = line.is_backorder_created
            line_list.append(line_values)
            line_values={}

        return line_list


                








