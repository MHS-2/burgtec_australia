# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BackOrderPlanning(models.Model):
    _name = 'back.order.planning'
    _description = 'Backorder Planning'

    planning_screen_id = fields.Many2one('planning.screen')
    sale_order_id = fields.Many2one('sale.order')
    product_id = fields.Many2one('product.product')
    component_id = fields.Many2one('product.product')
    purchase_order_id = fields.Many2one('purchase.order')
    picking_ids = fields.Many2many('stock.picking')
    picking_id = fields.Many2one('stock.picking')
    product_uom_qty = fields.Float()
    expected_qty = fields.Float()
    date_planned = fields.Datetime(string="ETA Date")
    back_order_qty = fields.Float(compute="_compute_back_order_qty", store=True)
    back_order_date_planned = fields.Datetime(string="Backorder ETA")
    is_check = fields.Boolean(default=False)
    stock_move_id = fields.Many2one('stock.move')
    # planned_backorder_line_id = fields.Many2one('back.order.lines.planned')
    purchase_order_line_id = fields.Many2one('purchase.order.line')
    sequence = fields.Integer("Sequence")
    name = fields.Char()
    display_type = fields.Selection([
        ('line_section', "Section"),
    ], string="Display Type")
    is_backorder_created = fields.Boolean()
    back_order_count = fields.Integer()
    is_no_longer_split = fields.Boolean()
    is_confirmed = fields.Boolean()
    is_process_completed = fields.Boolean()


    @api.depends('product_uom_qty','expected_qty')
    def _compute_back_order_qty(self):
        for record in self:
            if record.expected_qty > 0.0:
                record.back_order_qty = (record.product_uom_qty - record.expected_qty)
            else:
                record.back_order_qty = 0.0
    

    def create_back_order(self):
        seq = 10
        vals = {}
        list_of_vals = []
        rem_qty = 0
        checked_planning_lines_list = []
        available_picking = False
        stock_moves = False
        stock_move_line = False
        back_order_count = self.back_order_count
        purchase_order = self.purchase_order_id
        split_picking_obj = False
        back_order_colors_obj = self.env['back.order.color'].sudo()
        back_order_colors_rec = False
        is_backorder_split = True
        is_zero_qty_left = False
        back_order_planning_lines = self.search([('purchase_order_id','=',purchase_order.id),('display_type','=',False), ('is_backorder_created','=',False)]).sorted(lambda pl:pl.sequence)
        # planning_lines_picking = back_order_planning_lines.mapped('picking_ids')[0]
        planning_lines_picking = back_order_planning_lines.mapped('picking_id')
        planning_line = False
        custom_back_order_picking = False
        allocation_vals_list = []
        allocation_vals = {}
        allocation_res = False
        if not back_order_planning_lines:
            raise UserError(_(f"No Back Order Planning Lines Found For Purchase Order {purchase_order.burgtec_purchase_reference}"))
        if back_order_planning_lines:
            checked_planning_lines_list = back_order_planning_lines.mapped('is_check')
            if False in checked_planning_lines_list:
                raise UserError(_(f"Make sure you have marked all lines as checked before creating the Back Order for Purchase Order {purchase_order.burgtec_purchase_reference}"))
        pickings = purchase_order.picking_ids
        if not pickings:
            raise UserError(_('No Picking Found, We cannot create BackOrder!. You need to confirm this Purchase Order.'))
        if pickings:
            available_picking = pickings.filtered(lambda p:not p.is_custom_back_order_created and p.state not in ['cancel','done'])
            if len(available_picking) > 1:
                raise UserError(_('More than 1 Available Pickings are found. Data is Ambiguous!'))
            stock_moves = available_picking.move_ids
        # picking_id = picking_data[0]['picking_id']
        # picking = record.env['stock.picking'].sudo().browse(picking_id)
        # purchase_order = record.env['purchase.order'].sudo().browse(purchase_order_id)
        # stock_move_lines = picking_data[0]['stock_move_lines']
        # warehouse_lines = record.warehouse_receiving_line_ids.filtered(lambda w: w.purchase_id.id == purchase_order_id)
        for line in back_order_planning_lines:
            stock_move_line = stock_moves.filtered(lambda m:m.purchase_line_id.id == line.purchase_order_line_id.id)
            stock_move_line.quantity = line.expected_qty
            seq = line.sequence
            # last_line_seq = seq
        back_order_planning_lines.sudo().write({
            'is_backorder_created': True
        })
        split_picking_obj = available_picking.action_custom_split_transfer()
        if available_picking.backorder_id:
            custom_back_order_picking = self.env['back.order.picking'].sudo().create({
                    'planning_screen_id': self.planning_screen_id.id,
                    'purchase_order_id': purchase_order.id,
                    'picking_id': available_picking.id,
                    'order_id':self.sale_order_id.id,
                })
            self.planning_screen_id.back_order_custom_picking_ids = [(4,custom_back_order_picking.id,0)]

            # Create allocations.
            for line in back_order_planning_lines:
                stock_move_line = stock_moves.filtered(lambda m:m.purchase_line_id.id == line.purchase_order_line_id.id)
                if split_picking_obj.backorder_id:
                    # Create Allocation Record.
                    allocation_vals = {
                            'planning_screen_id': self.planning_screen_id.id,
                            'sale_order_id': self.sale_order_id.id,
                            'component_id': line.component_id.id,
                            'purchase_order_id': purchase_order.id,
                            'custom_bo_picking_id': custom_back_order_picking.id,
                            'purchase_order_line_id': line.purchase_order_line_id.id,
                            'stock_move_id': stock_move_line.id,
                            'allocated_qty': line.expected_qty
                        }
                    allocation_vals_list.append(allocation_vals)
                    allocation_vals = {}
            # Create the allocated record.
            if allocation_vals_list:
                allocation_res = self.env['back.order.lines.planned.allocation'].sudo().create(allocation_vals_list)
                # As One Back order can have multiple allocations so a one2many relation here as well.
                if allocation_res:
                    for allocation in allocation_res:
                        custom_back_order_picking.back_order_lines_planned_allocation_ids = [(4,allocation.id,0)]

        if split_picking_obj:
            if planning_lines_picking:
                planning_lines_picking.is_custom_back_order_created = True

        # If a back order picking then do not validate it.
        if not available_picking.backorder_id:
            is_backorder_split = False
            available_picking.button_validate()
        
        # back order created successfully so update the count.
        back_order_count+=1
        self.back_order_count = back_order_count

        next_lines = self.planning_screen_id.backorder_planning_line_ids.filtered(lambda pl:pl.sequence > seq).sorted(lambda pl:pl.sequence)

        #  Now process and see remaining partial lines.
        purchase_lines = purchase_order.order_line.filtered(lambda ol:ol.product_qty - ol.qty_received != 0)

        # If we get next lines having 1 quantity, means it cannot be further split so allocations must be created by default for them.
        allocation_vals_list = []
        allocation_vals = {}

        for line in purchase_lines:
            # if line.move_ids:
            #     move = line.move_ids.filtered(lambda m:m.state not in ['cancel','done'])
            if is_backorder_split:
                planning_line = back_order_planning_lines.filtered(lambda bl:bl.purchase_order_line_id.id == line.id)
                if planning_line.product_uom_qty - planning_line.expected_qty == 0.0:
                    continue           
            seq += 1
            vals = {
                'planning_screen_id': self.planning_screen_id.id,
                'sale_order_id': self.sale_order_id.id,
                'component_id': line.product_id.id,
                'purchase_order_id': purchase_order.id,
                # 'picking_ids': purchase_order.picking_ids.filtered(lambda p:p.state not in ['cancel','done'] and p.),
                # 'picking_ids': [(4,split_picking_obj.id,0)],
                'picking_id': split_picking_obj.id,
                'product_uom_qty': line.product_uom_qty - line.qty_received,
                'date_planned': line.date_planned, 
                # 'stock_move_id': move.id if move else False,
                'purchase_order_line_id': line.id,
                'sequence': seq,
                'back_order_count': self.back_order_count,
            }
            if is_backorder_split:
                # planning_line = back_order_planning_lines.filtered(lambda bl:bl.purchase_order_line_id.id == line.id)
                vals['product_uom_qty'] = planning_line.product_uom_qty - planning_line.expected_qty
            list_of_vals.append(vals)
            vals={}
        result = self.env['back.order.planning'].sudo().create(list_of_vals)
        if result:
            for rec in result:
                back_order_colors_rec = back_order_colors_obj.search([('back_order_count','=',back_order_count)])
                self.env['color.picker'].sudo().create({
                    'record_id': rec.id,
                    'res_model': 'back.order.planning',
                    'color': back_order_colors_rec.color if back_order_colors_rec else '#FFFFFF',
                })

        # Update Sequences of previously existing lines.
        for nl in next_lines:
            seq += 1
            nl.sequence = seq
        
            
    
    @api.constrains("is_check","expected_qty")
    def _check_expected_qty(self):
        for record in self:
            if record.is_check:
                if record.expected_qty <= 0.0:
                    raise UserError(_("Expected Quantity Must be greater than 0, when marking a line as checked."))
    
    def get_back_order_matrix_data(self):
        """Return matrix data for the back order allocations widget."""
        self.ensure_one()
        # Aggregate order line quantities by product.
        products = {}
        order_line = self.purchase_order_id.order_line 
        for line in order_line:
            product = line.product_id
            if not product:
                continue
            if product.type in ('combo','service'):
                continue
            if product.is_delivery_and_installation:
                continue
            # if product.id not in products:
            if line.id not in products: # Each Purchase Order Line with product is treated seperately whether the product was same or not.
                products[line.id] = {
                    'order_line_id':line.id,
                    'supplier':line.partner_id.name,
                    # 'product_identifier':line.product_identifier,
                    # 'code': line.line_section_name,
                    'product_id': product.id,
                    'display_name': product.display_name,
                    # 'product_custom_name': line.custom_product_name,
                    'total_qty': line.product_qty - line.qty_received,
                }
            # products[line.id]['total_qty'] += line.product_uom_qty

        # Get back orders sorted by sequence
        custom_back_order_pickings = self.planning_screen_id.back_order_custom_picking_ids.filtered(lambda bo:bo.purchase_order_id.id == self.purchase_order_id.id).sorted('id')
        back_orders = [{
            'id': bo.id,
            'name': bo.picking_id.name,
            'state': bo.picking_id.state,
            # 'sequence': area.sequence,
        } for bo in custom_back_order_pickings]

        # Get allocations as {product_id}_{custom_bo_id} -> qty
        back_order_allocations = self.planning_screen_id.backorder_planned_line_allocation_ids.filtered(lambda bo:bo.purchase_order_id.id == self.purchase_order_id.id)
        allocations = {}
        for alloc in back_order_allocations:
            # key = '%s_%s' % (alloc.product_id.id, alloc.area_id.id)
            # Each Sale Order Line with product is treated seperately whether the product was same or not.
            key = '%s_%s' % (alloc.purchase_order_line_id.id, alloc.custom_bo_picking_id.id)
            allocations[key] = alloc.allocated_qty

        # Compute available qty per product
        product_list = []
        for pid, pdata in products.items():
            allocated_total = sum(
                allocations.get('%s_%s' % (pid, bo['id']), 0.0)
                for bo in back_orders
            )
            pdata['available_qty'] = pdata['total_qty'] - allocated_total
            product_list.append(pdata)
        
        return {
            'back_orders': back_orders,
            'products': product_list,
            'allocations': allocations,
            'process_completed': self.is_process_completed
        }
    
    def save_back_order_allocation(self, productorderline_id, product_id, back_order_id, qty):
        """Save or update an back order allocation for a product in it stock move."""
        self.ensure_one()
        qty = max(float(qty), 0.0)
        back_order_allocations = self.planning_screen_id.backorder_planned_line_allocation_ids

        alloc = back_order_allocations.filtered(
            lambda a: a.purchase_order_id.id == self.purchase_order_id.id and a.component_id.id == product_id
            and a.custom_bo_picking_id.id == back_order_id and a.purchase_order_line_id.id == productorderline_id
        )
        if alloc:
            alloc.allocated_qty = qty

        # This logic not needed now. As moves will be updated in the end when confirming back orders.....
        # Logic to update back order picking lines quantity, which is also stock move.
        # stock_move = alloc.stock_move_id
        # stock_move.quantity = qty

        # Validate total allocation does not exceed purchase order line qty
        self._validate_back_order_allocations()
        return self.get_back_order_matrix_data()
    
    def _validate_back_order_allocations(self):
        """Validate that allocations don't exceed total quantities."""
        for record in self:
            products = {}
            order_line = record.purchase_order_id.order_line 
            for line in order_line:
                # Each Purchase Order Line with product is treated seperately whether the product was same or not.
                order_line_id = line.id
                if order_line_id not in products:
                    products[order_line_id] = {
                        'name': line.product_id.display_name,
                        'total_qty': line.product_qty - line.qty_received,
                    }
            
            back_order_allocations = record.planning_screen_id.backorder_planned_line_allocation_ids.filtered(lambda bo:bo.purchase_order_id.id == record.purchase_order_id.id)

            for alloc in back_order_allocations:
                # Each Purchase Order Line with product is treated seperately whether the product was same or not.
                order_line_id = alloc.purchase_order_line_id.id
                if order_line_id in products:
                    products[order_line_id].setdefault('allocated', 0.0)
                    products[order_line_id]['allocated'] += alloc.allocated_qty

            for order_line_id, data in products.items():
                allocated = data.get('allocated', 0.0)
                if allocated > data['total_qty']:
                    raise ValidationError(
                        _('Total allocated quantity (%(allocated)s) for "%(product)s" '
                          'exceeds the back order quantity (%(total)s).',
                          allocated=allocated,
                          product=data['name'],
                          total=data['total_qty'],
                        )
                    )



    
    def view_back_order_matrix_table(self):
        view_id = self.env.ref('burgtec_back_order.view_back_order_planning_allocation_table_form').id
        return {
            'target': 'new',
            'type': 'ir.actions.act_window',
            'name': _('Back Order Allocation Table'),
            'res_model': 'back.order.planning',
            'view_mode': 'form',
            'view_id': view_id,
            'context': "{'create': False,'delete': False,'dialog_size': 'extra-large',}",
             'res_id': self.id,
        }
    
    def action_confirm(self):
        allocation_vals = {}
        purchase_order = self.purchase_order_id
        back_order_planning_lines = self.search([('purchase_order_id','=',purchase_order.id),('display_type','=',False), ('is_backorder_created','=',False)]).sorted(lambda pl:pl.sequence)
        picking_id = False
        if back_order_planning_lines:
            picking_id = back_order_planning_lines.mapped('picking_id')
        

        for line in back_order_planning_lines:       
            #  Search for custom picking if exists
            custom_back_order_picking = False
            custom_back_order_picking = self.env['back.order.picking'].sudo().search([('picking_id','=',picking_id.id)])
            if not custom_back_order_picking:
                custom_back_order_picking = self.env['back.order.picking'].sudo().create({
                    'planning_screen_id': self.planning_screen_id.id,
                    'purchase_order_id': purchase_order.id,
                    'picking_id': picking_id.id,
                    'order_id':self.sale_order_id.id,
                    })
                if custom_back_order_picking.id not in self.planning_screen_id.back_order_custom_picking_ids.ids:
                    self.planning_screen_id.back_order_custom_picking_ids = [(4,custom_back_order_picking.id,0)]
            stock_moves = picking_id.move_ids
            stock_move_line = stock_moves.filtered(lambda m:m.purchase_line_id.id == line.purchase_order_line_id.id)
            allocation_vals = {
                    'planning_screen_id': self.planning_screen_id.id,
                    'sale_order_id': self.sale_order_id.id,
                    'component_id': line.component_id.id,
                    'purchase_order_id': purchase_order.id,
                    'custom_bo_picking_id': custom_back_order_picking.id,
                    'purchase_order_line_id': line.purchase_order_line_id.id,
                    'stock_move_id': stock_move_line.id,
                    'allocated_qty': line.product_uom_qty,
                }
            # Create the allocated record.
            if allocation_vals:
                allocation_res = self.env['back.order.lines.planned.allocation'].sudo().create(allocation_vals)
                # As One Back order can have multiple allocations so a one2many relation here as well.
                if allocation_res:
                    custom_back_order_picking.back_order_lines_planned_allocation_ids = [(4,allocation_res.id,0)]
            allocation_vals = {}

            # No longer split or back order now needs to be created.
            self.is_no_longer_split = True
            back_order_planning_lines.write({
                'is_confirmed': True
            })
    
    def confirm_back_order_pickings(self):
        matrix_data = self.get_back_order_matrix_data()
        back_orders = matrix_data['back_orders']
        products = matrix_data['products']
        allocations = matrix_data['allocations']
        key = False
        back_order_ids = []
        custom_bo_recordset = False
        custom_bo_allocations = False
        stock_move = False
        stock_move_demand = 0.0
        stock_move_qty = 0.0
        allocated_qty = 0.0
        pickings = False

        for product in products:
            # If user tries to confirm back orders but the total available qty is not zero. We need to make him stop.
            if product['available_qty'] > 0:
                raise UserError(_('You can not confirm back orders, when quantities are still available. \nMake sure to use all available quantity!'))
            for bo in back_orders:
                if bo['id'] not in back_order_ids:
                    back_order_ids.append(bo['id'])
                key = f"{product['order_line_id']}_{bo['id']}"
                if key in allocations and allocations[key] == 0.0:
                    raise UserError(_('You can not confirm back orders, when allocation is 0. \nAllocation must be greater than zero in Allocation Table.'))
        
        if back_order_ids:
            custom_bo_recordset = self.env['back.order.picking'].sudo().browse(back_order_ids)
            if custom_bo_recordset:
                # now we will go through each allocation. And update demand and quantity for the final time and validate the pickings.
                for custom_bo in custom_bo_recordset:
                    custom_bo_allocations = custom_bo.back_order_lines_planned_allocation_ids
                    for alloc in custom_bo_allocations:
                        stock_move = alloc.stock_move_id
                        stock_move_qty = stock_move.quantity
                        stock_move_demand = stock_move.product_uom_qty
                        allocated_qty = alloc.allocated_qty
                        if stock_move_demand != allocated_qty:
                            stock_move.write({
                                'product_uom_qty': allocated_qty,
                                'quantity': allocated_qty,
                            })
                #Validate all pickings after update.
                pickings = custom_bo_recordset.mapped('picking_id')
                pickings.button_validate()
                self.is_process_completed = True







        
        




    

class BackOrderLinesPlannedAllocation(models.Model):
    _name = 'back.order.lines.planned.allocation'
    _description = 'Backorder Lines Planned Allocation'

    planning_screen_id = fields.Many2one('planning.screen')
    sale_order_id = fields.Many2one('sale.order')
    # product_id = fields.Many2one('product.product')
    component_id = fields.Many2one('product.product')
    purchase_order_id = fields.Many2one('purchase.order')
    picking_id = fields.Many2one('stock.picking')
    custom_bo_picking_id = fields.Many2one('back.order.picking')
    purchase_order_line_id = fields.Many2one('purchase.order.line', ondelete='cascade')
    stock_move_id = fields.Many2one('stock.move', ondelete='cascade')
    allocated_qty = fields.Float(
        string='Allocated Quantity',
        default=0.0,
        digits='Product Unit of Measure'
    )
    back_order_picking_id = fields.Many2one('back.order.picking')

class BackOrderPicking(models.Model):
    _name = 'back.order.picking'
    _description = 'Backorder Picking'
    _rec_name = 'picking_id'

    planning_screen_id = fields.Many2one('planning.screen')
    picking_id = fields.Many2one('stock.picking')
    order_id = fields.Many2one('sale.order')
    purchase_order_id = fields.Many2one('purchase.order')
    back_order_lines_planned_allocation_ids = fields.One2many('back.order.lines.planned.allocation','back_order_picking_id')



