from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError


PICKING_STATES = {
    'draft':     ('Draft',                     'bg-secondary'),
    'waiting':   ('Waiting Another Operation', 'bg-warning text-dark'),
    'confirmed': ('Waiting',                   'bg-warning text-dark'),
    'assigned':  ('Ready',                     'bg-info text-dark'),
    'done':      ('Done',                      'bg-success'),
    'cancel':    ('Cancelled',                 'bg-danger'),
}

STOCK_MOVE_STATES = {
    'draft':               ('New',                   'bg-secondary'),
    'waiting':             ('Waiting Another Move',  'bg-warning text-dark'),
    'confirmed':           ('Waiting Availability',  'bg-warning text-dark'),
    'partially_available': ('Partially Available',   'bg-info text-dark'),
    'assigned':            ('Available',             'bg-success'),
    'done':                ('Done',                  'bg-success'),
    'cancel':              ('Cancelled',             'bg-danger'),
}

class warehouse_receiving(models.Model):
    _name = 'warehouse.receiving'
    _description = 'Manages Warehouse Receiving Items'

    _sql_constraints = [
        ('uniq_delivery_stage', 'unique(delivery_quote_id)', 'Selected Delivery Stage, already have warehouse receiving created!'),
    ]

    @api.depends('project_quote_id')
    def compute_delivery_quote_domain(self):
        for record in self:
            if not record.project_quote_id:
                record.delivery_quote_domain = False
            if record.project_quote_id:
                record.delivery_quote_domain = [('id', 'in', record.project_quote_id.child_sale_order_ids.ids),('state','=','sale')]

    name = fields.Char('Reference', copy=False)
    project_quote_id = fields.Many2one('sale.order', domain=[('quote_type','=','project_quote'),('is_parent_sale_order', '=', True)])
    delivery_quote_domain = fields.Binary(compute="compute_delivery_quote_domain")
    delivery_quote_id = fields.Many2one('sale.order')
    delivery_quote_code = fields.Binary(related="delivery_quote_id.qr_code")
    delivery_quote_location = fields.Selection(related="delivery_quote_id.location")
    stock_warehouse_id = fields.Many2one('stock.warehouse')
    date = fields.Datetime()
    warehouse_receiving_line_ids = fields.One2many('warehouse.receiving.line','warehouse_receiving_id')
    warehouse_dispatching_id = fields.Many2one('warehouse.dispatching')
    parent_purchase_order_id = fields.Many2one(related="delivery_quote_id.purchase_order_id")
    parent_purchase_order_state = fields.Selection(related="parent_purchase_order_id.state")
    child_purchase_order_ids = fields.Many2many(related='parent_purchase_order_id.child_purchase_order_ids')

    @api.model_create_multi
    def create(self, vals_list):
        """ Create a sequence for the student model """
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = (self.env['ir.sequence'].
                next_by_code('burgtec.warehouse'))
        return super().create(vals_list)

    def fetch_stage_items(self):
        self.sudo().warehouse_receiving_line_ids = [(5,0,0)]
        delivery_stage = self.delivery_quote_id
        purchase_order_obj = self.env['purchase.order'].sudo()
        parent_purchase_order = False
        child_purchese_order = False
        child_purchese_order_lines = False
        parent_purchase_order_pickings = []
        warehouse_lines =[]
        warehouse_line_vals = {}
        description = ''
        if not delivery_stage:
            raise UserError (_('Delivery stage must be selected!'))
        if delivery_stage:
            parent_purchase_order = delivery_stage._get_purchase_orders()
            if not parent_purchase_order:
                raise UserError (_('Parent purchase order not found!. \nKindly confirm this delivery stage %s', delivery_stage.burgtec_quote_reference))
            if parent_purchase_order.state not in ('purchase','done'):
                raise UserError (_('Parent purchase order is not confirmed yet!. \nKindly confirm this purchase order %s', parent_purchase_order.burgtec_purchase_reference))
            parent_purchase_order_pickings = parent_purchase_order.picking_ids.mapped('name')
            child_purchese_order = purchase_order_obj.sudo().search([
                ('origin','in',parent_purchase_order_pickings), ('state', 'in', ['purchase','done']),
            ]).sorted('id')

            if not child_purchese_order:
                raise UserError(_(f"""No Purchase Orders, available for Warehouse Receiving.\n\nMake sure Parent Purchase Order {delivery_stage.purchase_order_id.burgtec_purchase_reference} is Confirmed.\n\nMake sure Child Purchase Orders of {delivery_stage.purchase_order_id.burgtec_purchase_reference} are Confirmed.\n\nChild Purchase Order's whose Pickings are already validated will not be shown here!."""))

            # Filter out child POs whose all pickings are already validated
            child_purchese_order = child_purchese_order.filtered(
                lambda po: not po.is_purchase_lines_fetched_for_bo and not all(
                    picking.state == 'done'
                    for picking in po.picking_ids
                )
            )

            if not child_purchese_order:
                raise UserError(_(f"""Delivery Stage {delivery_stage.burgtec_quote_reference}, Child Purchase Order's Pickings are already Done!"""))


            if child_purchese_order:
                child_purchese_order.sudo().write({
                    'is_purchase_lines_fetched_for_bo':True
                })
                for child_po in child_purchese_order:
                    child_purchese_order_lines = child_po.order_line.filtered(lambda l:not l.product_id.is_delivery_and_installation and l.product_id.type != 'service' and not l.is_back_order_planning)
                    if not child_purchese_order_lines:
                        continue
                    child_purchese_order_lines.sudo().write({
                        'is_back_order_planning':True
                    })
                    for line in child_purchese_order_lines:
                        warehouse_line_vals['purchase_id'] = child_po.id
                        warehouse_line_vals['purchase_order_line_id'] = line.id
                        warehouse_line_vals['supplier_id'] = child_po.partner_id.id
                        warehouse_line_vals['group_code'] = line.line_section_name_child
                        warehouse_line_vals['product_default_code'] = line.product_id.default_code
                        warehouse_line_vals['product_id'] = line.product_id.id
                        warehouse_line_vals['picking_id'] = child_po.picking_ids.filtered(lambda p:p.state not in ['cancel','done'])[0].id
                        if not line.note:
                            description = line.product_id.name
                        if line.note:
                            description = f"""{line.product_id.name} \n Note: \n {line.note}"""
                        warehouse_line_vals['product_description'] = description
                        # If more than one pickings and few are confirmed then qty received must be subtracted from expected qty.
                        warehouse_line_vals['product_qty'] = line.product_uom_qty - line.qty_received
                        warehouse_lines.append((0,0,warehouse_line_vals))
                        warehouse_line_vals = {}
                
                if warehouse_lines:
                    self.warehouse_receiving_line_ids = warehouse_lines
    

    def unchecked_lines(self,purchase_order_id):
        for record in self:
            received_list = []
            warehouse_lines = record.warehouse_receiving_line_ids.filtered(lambda w:w.purchase_id.id == purchase_order_id)
            if not warehouse_lines:
                raise UserError(_("No Warehouse Receiving Lines Found!"))
            if warehouse_lines:
                received_list = warehouse_lines.mapped('is_received')
                if False in received_list:
                    raise UserError(_("Make sure you have marked all lines as received before creating the Back Order!"))
    
    def open_create_backorder_dialog(self,purchase_order_id):
        for record in self:
            picking_data_list = []
            picking_data_vals = {}
            stock_move_line_list =[]
            stock_move_line_vals ={}
            available_picking = False
            warehouse_lines = record.warehouse_receiving_line_ids.filtered(lambda w:w.purchase_id.id == purchase_order_id and not w.is_backorder_created)
            if not warehouse_lines:
                raise UserError(_('No Warehouse Receiving lines available to create BackOrder!'))
            purchase_order = record.env['purchase.order'].sudo().browse(purchase_order_id)
            pickings = purchase_order.picking_ids
            if not pickings:
                raise UserError(_('No Picking Found, We cannot create BackOrder!. You need to confirm this Purchase Order.'))
            if pickings:
                available_picking = pickings.filtered(lambda p:p.state not in ['cancel','done'])
                if len(available_picking) > 1:
                    raise UserError(_('More than 1 Available Pickings are found. Data is Ambiguous!'))
                for pick in available_picking:
                    stock_move_line_list = []
                    stock_move_lines = pick.move_ids
                    state_label, state_class = PICKING_STATES.get(pick.state, ('Unknown', 'bg-secondary'))
                    picking_data_vals['warehouse_receiving_id'] = record.id
                    picking_data_vals['picking_id'] = pick.id
                    picking_data_vals['picking_name'] = pick.name
                    picking_data_vals['picking_source'] = pick.purchase_id.burgtec_purchase_reference
                    picking_data_vals['state'] = state_label
                    picking_data_vals['state_badge_class'] = state_class
                    for move in stock_move_lines:
                        warehouse_line = warehouse_lines.filtered(lambda wl:wl.purchase_order_line_id.id == move.purchase_line_id.id)
                        state_label, state_class = STOCK_MOVE_STATES.get(move.state, ('Unknown', 'bg-secondary'))
                        # If data is incorrect and service or delivery products comes with physical products.
                        if move.product_id.is_delivery_and_installation or move.product_id.type in 'service':
                            stock_move_line_vals['id'] = move.id
                            stock_move_line_vals['warehouse_line_id'] = warehouse_line.id
                            stock_move_line_vals['product_name'] = move.product_id.name
                            stock_move_line_vals['demanded_qty'] = move.product_uom_qty
                            stock_move_line_vals['warehouse_line_received_quantity'] = move.product_qty
                            stock_move_line_vals['state'] = state_label
                            stock_move_line_vals['state_badge_class'] = state_class
                            stock_move_line_list.append(stock_move_line_vals)
                            stock_move_line_vals = {}
                        # Physical products logic
                        else:
                            stock_move_line_vals['id'] = move.id
                            stock_move_line_vals['warehouse_line_id'] = warehouse_line.id
                            stock_move_line_vals['product_name'] = move.product_id.name
                            stock_move_line_vals['demanded_qty'] = move.product_uom_qty
                            stock_move_line_vals['warehouse_line_received_quantity'] = warehouse_line.received_qty
                            stock_move_line_vals['state'] = state_label
                            stock_move_line_vals['state_badge_class'] = state_class
                            stock_move_line_list.append(stock_move_line_vals)
                            stock_move_line_vals = {}
                    picking_data_vals['stock_move_lines'] = stock_move_line_list
                    picking_data_list.append(picking_data_vals)
                    picking_data_vals = {}
                return picking_data_list
    
    def create_backorder(self,purchase_order_id, picking_data):
        for record in self:
            # Get Picking ID.
            vals = {}
            list_of_vals = []
            rem_qty = 0
            picking_id = picking_data[0]['picking_id']
            picking = record.env['stock.picking'].sudo().browse(picking_id)
            purchase_order = record.env['purchase.order'].sudo().browse(purchase_order_id)
            stock_move_lines = picking_data[0]['stock_move_lines']
            warehouse_lines = record.warehouse_receiving_line_ids.filtered(lambda w: w.purchase_id.id == purchase_order_id and not w.is_backorder_created)
            for line in stock_move_lines:
                stock_move_line = record.env['stock.move'].sudo().browse(line['id'])
                stock_move_line.quantity = line['warehouse_line_received_quantity']
            warehouse_lines.sudo().write({
                'is_backorder_created': True
            })
            split_picking_obj = picking.action_custom_split_transfer()
            # picking.action_split_transfer()
            picking.button_validate()

            #  Now process and see remaining partial lines.
            # purchase_lines = purchase_order.order_line.filtered(lambda ol:ol.product_qty - ol.qty_received != 0)
            purchase_lines = purchase_order.order_line.filtered(lambda ol:ol.product_qty - ol.qty_received != 0)
            for order_line in purchase_lines:
                vals['purchase_id'] = purchase_order_id
                vals['purchase_order_line_id'] = order_line.id
                vals['supplier_id'] = purchase_order.partner_id.id
                vals['group_code'] = order_line.line_section_name_child
                vals['product_default_code'] = order_line.product_id.default_code
                vals['product_id'] = order_line.product_id.id
                vals['picking_id'] = split_picking_obj.id
                if not order_line.note:
                    description = order_line.product_id.name
                if order_line.note:
                    description = f"""{order_line.product_id.name} \n Note: \n {order_line.note}"""
                vals['product_description'] = description
                # Now received qty will be the remaining quantity
                rem_qty = order_line.product_qty - order_line.qty_received 
                vals['product_qty'] = rem_qty
                vals['warehouse_receiving_id'] = record.id
                list_of_vals.append(vals)
                vals = {}
            self.env['warehouse.receiving.line'].sudo().create(list_of_vals)

            self.create_or_update_dispatching(warehouse_lines)
    
    def auto_validate_picking(self,purchase_order_id):
        for record in self:
            purchase_order = record.env['purchase.order'].sudo().browse(purchase_order_id)
            warehouse_lines = record.warehouse_receiving_line_ids.filtered(lambda w: w.purchase_id.id == purchase_order_id and not w.is_backorder_created)
            # All warehouse lines for same PO FETCHED.

            # Check if all are received.
            received_status_list = warehouse_lines.mapped('is_received')
            if False in received_status_list:
                # Not All are received if any False found
                return
            
            mismatches = warehouse_lines.filtered(
                lambda l: l.product_qty != l.received_qty
            )

            if mismatches:
                # All qauntities not received
                return

            # See if all expected and received qty is same.
            all_match = all(
                line.product_qty == line.received_qty
                for line in warehouse_lines
            )

            if all_match:
                picking = purchase_order.picking_ids.filtered(lambda p:p.state not in ['cancel','done'])
                if len(picking) == 1:
                    # One Available Picking Found!
                    picking.button_validate()
                    self.create_or_update_dispatching(warehouse_lines)
                    return True

                if len(picking) < 1:
                    raise UserError(_("No Picking's Found To Validate Received Products!!!"))
                
                if len(picking) > 2:
                    raise UserError(_("More than one Available Pickings Found. Data is Ambiguous so received product's were not validated!!!"))

    
    def create_or_update_dispatching(self,warehouse_lines):
        dispatch_result = False
        vals = {}
        lines_vals= {}
        line_vals_list = []
        dispatching_object = self.warehouse_dispatching_id

        # Update Lines
        if dispatching_object:
            if warehouse_lines:
                for wl in warehouse_lines:
                    lines_vals = {
                        'warehouse_dispatching_id':dispatching_object.id,
                        'warehouse_receiving_line_id': wl.id
                    }
                    line_vals_list.append(lines_vals)
                    lines_vals = {}
            
            if line_vals_list:
                self.env['warehouse.dispatching.line'].sudo().create(line_vals_list)


        # Create if not exist.
        if not dispatching_object:
            if warehouse_lines:
                for wl in warehouse_lines:
                    lines_vals = {
                        'warehouse_receiving_line_id': wl.id
                    }
                    line_vals_list.append((0,0,lines_vals))
                    lines_vals = {}
                vals = {
                    'warehouse_receiving_id':self.id,
                    'warehouse_dispatching_line_ids':line_vals_list,
                }
            dispatch_result = self.env['warehouse.dispatching'].sudo().create(vals)
            if dispatch_result:
                self.warehouse_dispatching_id = dispatch_result.id
    

    def action_view_dispatching(self):
        return {
            'name': _('Warehouse Dispatching'),
            'type': 'ir.actions.act_window',
            'res_model': 'warehouse.dispatching',
            'view_mode': 'form',
            'res_id': self.warehouse_dispatching_id.id,
        }









                
                


                    






                




            
        

                    
                        



            



