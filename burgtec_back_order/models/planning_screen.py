# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PlanningScreen(models.Model):
    _inherit = 'planning.screen'


    def _compute_ds_domain(self):
        for record in self:
            sale_state_orders = False
            child_orders = record.order_id.child_sale_order_ids
            if record.order_id and child_orders: 
                sale_state_orders = child_orders.filtered(lambda s: s.state == 'sale')
                record.ds_domain =  [('id', 'in', sale_state_orders.ids)]
            else:
                record.ds_domain =  [('id', 'in', child_orders.ids)]
    
    @api.depends('delivery_stage_id')
    def _compute_planning_line_domain(self):
        for record in self:
            if record.delivery_stage_id:
                return [('sale_order_id', '=', record.delivery_stage_id.id)]



    ds_domain = fields.Binary(compute="_compute_ds_domain")
    delivery_stage_id = fields.Many2one('sale.order')
    backorder_planning_line_ids = fields.One2many('back.order.planning','planning_screen_id', domain=lambda self: self._compute_planning_line_domain())
    # backorder_planning_line_ids = fields.One2many('back.order.planning','planning_screen_id', compute="_compute_backorder_planning_lines", store=True, readonly=False, domain=lambda self: self._compute_planning_line_domain(),)
    backorder_planned_line_allocation_ids = fields.One2many('back.order.lines.planned.allocation','planning_screen_id')
    back_order_custom_picking_ids = fields.One2many('back.order.picking','planning_screen_id')

    def fetch_bo_planning_lines(self):
        # if not self.delivery_stage_id:
        #     # Clear all lines if no delivery stage is selected
        #     self.backorder_planning_line_ids = [(5, 0, 0)]
        # Build new lines for the selected delivery stage
        child_purchase_orders = self.delivery_stage_id.purchase_order_id.child_purchase_order_ids.filtered(
                lambda c: c.state in ['purchase','done']
            ).sorted('id')
            # and c.picking_ids.filtered(lambda p: p.state not in ['cancel','done']
        if not child_purchase_orders:
            raise UserError(_(f"""No Purchase Orders, available for Back Order Planning Screen.\n\nMake sure Parent Purchase Order {self.delivery_stage_id.purchase_order_id.burgtec_purchase_reference} is Confirmed.\n\nMake sure Child Purchase Orders of {self.delivery_stage_id.purchase_order_id.burgtec_purchase_reference} are Confirmed.\n\nChild Purchase Order's whose Pickings are already validated will not be shown here!."""))

        # Filter out child POs whose all pickings are already validated
        child_purchase_orders = child_purchase_orders.filtered(
            lambda po: not po.is_purchase_lines_fetched_for_bo and not all(
                picking.state == 'done'
                for picking in po.picking_ids
            )
        )

        if not child_purchase_orders:
            raise UserError(_(f"""Delivery Stage {self.delivery_stage_id.burgtec_quote_reference}, Child Purchase Order's Pickings are already Done!"""))
        child_purchase_orders.sudo().write({
            'is_purchase_lines_fetched_for_bo':True
        })
        line_vals = []
        move = False
        seq = 10
        for po in child_purchase_orders:
            purchase_lines = po.order_line.filtered(lambda l:not l.product_id.is_delivery_and_installation and l.product_id.type != 'service' and not l.is_back_order_planning)
            if not purchase_lines:
                continue
            line_vals.append((0, 0, {
                    'display_type': 'line_section',
                    'name': po.burgtec_purchase_reference,
                    'sale_order_id': self.delivery_stage_id.id,
                    'purchase_order_id': po.id,
                    'sequence': seq,
                }))
            seq += 1
            purchase_lines.sudo().write({
                'is_back_order_planning':True
            })
            # Now these lines will not be duplicated if again the same delivery stage is selected gor back order planning.
            for line in purchase_lines:
                if line.product_uom_qty - line.qty_received != 0.0:
                # if line.move_ids:
                #     move = line.move_ids.filtered(lambda m:m.state not in ['cancel','done'])
                    line_vals.append((0, 0, {
                        'sale_order_id': self.delivery_stage_id.id,
                        'component_id': line.product_id.id,
                        'purchase_order_id': po.id,
                        # 'picking_ids': po.picking_ids.filtered(lambda p:p.state not in ['cancel','done']),
                        'picking_id': po.picking_ids.filtered(lambda p:p.state not in ['cancel','done'])[0].id,
                        'product_uom_qty': line.product_uom_qty - line.qty_received,
                        'date_planned': line.date_planned, 
                        # 'stock_move_id': move.id if move else False,
                        'purchase_order_line_id': line.id,
                        'sequence': seq,
                    }))
                    seq += 1

        if line_vals:
            self.backorder_planning_line_ids = line_vals


    @api.depends('delivery_stage_id')
    def _compute_backorder_planning_lines(self):
        for record in self:
            if not record.delivery_stage_id:
                # Clear all lines if no delivery stage is selected
                record.backorder_planning_line_ids = [(5, 0, 0)]
                continue

            # Check if lines already exist for this specific delivery stage
            existing_lines_for_stage = record.backorder_planning_line_ids.filtered(
                lambda l: l.sale_order_id.id == record.delivery_stage_id.id
            )

            # Remove lines that belong to OTHER stages (stale lines)
            lines_to_remove = record.backorder_planning_line_ids.filtered(
                lambda l: l.sale_order_id.id != record.delivery_stage_id.id
            )
            if lines_to_remove:
                record.backorder_planning_line_ids = [(3, line.id) for line in lines_to_remove]

            # Skip creation if lines for this stage already exist (prevents duplicates on reselect)
            if existing_lines_for_stage:
                continue

            # Build new lines for the selected delivery stage
            child_purchase_orders = record.delivery_stage_id.purchase_order_id.child_purchase_order_ids.filtered(
                lambda c: c.state in ['purchase','done']
            ).sorted('id')
            # and c.picking_ids.filtered(lambda p: p.state not in ['cancel','done']
            if not child_purchase_orders:
                raise UserError(_(f"""No Purchase Orders, available for Back Order Planning Screen.\n\nMake sure Parent Purchase Order {record.delivery_stage_id.purchase_order_id.burgtec_purchase_reference} is Confirmed.\n\nMake sure Child Purchase Orders of {record.delivery_stage_id.purchase_order_id.burgtec_purchase_reference} are Confirmed.\n\nChild Purchase Order's whose Pickings are already validated will not be shown here!."""))

            # Filter out child POs whose all pickings are already validated
            child_purchase_orders = child_purchase_orders.filtered(
                lambda po: not all(
                    picking.state == 'done'
                    for picking in po.picking_ids
                )
            )
            line_vals = []
            move = False
            seq = 10
            for po in child_purchase_orders:
                line_vals.append((0, 0, {
                        'display_type': 'line_section',
                        'name': po.burgtec_purchase_reference,
                        'sale_order_id': record.delivery_stage_id.id,
                        'purchase_order_id': po.id,
                        'sequence': seq,
                    }))
                seq += 1
                purchase_lines = po.order_line.filtered(lambda l:not l.product_id.is_delivery_and_installation and l.product_id.type != 'service')
                for line in purchase_lines:
                    # if line.move_ids:
                    #     move = line.move_ids.filtered(lambda m:m.state not in ['cancel','done'])
                    line_vals.append((0, 0, {
                        'sale_order_id': record.delivery_stage_id.id,
                        'component_id': line.product_id.id,
                        'purchase_order_id': po.id,
                        # 'picking_ids': po.picking_ids.filtered(lambda p:p.state not in ['cancel','done']),
                        'picking_id': po.picking_ids.filtered(lambda p:p.state not in ['cancel','done'])[0].id,
                        'product_uom_qty': line.product_uom_qty - line.qty_received,
                        'date_planned': line.date_planned, 
                        # 'stock_move_id': move.id if move else False,
                        'purchase_order_line_id': line.id,
                        'sequence': seq,
                    }))
                    seq += 1

            if line_vals:
                record.backorder_planning_line_ids = line_vals


    
    def create_backorder(self):
        for record in self:
            lines_for_backorder = record.backorder_planning_line_ids.filtered(lambda l: l.is_check)
            if not lines_for_backorder:
                raise UserError(_("No Line is checked to create its Back Order!"))

            # Validate expected quantities first
            for line in lines_for_backorder:
                if line.expected_qty == 0:
                    raise UserError(_("Expected Quantity can't be Zero."))
                if not line.back_order_date_planned:
                    raise UserError(_("Kindly, Set Back Order ETA!"))

            # Group lines by picking
            picking_lines_map = {}
            for line in lines_for_backorder:
                # A line may have multiple pickings — take the relevant one via stock_move_id
                picking = line.stock_move_id.picking_id
                if not picking:
                    raise UserError(_("No picking found for product %s") % line.component_id.name)
                if picking.id not in picking_lines_map:
                    picking_lines_map[picking.id] = {
                        'picking': picking,
                        'lines': []
                    }
                picking_lines_map[picking.id]['lines'].append(line)

            # Process each picking group independently
            for picking_id, data in picking_lines_map.items():
                picking = data['picking']
                grouped_lines = data['lines']

                # Set expected_qty on all moves belonging to this picking's checked lines
                for line in grouped_lines:
                    line.stock_move_id.quantity = line.expected_qty

                # Split this picking once (handles all grouped lines together)
                result = picking.action_custom_split_transfer()

                # Create planned backorder lines for each line in this group
                for line in grouped_lines:
                    if result:
                        result.sudo().write({
                            'date_deadline': line.back_order_date_planned,
                        })
                    planned_vals = {
                        'is_check': line.is_check,
                        'back_order_planning_line_id': line.id,
                        'planning_screen_id': line.planning_screen_id.id,
                        'sale_order_id': line.sale_order_id.id,
                        'component_id': line.component_id.id,
                        'purchase_order_id': line.purchase_order_id.id,
                        'product_uom_qty': line.back_order_qty,
                        'expected_qty': line.back_order_qty,
                        'date_planned': line.back_order_date_planned,
                        'purchase_order_line_id': line.purchase_order_line_id.id,
                        'picking_ids': [(4,result.id,0)],
                    }
                    planned_line_res = self.env['back.order.lines.planned'].sudo().create(planned_vals)
                    line.planned_backorder_line_id = planned_line_res.id

        return True







