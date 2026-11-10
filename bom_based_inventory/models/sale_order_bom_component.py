import logging
import copy
import json

from email.policy import default
from odoo import models, fields, api, _
from odoo.api import readonly
from odoo.exceptions import UserError, AccessError, ValidationError, RedirectWarning

_logger = logging.getLogger(__name__)

sale_state_dict = {
    'draft': 'Draft',
    'sent': 'Quotation Sent',
    'quotation_confirmed': 'Quotation Confirmed',
    'sale': 'Sales Order',
    'cancel': 'Cancelled',
}


class SaleOrderBOMComponent(models.Model):
    _name = 'sale.order.bom.component'
    _description = 'BOM Components for Sale Order'
    _rec_name = 'order_id'

    order_id = fields.Many2one('sale.order', string='Sale Order', required=True, ondelete='cascade')
    state = fields.Selection(related='order_id.state')

    component_line_ids = fields.One2many(
        'sale.order.bom.component.line',
        'component_id',
        copy=True
    )
    show_warning = fields.Boolean(string="Show Warning", compute='_compute_show_warning', store=False)
    show_live_percentage_warning = fields.Boolean(
        string="Show Percentage Warning",
        compute='_show_live_percentage_warning',
        store=False
    )
    display_type = fields.Selection([
        ('line_section', "Section"),
    ], string="Display Type")
    name = fields.Char('Product')
    force_compute_trigger = fields.Integer('Force Compute Trigger', default=0)

    view_team = fields.Selection([
        ('sales_team', 'Sales Team'),
        ('preproject_team', 'Pre-projects Team'),
        ('purchasing_team', 'Purchasing Team'),
    ])

    # JSON field for component state - structure: {order_line_id: {product_id: {...state...}}}
    # component_state = fields.Json(string='Component state', default=lambda self: {})
    # component_state = fields.Text(string='Component state', default=lambda self: {})

    component_state_id = fields.Many2one('bom.component.state', copy=False)

    # ----------------------------- Helper Methods ---------------------------------

    def _read_component_state(self) -> dict:
        # """Return a deep copy of the stored state."""
        self.ensure_one()
        if self and not self.component_state_id:
            # -------------------- CREATE STATE MODEL ----------------------------------
            state_record_result = False
            state_record = self.env['bom.component.state'].sudo().search([('order_id','=',self.order_id.id)],limit=1)

            if not state_record:
                state_record_result = self.env['bom.component.state'].sudo().create({
                    # 'bom_component_id':self.id,
                    'order_id':self.order_id.id,
                    'component_state': {}
                }) 
                if state_record_result:
                    self.component_state_id = state_record_result.id
            # res = self.env['bom.component.state'].sudo().create({
            #     'bom_component_id':self.id,
            #     'order_id':self.order_id.id,
            #     'component_state':{}
            # })
            if state_record:
                self.component_state_id = state_record.id
        if self.component_state_id:
            state = self.component_state_id.component_state
            return copy.deepcopy(state or {})

    def _write_component_state(self, state: dict):
        self.ensure_one()
        # Use write directly to avoid triggering unnecessary computations
        if self and not self.component_state_id:
            # -------------------- CREATE STATE MODEL ----------------------------------
            state_record_result = False
            state_record = self.env['bom.component.state'].sudo().search([('order_id','=',self.order_id.id)],limit=1)

            if not state_record:
                state_record_result = self.env['bom.component.state'].sudo().create({
                    # 'bom_component_id':self.id,
                    'order_id':self.order_id.id,
                    'component_state': {}
                })
                if state_record_result: 
                    self.component_state_id = state_record_result.id
            # res = self.env['bom.component.state'].sudo().create({
            #     'bom_component_id':self.id,
            #     'order_id':self.order_id.id,
            #     'component_state':{}
            # })
            if state_record:
                self.component_state_id = state_record.id
        if self.component_state_id:
            self.component_state_id.sudo().write({'component_state': state})

    def _get_product_state(self, order_line_id: int, product_id: int, state_dict: dict = None) -> dict:
        if state_dict is None:
            state_dict = self._read_component_state() if self else {}
        
       
        line_key = str(order_line_id)
        prod_key = str(product_id)
        
        line_st = state_dict.setdefault(line_key, {})
        prod_st = line_st.setdefault(prod_key, {})
        
        return prod_st

    def _batch_update_state(self, updates: list):
        self.ensure_one()
        state = self._read_component_state()
        
        for order_line_id, product_id, updater in updates:
            line_key = str(order_line_id)
            prod_key = str(product_id)
            
            line_state = state.setdefault(line_key, {})
            product_state = line_state.setdefault(prod_key, {})
            
            # Call updater
            updater(product_state)
        
        # Single write for all updates
        self._write_component_state(state)

    def _update_product_state(self, order_line_id: int, product_id: int, updater, create=True):
        self.ensure_one()
        
        state = self._read_component_state()
        
        line_key = str(order_line_id)
        prod_key = str(product_id)
        
        line_state = state.setdefault(line_key, {})
        
        if not create and prod_key not in line_state:
            return None
            
        product_state = line_state.setdefault(prod_key, {})
        
        # Call the updater function with the product state
        result = updater(product_state)
        
        # Persist the mutated state back to the DB field
        self._write_component_state(state)
        
        return result

    # ----------------------------- Helper Methods ---------------------------------

    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.order_id.id,
            'target': 'current',
        }

    @api.depends('component_line_ids.product_qty', 'component_line_ids.live_unit_cost',
                 'component_line_ids.manual_live_unit_cost', 'component_line_ids.total_sale_price')
    def _show_live_percentage_warning(self):
        for record in self:
            show_warning = False
            parent_line = record.component_line_ids.filtered(lambda l: l.is_parent)
            
            if parent_line:
                for parent in parent_line:
                    total_sale_price = parent.total_sale_price or 0.0
                    live_unit_cost = parent.live_unit_cost or 0.0

                    if total_sale_price:
                        margin_live_cost = (total_sale_price - live_unit_cost) / total_sale_price
                        margin_live_percentage = margin_live_cost * 100
                        
                        if margin_live_percentage <= 0.0 or margin_live_percentage >= 100.0:
                            show_warning = True
                            break
                    else:
                        show_warning = True
                        break

            record.show_live_percentage_warning = show_warning

    @api.depends('component_line_ids.product_id',
                 'component_line_ids.display_type',
                 'component_line_ids.is_auto_generated')
    def _compute_show_warning(self):
        for comp in self:
            component_lines = comp.component_line_ids.filtered(
                lambda l: l.display_type != 'line_section'
            )
            comp.show_warning = any(
                line.product_id and not line.is_auto_generated
                for line in component_lines
            )

    def _compute_component_quantities(self, parent):
        """Optimized to read state once and write once"""
        for record in self:
            lines = record.component_line_ids
            if not lines:
                continue

            parent_line = parent
            child_lines = lines.filtered(
                lambda l: l.parent_product_id == parent.product_id.product_tmpl_id 
                and l.order_line_id == parent.order_line_id
            )
            
            if not parent_line:
                continue

            parent_qty = parent_line.product_qty

            # Read state ONCE at the beginning
            state = self._read_component_state()
            state_modified = False

            for component_line in child_lines:
                # Get product state from the already-read state dict
                prod_state = self._get_product_state(
                    parent_line.order_line_id.id, 
                    component_line.product_id.id, 
                    state
                )

                # Check if we have a stored proportion factor
                proportion_factor = prod_state.get('proportion_factor', None)

                if proportion_factor is not None:
                    # Use stored proportion factor
                    live_cost_per_unit = (component_line.live_unit_cost / component_line.product_qty 
                                         if component_line.product_qty > 0 else 0)
                    quoted_cost_per_unit = (component_line.quoted_cost_per_unit / component_line.product_qty 
                                           if component_line.product_qty > 0 else 0)
                    pre_project_cost_per_unit = (component_line.pre_project_cost_per_unit / component_line.product_qty 
                                                if component_line.product_qty > 0 else 0)

                    # Calculate new quantity using proportion
                    new_qty = parent_qty * proportion_factor
                    component_line.product_qty = new_qty

                    # Update costs
                    component_line.live_unit_cost = (new_qty * live_cost_per_unit 
                                                    if live_cost_per_unit 
                                                    else new_qty * component_line.manual_live_unit_cost)
                    component_line.quoted_cost_per_unit = new_qty * quoted_cost_per_unit
                    component_line.pre_project_cost_per_unit = new_qty * pre_project_cost_per_unit
                    component_line.system_cost_per_unit = new_qty * component_line.product_id.standard_price

                else:
                    # Handle skip flags and update state
                    prod_state.setdefault('live_unit_cost',
                                   component_line.live_unit_cost or component_line.product_id.standard_price)

                    if prod_state.get('skip_product_qty', False):
                        prod_state['skip_product_qty'] = False
                        state_modified = True
                        continue
                        
                    component_line.product_qty = prod_state.get('product_qty', 1) * parent_qty
                    component_line.system_cost_per_unit = component_line.product_qty * component_line.product_id.standard_price

                    if prod_state.get('skip_pre_project_cost_per_unit', False):
                        prod_state['skip_pre_project_cost_per_unit'] = False
                        state_modified = True
                        continue
                        
                    pre_project_cost_per_unit = prod_state.get('pre_project_cost_per_unit', 0)
                    component_line.pre_project_cost_per_unit = pre_project_cost_per_unit * component_line.product_qty

                    if prod_state.get('skip_quoted_cost_per_unit', False):
                        prod_state['skip_quoted_cost_per_unit'] = False
                        state_modified = True
                        continue
                        
                    quoted_cost_per_unit = prod_state.get('quoted_cost_per_unit', 0)
                    component_line.quoted_cost_per_unit = quoted_cost_per_unit * component_line.product_qty

                    if prod_state.get('skip_live_unit_cost', False):
                        prod_state['skip_live_unit_cost'] = False
                        state_modified = True
                        continue
                        
                    component_line.live_unit_cost = component_line.manual_live_unit_cost * component_line.product_qty

            # Write state ONCE at the end if modified
            if state_modified:
                self._write_component_state(state)

    @api.onchange('component_line_ids')
    def onchange_component_line_ids(self):
        sequence_val = False
        order_line_val = False
        parent_product = False

        for record in self:
            component_lines = record.component_line_ids
            if component_lines:
                for line in component_lines.sorted(lambda o: o.sequence):
                    if line.display_type == 'line_section':
                        if not sequence_val:
                            sequence_val = line.sequence
                            order_line_val = line.order_line_id.id
                        else:
                            sequence_val += 1
                            line.sequence = sequence_val
                            order_line_val = line.order_line_id.id
                            
                    if line.is_parent:
                        parent_product = line.product_id.product_tmpl_id.id
                        sequence_val = sequence_val + 1
                        line.sequence = sequence_val
                        order_line_val = line.order_line_id.id
                        
                    if not line.display_type and not line.is_parent:
                        sequence_val = sequence_val + 1
                        line.sequence = sequence_val
                        line.parent_product_id = parent_product
                        line.order_line_id = order_line_val
                        
            parent_line = component_lines.filtered(lambda l: l.is_parent)
            if not parent_line:
                return
                
            for parent in parent_line:
                if parent.current_change:
                    parent.current_change = False
                    self._compute_component_quantities(parent)
                    
                child_lines = component_lines.filtered(
                    lambda l: l.parent_product_id == parent.product_id.product_tmpl_id 
                    and l.order_line_id == parent.order_line_id
                )
                
                parent.pre_project_cost_per_unit = sum(line.pre_project_cost_per_unit for line in child_lines)
                parent.system_cost_per_unit = sum(line.system_cost_per_unit for line in child_lines)
                parent.quoted_cost_per_unit = sum(line.quoted_cost_per_unit for line in child_lines)
                parent.live_unit_cost = sum(line.live_unit_cost for line in child_lines)
                parent.manual_live_unit_cost = sum(line.manual_live_unit_cost for line in child_lines)
            
            # BATCH UPDATE: Collect all state updates and do ONE write
            updates = []
            for parent in parent_line:
                child_lines = component_lines.filtered(
                    lambda l: l.parent_product_id == parent.product_id.product_tmpl_id 
                    and l.order_line_id == parent.order_line_id
                )
                
                for line in child_lines:
                    if line.product_id:
                        multiply_qty = line.product_qty
                        new_proportion = multiply_qty / parent.product_qty if parent.product_qty > 0 else 0.0
                        
                        def make_updater(prop):
                            def _updater(s):
                                s['proportion_factor'] = prop
                                s['custom_proportion'] = True
                            return _updater
                        
                        updates.append((
                            line.order_line_id.id,
                            line.product_id.id,
                            make_updater(new_proportion)
                        ))
            
         
            if updates:
                self._batch_update_state(updates)

    def _update_bom_line_component_sequence(self):
        seq = 11
        for line in self.component_line_ids.sorted('sequence'):
            line.sequence = seq
            seq += 1

    def _compute_cost_margin(self):
        for record in self:
            parent_product_total_sale_price = 0.0
            total_system_cost = 0.0
            total_live_cost = 0.0
            total_quoted_cost = 0.0
            total_pre_project_cost = 0.0
            total_margin_system_cost = 0.0
            total_margin_quoted_cost = 0.0
            total_margin_pre_project_cost = 0.0
            total_margin_live_cost = 0.0
            sale_order = record.order_id
            component_lines = record.component_line_ids
            sale_order_lines = record.order_id.order_line
            
            for line in component_lines:
                if line.is_parent:
                    parent_product_total_sale_price += line.total_sale_price
                if line.system_cost_per_unit and not line.is_parent:
                    total_system_cost += line.system_cost_per_unit
                if line.live_unit_cost and not line.is_parent:
                    total_live_cost += line.live_unit_cost
                if line.quoted_cost_per_unit and not line.is_parent:
                    total_quoted_cost += line.quoted_cost_per_unit
                if line.pre_project_cost_per_unit and not line.is_parent:
                    total_pre_project_cost += line.pre_project_cost_per_unit
                # New Margin fields total for Parents
                if line.system_cost_per_unit and line.is_parent:
                    total_margin_system_cost += line.system_cost_per_unit
                if line.quoted_cost_per_unit and line.is_parent:
                    total_margin_quoted_cost += line.quoted_cost_per_unit
                if line.pre_project_cost_per_unit and line.is_parent:
                    total_margin_pre_project_cost += line.pre_project_cost_per_unit
                if line.live_unit_cost and line.is_parent:
                    total_margin_live_cost += line.live_unit_cost
                    
            if sale_order:
                sale_order.write({
                    'system_cost_per_unit': parent_product_total_sale_price - total_margin_system_cost,
                    'live_unit_cost': parent_product_total_sale_price - total_margin_live_cost,
                    'quoted_cost_per_unit': parent_product_total_sale_price - total_margin_quoted_cost,
                    'pre_project_cost_per_unit': parent_product_total_sale_price - total_margin_pre_project_cost,
                    'system_cost_bom_total': total_system_cost,
                    'live_cost_bom_total': total_live_cost,
                    'quoted_cost_bom_total': total_quoted_cost,
                    'pre_project_cost_bom_total': total_pre_project_cost,

                    # Markup Fields
                    "percentage_markup_system_cost": (
                        (parent_product_total_sale_price - total_margin_system_cost) / total_margin_system_cost
                        if total_margin_system_cost else 0.0),
                    "percentage_markup_live_cost": (
                        (parent_product_total_sale_price - total_margin_live_cost) / total_margin_live_cost
                        if total_margin_live_cost else 0.0),
                    "percentage_markup_quoted_cost": (
                        (parent_product_total_sale_price - total_margin_quoted_cost) / total_margin_quoted_cost
                        if total_margin_quoted_cost else 0.0),
                    "percentage_markup_pre_project_cost": (
                        (parent_product_total_sale_price - total_margin_pre_project_cost) / total_margin_pre_project_cost
                        if total_margin_pre_project_cost else 0.0),
                    # Margin Fields
                    "percentage_margin_system_cost": (
                        (parent_product_total_sale_price - total_margin_system_cost) / parent_product_total_sale_price
                        if parent_product_total_sale_price else 0.0
                    ),
                    "percentage_margin_live_cost": (
                        (parent_product_total_sale_price - total_margin_live_cost) / parent_product_total_sale_price
                        if parent_product_total_sale_price else 0.0
                    ),
                    "percentage_margin_quoted_cost": (
                        (parent_product_total_sale_price - total_margin_quoted_cost) / parent_product_total_sale_price
                        if parent_product_total_sale_price else 0.0
                    ),
                    "percentage_margin_pre_project_cost": (
                        (parent_product_total_sale_price - total_margin_pre_project_cost) / parent_product_total_sale_price
                        if parent_product_total_sale_price else 0.0
                    )
                })
                
        filtered_sale_order_lines = sale_order_lines.filtered(lambda l: l.product_id)
        for line in filtered_sale_order_lines:
            matching_bom_line = component_lines.filtered(
                lambda l: l.order_line_id.id == line.id and l.is_parent and l.product_id.id == line.product_id.id)
            if matching_bom_line:
                line.write({
                    'product_uom_qty': matching_bom_line.product_qty,
                    'price_unit': matching_bom_line.unit_sale_price,
                })

    @api.model_create_multi
    def create(self, vals_list):
            res = super(SaleOrderBOMComponent, self).create(vals_list)
            model = self.env.context.get('active_model')
            active_id = self.env.context.get('active_id')
            if model == 'sale.order':
                sale_order = self.env[model].browse(active_id)
                sale_order.bom_component_id = res.id
            return res
        # if self.env.context.get('auto_create_bom'):
        #     res = super(SaleOrderBOMComponent, self).create(vals_list)
        #     # res._compute_cost_margin()
        #     return res
        # else:
        #     res = super(SaleOrderBOMComponent, self).create(vals_list)
        #     model = self.env.context.get('active_model')
        #     active_id = self.env.context.get('active_id')
        #     if model == 'sale.order':
        #         sale_order = self.env[model].browse(active_id)
        #         sale_order.bom_component_id = res.id
        #     # res._compute_cost_margin()
        #     return res

    def web_save(self, vals, specification: dict[str, dict], next_id=None) -> list[dict]:
        if self:
            if self.order_id.state not in ('draft'):
                if not self.env.user.has_group("sales_team.group_sale_manager"):
                    raise AccessError(
                        _(f"Only Sales Administrator can edit a Sale Quotation in '{sale_state_dict[self.order_id.state]}' State"))
        return super(SaleOrderBOMComponent, self).web_save(vals, specification)



    def get_product_suppiler(self, product_id):
        if product_id.seller_ids:
            return product_id.seller_ids[0].partner_id.id
        return False

    def update_component_lines(self):
        _logger.info("------------------    UPDATE COMPONENT LINES EXECUTED  -------------------------")
        self.ensure_one()
        sale_order = self.order_id
        sale_order_line = sale_order.order_line
        component_lines = self.component_line_ids
        parent_component_lines = component_lines.filtered(lambda l: l.is_parent)

        already_added_pairs = set(
            (line.product_id.id, line.order_line_id.id)
            for line in parent_component_lines
        )

        seq = max(component_lines.mapped('sequence') or [0]) + 1
        set_seq = 10

        # Collect all state updates to batch them
        batch_updates = []
        
        # Collect new records to create in batch
        new_records_vals = []

        filtered_sale_order_lines = sale_order_line.sorted(lambda o: o.sequence).filtered(lambda l: l.product_id)
        
        for line in filtered_sale_order_lines:
            pair_key = (line.product_id.id, line.id)

            if pair_key in already_added_pairs:
                section_line = component_lines.filtered(
                    lambda s: s.display_type == 'line_section' and s.name == line.product_id.name and s.line_id == line.id
                )
                
                parent_line = component_lines.filtered(
                    lambda l: l.is_parent and l.product_id.id == line.product_id.id and l.order_line_id.id == line.id
                )

                if section_line:
                    section_line.write({'sequence': set_seq})
                    set_seq += 1
                    
                if parent_line:
                    parent_line.write({
                        'product_qty': line.product_uom_qty,
                        'unit_sale_price': line.price_unit,
                        'sequence': set_seq
                    })
                    set_seq += 1

                    tmpl_id = line.product_id.product_tmpl_id.id
                    child_lines = component_lines.filtered(
                        lambda l: not l.is_parent and
                        l.parent_product_id.id == tmpl_id and
                        l.order_line_id.id == line.id
                    )
                    
                    for child in child_lines:
                        child.sequence = set_seq
                        set_seq += 1
                        
                        if line.product_uom_qty > 0:
                            proportion = child.product_qty / line.product_uom_qty if line.product_uom_qty else 0.0
                            
                            def make_child_updater(c, prop):
                                def _updater(s):
                                    s['proportion_factor'] = prop
                                    s['live_unit_cost'] = c.live_unit_cost / c.product_qty if c.product_qty else 0.0
                                    s['quoted_cost_per_unit'] = c.quoted_cost_per_unit / c.product_qty if c.product_qty else 0.0
                                    s['pre_project_cost_per_unit'] = c.pre_project_cost_per_unit / c.product_qty if c.product_qty else 0.0
                                    s['custom_proportion'] = True
                                return _updater
                            
                            batch_updates.append((
                                line.id,
                                child.product_id.id,
                                make_child_updater(child, proportion)
                            ))
                continue

            # Collect Section line values
            new_records_vals.append({
                'component_id':self.id,
                'display_type': 'line_section',
                'name': line.product_id.name,
                'sequence': set_seq,
                'order_line_id': line.id,
            })
            seq += 1
            set_seq += 1

            # Collect Parent line values
            new_records_vals.append({
                'component_id':self.id,
                'is_parent': True,
                'product_id': line.product_id.id,
                'product_name': line.custom_product_name,
                'parent_product_code': line.line_section_name,
                'product_qty': line.product_uom_qty,
                'unit_sale_price': line.price_unit,
                'live_unit_cost': 0.0,
                'system_cost_per_unit': 0.0,
                'is_auto_generated': True,
                'supplier_id': self.get_product_suppiler(line.product_id),
                'sequence': set_seq,
                'order_line_id': line.id,
            })
            seq += 1
            set_seq += 1

            # Collect BOM lines (children) values
            bom_dict = self.env['mrp.bom']._bom_find(line.product_id)
            bom = bom_dict.get(line.product_id)
            
            if bom:
                for bom_line in bom.bom_line_ids:
                    multiply_qty = bom_line.product_qty * line.product_uom_qty
                    proportion = bom_line.product_qty

                    def make_bom_updater(bl_prod_price, prop):
                        def _updater(s):
                            s['proportion_factor'] = prop
                            s['custom_proportion'] = False
                            s.setdefault('live_unit_cost', bl_prod_price)
                            s.setdefault('pre_project_cost_per_unit', 0)
                            s.setdefault('quoted_cost_per_unit', 0)
                        return _updater

                    batch_updates.append((
                        line.id,
                        bom_line.product_id.id,
                        make_bom_updater(bom_line.product_id.standard_price, proportion)
                    ))

                    new_records_vals.append({
                        'component_id':self.id,
                        'is_parent': False,
                        'is_new_bom_line': True,
                        'parent_product_id': line.product_id.product_tmpl_id.id,
                        'product_id': bom_line.product_id.id,
                        'product_qty': multiply_qty,
                        'system_cost_per_unit': multiply_qty * bom_line.product_id.standard_price,
                        'live_unit_cost': multiply_qty * bom_line.product_id.standard_price,
                        'manual_live_unit_cost': bom_line.product_id.standard_price,
                        'is_auto_generated': True,
                        'supplier_id': self.get_product_suppiler(bom_line.product_id),
                        'sequence': set_seq,
                        'order_line_id': line.id,
                    })
                    seq += 1
                    set_seq += 1
        if new_records_vals:
            self.env['sale.order.bom.component.line'].sudo().create(new_records_vals)
            _logger.info(" ----------------------   SALE ORDER BOM COMPONENT LINE CREATED  ----------------------- ")
            # _logger.info(new_records_vals)

        if batch_updates:
            self._batch_update_state(batch_updates)

        # Refresh component_lines to include newly created records
        component_lines = self.component_line_ids
        parent_lines = component_lines.sorted(lambda o: o.sequence).filtered(lambda l: l.is_parent)
        parent_number = 1
        for parent_line in parent_lines:
            parent_line.write({'parent_number': parent_number})
            parent_number += 1

        # Final trigger
        self.onchange_component_line_ids()
        self.write({
            'force_compute_trigger': self.force_compute_trigger + 1
        })

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderBOMComponent, self).default_get(fields)
        context = self.env.context
        order_id = context.get('default_order_id')
        
        if not order_id:
            return res
            
        sale_order = self.env['sale.order'].browse(order_id)
        sale_order_line = sale_order.order_line
        
        if not sale_order_line:
            raise UserError(_("No products in the order to show components."))
            
        component_lines = []
        seq = 11
        parent_number = 0
        
        # Build initial component state - batch all state in memory
        initial_state = {}
        
        for line in sale_order_line:
            if line.product_id:
                component_lines.append((0, 0, {
                    'display_type': 'line_section',
                    'name': line.product_id.name,
                    'sequence': seq,
                    'order_line_id': line.id
                }))
                seq += 1
                parent_number += 1

                # Add the parent product line
                component_lines.append((0, 0, {
                    'is_parent': True,
                    'order_line_id': line.id,
                    'parent_product_code': line.line_section_name,
                    'parent_number': parent_number,
                    'product_id': line.product_id.id,
                    'product_name': line.custom_product_name,
                    'product_qty': line.product_uom_qty,
                    'unit_sale_price': line.price_unit,
                    'live_unit_cost': 0.0,
                    'system_cost_per_unit': 0.0,
                    'is_auto_generated': True,
                    'supplier_id': self.get_product_suppiler(line.product_id),
                    'sequence': seq,
                }))
                seq += 1

                # Process BOM components
                bom_dict = self.env['mrp.bom']._bom_find(line.product_id)
                bom = bom_dict.get(line.product_id)
                bom_lines_ids = bom.bom_line_ids if bom else self.env['mrp.bom.line']
                
                if bom:
                    # Initialize line state in initial_state dict
                    line_key = str(line.id)
                    if line_key not in initial_state:
                        initial_state[line_key] = {}
                    
                    for bom_line in bom_lines_ids:
                        multiply_qty = bom_line.product_qty * line.product_uom_qty
                        new_proportion = bom_line.product_qty
                        
                        # Store state in initial_state dict
                        prod_key = str(bom_line.product_id.id)
                        initial_state[line_key][prod_key] = {
                            'live_unit_cost': bom_line.product_id.standard_price,
                            'pre_project_cost_per_unit': 0,
                            'quoted_cost_per_unit': 0,
                            'proportion_factor': new_proportion,
                            'custom_proportion': True,
                        }
                        
                        component_lines.append((0, 0, {
                            'is_parent': False,
                            'is_new_bom_line': True,
                            'order_line_id': line.id,
                            'parent_product_id': line.product_id.product_tmpl_id.id,
                            'product_id': bom_line.product_id.id,
                            'product_qty': multiply_qty,
                            'system_cost_per_unit': multiply_qty * bom_line.product_id.standard_price,
                            'live_unit_cost': multiply_qty * bom_line.product_id.standard_price,
                            'manual_live_unit_cost': bom_line.product_id.standard_price,
                            'is_auto_generated': True,
                            'supplier_id': self.get_product_suppiler(bom_line.product_id),
                            'sequence': seq,
                        }))
                        seq += 1

        if not component_lines:
            raise UserError(_("No Bill of Materials found for the products in this order."))
        
        # -------------------- CREATE STATE MODEL ----------------------------------
        state_record_result = False
        component_state_id = False
        state_record = self.env['bom.component.state'].sudo().search([('order_id','=',order_id)],limit=1)

        if not state_record:
            state_record_result = self.env['bom.component.state'].sudo().create({
                'order_id':order_id,
                'component_state': initial_state
            })
            component_state_id = state_record_result.id
        if state_record:
            component_state_id = state_record.id  
        res.update({
            'order_id': order_id,
            'component_line_ids': component_lines,
            'component_state_id': component_state_id
        })
        return res

    def action_fetch_live_cost(self):
        
        context = self.env.context
        order_id = context.get('default_order_id')
        bom_id = context.get('bom_id')
        
        batch_updates = []
        
        for line in self.component_line_ids:
            if line.product_id and not line.is_parent:
                def make_updater(prod_price):
                    def _updater(s):
                        s['live_unit_cost'] = prod_price
                    return _updater
                
                batch_updates.append((
                    line.order_line_id.id,
                    line.product_id.id,
                    make_updater(line.product_id.standard_price)
                ))
                line.live_unit_cost = line.product_qty * line.product_id.standard_price
        
        if batch_updates:
            self._batch_update_state(batch_updates)
                
        parent_lines = self.component_line_ids.filtered(lambda p: p.is_parent)
        for p_line in parent_lines:
            all_child_without_sequence_lines = self.component_line_ids.filtered(
                lambda p: not p.is_parent
            ).filtered(lambda l: l.product_id and l.parent_product_id)
            
            p_line.live_unit_cost = sum(
                all_child_without_sequence_lines.filtered(
                    lambda l: l.parent_product_id.id == p_line.product_id.product_tmpl_id.id 
                    and l.order_line_id.id == p_line.order_line_id.id
                ).mapped('live_unit_cost')
            )
            
        self.write({
            'force_compute_trigger': self.force_compute_trigger + 1
        })

        return {
            'name': _('BOM Components'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.bom.component',
            'res_id': self.id or False,
            'view_mode': 'form',
            'view_id': self.env.ref('bom_based_inventory.view_sale_order_bom_components_form').id,
            'target': 'new',
            'context': {
                'active_model': 'sale.order',
                'active_id': order_id,
                'default_order_id': order_id,
                'bom_id': bom_id,
            }
        }

    def action_quoted_cost(self):
        
        context = self.env.context
        order_id = context.get('default_order_id')
        bom_id = context.get('bom_id')
        
        batch_updates = []
        
        for line in self.component_line_ids:
            if line.product_id and not line.is_parent:
                def make_updater(live_cost, prod_qty):
                    def _updater(s):
                        s['quoted_cost_per_unit'] = live_cost / prod_qty if prod_qty else 0.0
                    return _updater
                
                batch_updates.append((
                    line.order_line_id.id,
                    line.product_id.id,
                    make_updater(line.live_unit_cost, line.product_qty)
                ))
                line.quoted_cost_per_unit = line.live_unit_cost
        
        
        if batch_updates:
            self._batch_update_state(batch_updates)
                
        parent_lines = self.component_line_ids.filtered(lambda p: p.is_parent)
        for p_line in parent_lines:
            all_child_without_sequence_lines = self.component_line_ids.filtered(
                lambda p: not p.is_parent
            ).filtered(lambda l: l.product_id and l.parent_product_id)
            
            p_line.quoted_cost_per_unit = sum(
                all_child_without_sequence_lines.filtered(
                    lambda l: l.parent_product_id.id == p_line.product_id.product_tmpl_id.id 
                    and l.order_line_id.id == p_line.order_line_id.id
                ).mapped('quoted_cost_per_unit')
            )
            
        self.write({
            'force_compute_trigger': self.force_compute_trigger + 1
        })
        return True

    def action_fetch_pre_project_cost(self):
        
        context = self.env.context
        order_id = context.get('default_order_id')
        bom_id = context.get('bom_id')
        
        batch_updates = []
        
        for line in self.component_line_ids:
            if line.product_id and not line.is_parent:
                def make_updater(live_cost, prod_qty):
                    def _updater(s):
                        s['pre_project_cost_per_unit'] = live_cost / prod_qty if prod_qty else 0.0
                    return _updater
                
                batch_updates.append((
                    line.order_line_id.id,
                    line.product_id.id,
                    make_updater(line.live_unit_cost, line.product_qty)
                ))
                line.pre_project_cost_per_unit = line.live_unit_cost
        
        
        if batch_updates:
            self._batch_update_state(batch_updates)
                
        parent_lines = self.component_line_ids.filtered(lambda p: p.is_parent)
        for p_line in parent_lines:
            all_child_without_sequence_lines = self.component_line_ids.filtered(
                lambda p: not p.is_parent
            ).filtered(lambda l: l.product_id and l.parent_product_id)
            
            p_line.pre_project_cost_per_unit = sum(
                all_child_without_sequence_lines.filtered(
                    lambda l: l.parent_product_id.id == p_line.product_id.product_tmpl_id.id 
                    and l.order_line_id.id == p_line.order_line_id.id
                ).mapped('pre_project_cost_per_unit')
            )
            
        self.write({
            'force_compute_trigger': self.force_compute_trigger + 1
        })
        return True


class SaleOrderBOMComponentLine(models.Model):
    _name = 'sale.order.bom.component.line'
    _description = 'BOM Component Line'

    component_id = fields.Many2one('sale.order.bom.component', string='Components', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product',
        string='Component',
        domain="[('product_tmpl_id.product_bom_type', '=', 'components')]"
    )
    order_line_id = fields.Many2one('sale.order.line', ondelete='cascade')
    line_id = fields.Integer(related="order_line_id.id", string="Order Line Id")
    parent_number = fields.Integer('Parent Serial Number')
    parent_product_id = fields.Many2one('product.template', string='Parent Product')
    product_qty = fields.Float(string='Quantity', digits='Product Quantity', default=1)
    update_qty = fields.Float(string='Update Quantity')
    unit_sale_price = fields.Float(string='Unit Sale Price', readonly=True, default=False)
    total_sale_price = fields.Float(string="Total Sale Price", compute='_compute_total_sale_price', store=True)
    product_reference = fields.Char(string='Product Reference', related='product_id.default_code')
    parent_product_reference = fields.Char('Parent Product Reference')
    live_unit_cost = fields.Float(string='Total Live Cost')
    manual_live_unit_cost = fields.Float(string='Live Unit Cost')
    system_cost_per_unit = fields.Float(string='System Cost per Unit')
    quoted_cost_per_unit = fields.Float(string='Quoted Cost per Unit')
    pre_project_cost_per_unit = fields.Float(string='Pre-Project Cost per Unit')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    is_parent = fields.Boolean(string="Is Parent")
    current_change = fields.Boolean()
    note = fields.Text('Note')
    is_auto_generated = fields.Boolean(
        string="Auto-Generated",
        default=False,
        help="Technical field to identify lines created automatically"
    )
    is_readonly = fields.Boolean(
        string="Readonly",
        compute='_compute_is_readonly',
        help="Technical field to control readonly in views"
    )
    display_type = fields.Selection([
        ('line_section', "Section"),
    ], string="Display Type")
    name = fields.Char('')
    sequence = fields.Integer("Sequence")

    # Fields on Bom Component Screen for Margin
    margin_system_cost = fields.Float(string='Margin System Cost')
    margin_quoted_cost = fields.Float(string='Margin Quoted Cost')
    margin_pre_project_cost = fields.Float(string='Margin Pre-Project Cost')
    margin_live_cost = fields.Float(string='Margin Live Cost')

    # These fields are to show % margin and markup for each parent line on bom component screen
    margin_system_cost_per_parent = fields.Float(
        string='Percentage Margin System Cost',
        compute='_compute_margins_and_markups'
    )
    margin_quoted_cost_per_parent = fields.Float(string='Percentage Margin Quoted Cost')
    margin_pre_project_cost_per_parent = fields.Float(string='Percentage Margin Pre-Project Cost')
    margin_live_cost_per_parent = fields.Float(string='Percentage Margin Live Cost')

    markup_system_cost_per_parent = fields.Float(string='Percentage Markup System Cost')
    markup_quoted_cost_per_parent = fields.Float(string='Percentage Markup Quoted Cost')
    markup_pre_project_cost_per_parent = fields.Float(string='Percentage Markup Pre-Project Cost')
    markup_live_cost_per_parent = fields.Float(string='Percentage Markup Live Cost')

    check_move = fields.Integer()
    is_other_than_bom = fields.Boolean(default=False, store=True)
    is_new_bom_line = fields.Boolean(default=True, store=True)
    base_qty_per_parent = fields.Float(
        string='Base Quantity per Parent Unit',
        default=1.0,
        help="Base quantity of this component per unit of parent product"
    )
    parent_product_code = fields.Char('Product Code', related='order_line_id.line_section_name')
    product_name = fields.Char('Product Name')

    def action_open_add_components_wizard(self):
        """Open wizard to add components for this parent line"""
        if self.component_id.state == 'sale':
            raise UserError(_("You are not allowed to add components for Confirmed Sale Quotations!"))

        if self.component_id.order_id.state not in ('draft') and not self.env.user.has_group(
                'sales_team.group_sale_manager'):
            raise AccessError(
                _(f"Only Sale's Administrator Can Add New Components When The Sale Order In {sale_state_dict[self.component_id.order_id.state]} State"))
                
        if not self.is_parent:
            return

        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Components',
            'res_model': 'bom.component.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_component_id': self.component_id.id if self.component_id else False,
                'active_id': self.id,
                'active_model': 'sale.order.bom.component.line',
                'parent_line_seq': self.product_id.sequence,
                'parent_line_id': self.id,
                'dialog_size': 'extra-large',
            }
        }

    @api.onchange('manual_live_unit_cost', 'product_qty')
    def onchange_manual_unit_cost(self):
        for line in self:
            if not line.manual_live_unit_cost:
                line.live_unit_cost = 0.0
            if line.manual_live_unit_cost:
                line.live_unit_cost = line.manual_live_unit_cost


    @api.depends('product_qty', 'unit_sale_price', 'system_cost_per_unit', 'quoted_cost_per_unit',
                 'pre_project_cost_per_unit', 'live_unit_cost')
    def _compute_margins_and_markups(self):
        for rec in self:
            total_price = rec.total_sale_price or 0.0
            system_cost = rec.system_cost_per_unit or 0.0
            quoted_cost = rec.quoted_cost_per_unit or 0.0
            pre_project_cost = rec.pre_project_cost_per_unit or 0.0
            live_cost = rec.live_unit_cost or 0.0

            # MARGINS (% of selling price)
            rec.margin_pre_project_cost_per_parent = (
                (total_price - pre_project_cost) / total_price
            ) if total_price else 0.0

            rec.margin_live_cost_per_parent = (
                (total_price - live_cost) / total_price
            ) if total_price else 0.0

            rec.margin_system_cost_per_parent = (
                (total_price - system_cost) / total_price
            ) if total_price else 0.0

            rec.margin_quoted_cost_per_parent = (
                (total_price - quoted_cost) / total_price
            ) if total_price else 0.0

            # MARKUPS (% of cost)
            rec.markup_system_cost_per_parent = (
                (total_price - system_cost) / system_cost
            ) if system_cost else 0.0

            rec.markup_quoted_cost_per_parent = (
                (total_price - quoted_cost) / quoted_cost
            ) if quoted_cost else 0.0

            rec.markup_pre_project_cost_per_parent = (
                (total_price - pre_project_cost) / pre_project_cost
            ) if pre_project_cost else 0.0

            rec.markup_live_cost_per_parent = (
                (total_price - live_cost) / live_cost
            ) if live_cost else 0.0

    @api.onchange('sequence')
    def _validation_onchange_sequence(self):
        error_msg = _('You are not allowed to drag lines manually!. Reload the page to proceed further!')
        reload_view = {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        raise RedirectWarning(error_msg, reload_view, _('Reload Page'))

    @api.depends('is_auto_generated')
    def _compute_is_readonly(self):
        for line in self:
            line.is_readonly = line.is_auto_generated

    # def create(self, vals_list):
    #     records = super(SaleOrderBOMComponentLine, self).create(vals_list)
    #     if not self.env.context.get('duplicating_sale_quote'):
    #         for record in records:
    #             if record.component_id:
    #                 record.component_id._compute_cost_margin()
    #     return records

    @api.depends('product_qty', 'unit_sale_price', 'live_unit_cost',
                 'system_cost_per_unit', 'quoted_cost_per_unit',
                 'pre_project_cost_per_unit')
    def _compute_total_sale_price(self):
        for rec in self:
            qty = rec.product_qty or 0.0
            rec.total_sale_price = qty * (rec.unit_sale_price or 0.0)
            total_sale_price = rec.total_sale_price
            
            if rec.is_parent:
                rec.margin_system_cost = total_sale_price - (rec.system_cost_per_unit or 0.0)
                rec.margin_quoted_cost = total_sale_price - (rec.quoted_cost_per_unit or 0.0)
                rec.margin_pre_project_cost = total_sale_price - (rec.pre_project_cost_per_unit or 0.0)
                rec.margin_live_cost = total_sale_price - (rec.live_unit_cost or 0.0)

    @api.onchange('pre_project_cost_per_unit')
    def _compute_pre_project_cost_per_unit(self):
        for rec in self:
            def _updater(s):
                if s.get('skip_pre_project_cost_per_unit', False):
                    s['skip_pre_project_cost_per_unit'] = False
                    return True
                s['pre_project_cost_per_unit'] = rec.pre_project_cost_per_unit
                return False

            skipped = self.component_id._update_product_state(
                self.order_line_id.id, 
                rec.product_id.id, 
                _updater
            )
            
            if skipped:
                continue
                
            rec.pre_project_cost_per_unit = rec.pre_project_cost_per_unit * rec.product_qty

    @api.onchange('product_qty', 'system_cost_per_unit')
    def _compute_system_cost_per_unit(self):
        for rec in self:
            qty = rec.product_qty or 0.0
            rec.system_cost_per_unit = qty * (rec.product_id.standard_price or 0.0)

    @api.onchange('quoted_cost_per_unit')
    def _compute_quoted_cost_per_unit(self):
        for rec in self:
            def _updater(s):
                if s.get('skip_quoted_cost_per_unit', False):
                    s['skip_quoted_cost_per_unit'] = False
                    return True
                s['quoted_cost_per_unit'] = rec.quoted_cost_per_unit
                return False

            skipped = self.component_id._update_product_state(
                self.order_line_id.id, 
                rec.product_id.id, 
                _updater
            )
            
            if skipped:
                continue
                
            rec.quoted_cost_per_unit = rec.quoted_cost_per_unit * rec.product_qty

    @api.onchange('product_id')
    def onchange_product_id(self):
        for rec in self:
            if rec.product_id:
                rec.is_other_than_bom = True
                rec.system_cost_per_unit = rec.product_id.standard_price
                rec.live_unit_cost = rec.product_id.standard_price
                rec.manual_live_unit_cost = rec.product_id.standard_price
                rec.supplier_id = rec.component_id.get_product_suppiler(rec.product_id)
                
                if rec.parent_product_id:
                    rec.order_line_id = rec.component_id.component_line_ids.filtered(
                        lambda l: l.sequence == rec.sequence - 1
                    ).order_line_id
                    
                    rec.product_qty = 1

                    def _updater(s):
                        s['product_qty'] = rec.product_qty
                        s['live_unit_cost'] = rec.product_id.standard_price

                    self.component_id._update_product_state(
                        rec.order_line_id.id, 
                        rec.product_id.id, 
                        _updater
                    )

    @api.onchange('live_unit_cost')
    def _compute_live_unit_cost(self):
        for rec in self:
            def _updater(s):
                if s.get('skip_live_unit_cost', False):
                    s['skip_live_unit_cost'] = False
                    return True
                s['live_unit_cost'] = rec.live_unit_cost
                return False

            skipped = self.component_id._update_product_state(
                rec.order_line_id.id, 
                rec.product_id.id, 
                _updater
            )
            
            if skipped:
                continue
                
            # rec.live_unit_cost = rec.live_unit_cost * rec.product_qty
            rec.live_unit_cost = rec.manual_live_unit_cost * rec.product_qty

    @api.onchange('product_qty')
    def onchange_product_qty(self):
        """Optimized - single state read/write per record"""
        if self.is_parent:
            self.current_change = True

        for rec in self:
            # Read state once at the start
            state = rec.component_id._read_component_state()
            prod_state = rec.component_id._get_product_state(
                rec.order_line_id.id,
                rec.product_id.id,
                state
            )
            
            # Modify state in memory
            prod_state.setdefault('live_unit_cost', rec.live_unit_cost or rec.product_id.standard_price)
            if prod_state.get('live_unit_cost', False) > 0:
                prod_state['skip_live_unit_cost'] = True
            if prod_state.get('quoted_cost_per_unit', False) > 0:
                prod_state['skip_quoted_cost_per_unit'] = True
            if prod_state.get('pre_project_cost_per_unit', False) > 0:
                prod_state['skip_pre_project_cost_per_unit'] = True
            prod_state['product_qty'] = rec.product_qty

            live_unit_cost = prod_state.get('live_unit_cost', False)
            quoted_cost_per_unit = prod_state.get('quoted_cost_per_unit', False)
            pre_project_cost_per_unit = prod_state.get('pre_project_cost_per_unit', False)

            if rec.is_parent and rec._origin.product_qty == 0 and rec.product_qty > 0:
                child_lines = rec.component_id.component_line_ids.filtered(
                    lambda l: l.order_line_id.id == rec.order_line_id.id 
                    and l.parent_product_id.id == rec.product_id.product_tmpl_id.id
                )
                
                bom_dict = self.env['mrp.bom']._bom_find(rec.product_id)
                bom = bom_dict.get(rec.product_id)
                bom_lines = bom.bom_line_ids if bom else self.env['mrp.bom.line']

                for child in child_lines:
                    bom_line = bom_lines.filtered(
                        lambda bl: bl.product_id.product_tmpl_id == child.product_id.product_tmpl_id
                    )
                    
                    if bom_line:
                        proportion = bom_line[0].product_qty / bom.product_qty if bom.product_qty else 1
                        child.product_qty = rec.product_qty * proportion
                        
                        # Update child state in same state dict
                        child_state = rec.component_id._get_product_state(
                            rec.order_line_id.id,
                            child.product_id.id,
                            state
                        )
                        child_state['proportion_factor'] = proportion
                        child_state['custom_proportion'] = False
                    else:
                        child.product_qty = rec.product_qty
                        
                        child_state = rec.component_id._get_product_state(
                            rec.order_line_id.id,
                            child.product_id.id,
                            state
                        )
                        child_state['proportion_factor'] = 1.0
                        child_state['custom_proportion'] = False

            # Handle child component proportion calculation
            if not rec.is_parent:
                parent_line = rec.component_id.component_line_ids.filtered(
                    lambda l: l.order_line_id.id == rec.order_line_id.id and l.is_parent
                )
                
                if parent_line and parent_line.product_qty > 0:
                    new_proportion = rec.product_qty / parent_line.product_qty
                    prod_state['proportion_factor'] = new_proportion
                    prod_state['custom_proportion'] = True

            if not live_unit_cost:
                live_unit_cost = rec.live_unit_cost
                prod_state['live_unit_cost'] = live_unit_cost
                
            if not quoted_cost_per_unit:
                quoted_cost_per_unit = rec.quoted_cost_per_unit
                prod_state['quoted_cost_per_unit'] = quoted_cost_per_unit
                
            if not pre_project_cost_per_unit:
                pre_project_cost_per_unit = rec.pre_project_cost_per_unit
                prod_state['pre_project_cost_per_unit'] = pre_project_cost_per_unit

            rec.live_unit_cost = live_unit_cost * rec.product_qty

            if not rec.is_parent:
                rec.product_qty = rec.product_qty

            rec.quoted_cost_per_unit = quoted_cost_per_unit * rec.product_qty
            rec.pre_project_cost_per_unit = pre_project_cost_per_unit * rec.product_qty
            
            # Write state once at the end
            rec.component_id._write_component_state(state)
    

    # Server action method to fix total live cost when manual live cost is zero
    def set_live_unit_cost_zero(self):
        for record in self:
            record.live_unit_cost = 0.0