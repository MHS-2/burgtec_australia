from email.policy import default

from odoo import fields, models, api, _
import logging
from odoo.exceptions import UserError, AccessError, ValidationError, RedirectWarning

_logger = logging.getLogger(__name__)


class SaleOrderBomComponentExt(models.Model):
    _inherit = 'sale.order.bom.component'

    # Total computed fields for Computation of margins and markups.
    total_parent_product_sale_price = fields.Float(compute='_compute_multi_total_from_bom_lines', store=True)
    total_parent_system_cost_per_unit = fields.Float(compute='_compute_multi_total_from_bom_lines', store=True)
    total_parent_quoted_cost_per_unit = fields.Float(compute='_compute_multi_total_from_bom_lines', store=True)
    total_parent_pre_project_cost_per_unit = fields.Float(compute='_compute_multi_total_from_bom_lines', store=True)
    total_parent_live_unit_cost = fields.Float(compute='_compute_multi_total_from_bom_lines', store=True)

    def _compute_component_quantities(self, parent,child_lines):
        """Optimized to read state once and write once"""
        for record in self:
            # lines = record.component_line_ids
            if not child_lines:
                continue

            parent_line = parent
            # child_lines = lines.filtered(
            #     lambda l: l.parent_product_id == parent.product_id.product_tmpl_id
            #               and l.order_line_id == parent.order_line_id
            # )

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

                    # # Calculate new quantity using proportion
                    # new_qty = parent_qty * proportion_factor
                    # component_line.product_qty = new_qty

                    if parent_qty == 0:
                        component_line.product_qty = component_line.unit_component_quantity
                    if parent_qty > 0:
                        component_line.product_qty = parent_qty * component_line.unit_component_quantity

                    # Update costs
                    component_line.live_unit_cost = component_line.product_qty * component_line.manual_live_unit_cost
                    # component_line.live_unit_cost = (new_qty * live_cost_per_unit
                    #                                  if live_cost_per_unit
                    #                                  else new_qty * component_line.manual_live_unit_cost)
                    # component_line.quoted_cost_per_unit = new_qty * quoted_cost_per_unit
                    component_line.quoted_cost_per_unit = component_line.product_qty * quoted_cost_per_unit
                    # component_line.pre_project_cost_per_unit = new_qty * pre_project_cost_per_unit
                    component_line.pre_project_cost_per_unit = component_line.product_qty * pre_project_cost_per_unit
                    # component_line.system_cost_per_unit = new_qty * component_line.product_id.standard_price
                    component_line.system_cost_per_unit = component_line.product_qty * component_line.product_id.standard_price

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

    def update_component_lines(self,changed_sale_order_lines=False,lines_vals=[],):
        _logger.info("------------------    UPDATE COMPONENT LINES EXECUTED  -------------------------")
        self.ensure_one()
        sale_order = self.order_id
        sale_order_line = False
        new_sale_order_line = False
        parent_component_lines = False
        seq_list = False
        component_lines = self.component_line_ids
        already_added_pairs = False
        new_sale_line_added = False
        original = False
        seq = False
        maximum_seq = False
        next_order_line_seq = False
        next_order_line = False
        parent_section_seq = False
        next_comp_lines = False
        res =False
        section_line = False
        parent_line = False
        if not lines_vals and not changed_sale_order_lines:
            sale_order_line = sale_order.order_line
            sale_order_line = sale_order_line.sorted(lambda o: o.sequence).filtered(lambda l: l.product_id)
            parent_component_lines = component_lines.filtered(lambda l: l.is_parent and l.order_line_id.id in sale_order_line.ids)
            original = True
            already_added_pairs = set(
                (line.product_id.id, line.order_line_id.id)
                for line in parent_component_lines
            )
        if not lines_vals and changed_sale_order_lines:
            sale_order_line = sale_order.order_line
            parent_component_lines = component_lines.filtered(lambda l: l.is_parent and l.order_line_id.id in changed_sale_order_lines)
            sale_order_line = sale_order_line.sorted(lambda o: o.sequence).filtered(lambda l: l.id in changed_sale_order_lines)
            already_added_pairs = set(
                (line.product_id.id, line.order_line_id.id)
                for line in parent_component_lines
            )
        if lines_vals and not changed_sale_order_lines:
            new_sale_line_added = True
            already_added_pairs = False
            sale_order_line = sale_order.order_line.sorted(lambda o: o.sequence)
            seq_list = [item['sequence'] for item in lines_vals]
            maximum_seq = max(seq_list)
            # next_order_line_seq = maximum_seq + 1
            next_order_line = sale_order_line.filtered(lambda sol:sol.product_id and sol.sequence > maximum_seq)
            if not next_order_line:
                seq = max(component_lines.mapped('sequence') or [0]) + 1

            if next_order_line:
                next_order_line = next_order_line[0]
                parent_component_lines = component_lines.filtered(lambda l: l.is_parent and l.order_line_id.id in next_order_line.ids)
                parent_section_seq = parent_component_lines.sequence - 1
                seq = parent_section_seq # Subtracting by one because before parent line, their is a section line for that parent.

            # New Sales Order Lines Added.
            sale_order_line = sale_order_line.filtered(lambda nol:nol.product_id and nol.sequence in seq_list)

            # self.env['sale.order.line'].sudo().search([
            #         ('sequence','in', seq_list),
            #         ('order_id','=',sale_order.id),
            #         ('product_id','!=',False)
            #     ]
            # )




        # already_added_pairs = set(
        #     (line.product_id.id, line.order_line_id.id)
        #     for line in parent_component_lines
        # )


        # if not original:
        #     seq = max(component_lines.mapped('sequence') or [0]) + 1
        if original:
            seq = 10
        set_seq = 10

        # Collect all state updates to batch them
        batch_updates = []

        # Collect new records to create in batch
        new_records_vals = []
        odoo_adjustment_product = self.env.ref('freight_out_assembly_install_feature.product_odoo_adjustment')
        freight_assembly_products = self.env['product.product'].search(
            [('is_freight_or_assembly', '=', True)]
        )

        # filtered_sale_order_lines = sale_order_line.sorted(lambda o: o.sequence).filtered(lambda l: l.product_id)


        for line in sale_order_line:
            if already_added_pairs:    
                pair_key = (line.product_id.id, line.id)
                if pair_key in already_added_pairs:
                    if not original:
                        parent_line = component_lines.filtered(
                            lambda l: l.is_parent and l.product_id.id == line.product_id.id and l.order_line_id.id == line.id
                        )

                        if parent_line:
                            parent_line.write({
                                'product_qty': line.product_uom_qty,
                                'unit_sale_price': line.price_unit,
                            })

                            tmpl_id = line.product_id.product_tmpl_id.id
                            child_lines = component_lines.filtered(
                                lambda l: not l.is_parent and
                                        l.parent_product_id.id == tmpl_id and
                                        l.order_line_id.id == line.id
                            )

                            for child in child_lines:
                                # child.sequence = seq
                                # seq += 1
                                # child.sequence = set_seq
                                # set_seq += 1

                                if line.product_uom_qty > 0:
                                    proportion = child.product_qty / line.product_uom_qty if line.product_uom_qty else 0.0

                                    def make_child_updater(c, prop):
                                        def _updater(s):
                                            s['proportion_factor'] = prop
                                            s['live_unit_cost'] = c.live_unit_cost / c.product_qty if c.product_qty else 0.0
                                            s[
                                                'quoted_cost_per_unit'] = c.quoted_cost_per_unit / c.product_qty if c.product_qty else 0.0
                                            s[
                                                'pre_project_cost_per_unit'] = c.pre_project_cost_per_unit / c.product_qty if c.product_qty else 0.0
                                            s['custom_proportion'] = True

                                        return _updater

                                    batch_updates.append((
                                        line.id,
                                        child.product_id.id,
                                        make_child_updater(child, proportion)
                                    ))

                    if original:
                        section_line = component_lines.filtered(
                            lambda
                                s: s.display_type == 'line_section' and s.name == line.product_id.name and s.line_id == line.id
                        )

                        parent_line = component_lines.filtered(
                            lambda l: l.is_parent and l.product_id.id == line.product_id.id and l.order_line_id.id == line.id
                        )

                        if section_line:
                            section_line.write({'sequence': seq})
                            set_seq += 1
                            seq += 1

                        if parent_line:
                            parent_line.write({
                                'product_qty': line.product_uom_qty,
                                'unit_sale_price': line.price_unit,
                                'sequence': seq
                            })
                            set_seq += 1
                            seq += 1

                            tmpl_id = line.product_id.product_tmpl_id.id
                            child_lines = component_lines.filtered(
                                lambda l: not l.is_parent and
                                        l.parent_product_id.id == tmpl_id and
                                        l.order_line_id.id == line.id
                            )

                            for child in child_lines:
                                child.sequence = seq
                                seq += 1
                                # child.sequence = set_seq
                                # set_seq += 1

                                if line.product_uom_qty > 0:
                                    proportion = child.product_qty / line.product_uom_qty if line.product_uom_qty else 0.0

                                    def make_child_updater(c, prop):
                                        def _updater(s):
                                            s['proportion_factor'] = prop
                                            s['live_unit_cost'] = c.live_unit_cost / c.product_qty if c.product_qty else 0.0
                                            s[
                                                'quoted_cost_per_unit'] = c.quoted_cost_per_unit / c.product_qty if c.product_qty else 0.0
                                            s[
                                                'pre_project_cost_per_unit'] = c.pre_project_cost_per_unit / c.product_qty if c.product_qty else 0.0
                                            s['custom_proportion'] = True

                                        return _updater

                                    batch_updates.append((
                                        line.id,
                                        child.product_id.id,
                                        make_child_updater(child, proportion)
                                    ))
                        continue

            if new_sale_line_added:
                # Collect Section line values
                new_records_vals.append({
                    'component_id': self.id,
                    'display_type': 'line_section',
                    'name': line.product_id.name,
                    'sequence': seq,
                    'order_line_id': line.id,
                })
                seq += 1
                set_seq += 1

                # Collect Parent line values
                new_records_vals.append({
                    'component_id': self.id,
                    'is_parent': True,
                    'product_id': line.product_id.id,
                    'product_name': line.custom_product_name,
                    'parent_product_code': line.line_section_name,
                    'product_qty': line.product_uom_qty,
                    'unit_component_quantity': 1.0,
                    'unit_sale_price': line.price_unit,
                    'live_unit_cost': 0.0,
                    'system_cost_per_unit': 0.0,
                    'is_auto_generated': True,
                    'supplier_id': self.get_product_suppiler(line.product_id),
                    'sequence': seq,
                    'order_line_id': line.id,
                })
                seq += 1
                set_seq += 1

                # Collect BOM lines (children) values
                _logger.info(" ---------------------- Getting BOM  ----------------------- ")
                bom_dict = self.env['mrp.bom']._bom_find(line.product_id)
                bom = bom_dict.get(line.product_id)
                _logger.info(" ---------------------- GOT BOM  ----------------------- ")
                bom_lines = False

                if bom:
                    _logger.info(" ---------------------- Fething BOM lines Begins  ----------------------- ")
                    bom_lines = bom.bom_line_ids

                    for bom_line in bom_lines:
                        multiply_qty = bom_line.product_qty * line.product_uom_qty if line.product_uom_qty else bom_line.product_qty
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
                            'component_id': self.id,
                            'is_parent': False,
                            'is_new_bom_line': True,
                            'parent_product_id': line.product_id.product_tmpl_id.id,
                            'product_id': bom_line.product_id.id,
                            'product_qty': (line.product_uom_qty * bom_line.product_qty)
                                if (line.product_uom_qty * bom_line.product_qty) > 0
                                else (bom_line.product_qty if bom_line.product_qty > 0 else 1.0),
                            'unit_component_quantity': bom_line.product_qty if bom_line.product_qty > 0 else 1.0,
                            'system_cost_per_unit': multiply_qty * bom_line.product_id.standard_price,
                            'live_unit_cost': multiply_qty * bom_line.product_id.standard_price,
                            'manual_live_unit_cost': bom_line.product_id.standard_price,
                            'is_auto_generated': True,
                            'supplier_id': self.get_product_suppiler(bom_line.product_id),
                            'sequence': seq,
                            'order_line_id': line.id,
                        })
                        seq += 1
                        set_seq += 1
                    _logger.info(" ---------------------- BOM Lines Fetched and Looped.  ----------------------- ")

                if odoo_adjustment_product and line.product_id.id != odoo_adjustment_product.id and not line.product_id.is_delivery_and_installation:
                    # Collect freight/assembly lines for new parent only
                    for product in freight_assembly_products:
                        multiply_qty = 1 * line.product_uom_qty if line.product_uom_qty > 0 else 1.0
                        proportion = 1
                        batch_updates.append((
                            line.id,
                            product.id,
                            make_bom_updater(self._get_live_unit_for_delivery_or_installation(line.product_id, product),
                                            proportion)
                        ))
                        new_records_vals.append({
                            'component_id': self.id,
                            'is_parent': False,
                            'is_freight_or_assembly': True,
                            'is_new_bom_line': True,
                            'order_line_id': line.id,
                            'parent_product_id': line.product_id.product_tmpl_id.id,
                            'product_id': product.id,
                            'product_qty': line.product_uom_qty if line.product_uom_qty > 0 else 1.0,
                            'unit_component_quantity': 1.0,
                            'live_unit_cost': multiply_qty * self._get_live_unit_for_delivery_or_installation(
                                line.product_id, product
                            ),
                            'manual_live_unit_cost': self._get_live_unit_for_delivery_or_installation(
                                line.product_id, product
                            ),
                            'is_auto_generated': True,
                            'supplier_id': self.get_product_suppiler(product),
                            'sequence': seq,
                        })
                        seq += 1
                        set_seq += 1

        if new_records_vals:
            if next_order_line:
                _logger.info(" ---------------------- NEXT ORDER LINES Available  ----------------------- ")
                next_comp_lines = component_lines.sorted(lambda c:c.sequence).filtered(lambda cl:cl.sequence >= parent_section_seq)
                for line in next_comp_lines:
                    line.sequence = seq
                    seq+=1
                _logger.info(" ---------------------- NEXT ORDER LINES UPDATED  ----------------------- ")

            _logger.info(" ---------------------- CREATING NEW BOM LINES !!  ----------------------- ")
            res = self.env['sale.order.bom.component.line'].sudo().create(new_records_vals)
            _logger.info(" ----------------------   SALE ORDER BOM COMPONENT LINE CREATED  ----------------------- ")
            # _logger.info(new_records_vals)

        if batch_updates:
            self._batch_update_state(batch_updates)

        # Refresh component_lines to include newly created records
        if not res:
            self.update_component_line_ids(component_lines,parent_component_lines)
            # self._update_cost_margin(component_lines,parent_component_lines,sale_order_line)

        if res:
            component_lines = self.component_line_ids
            parent_component_lines = res.filtered(lambda l: l.is_parent)
            self.update_component_line_ids(res,parent_component_lines)



    def update_component_line_ids(self,component_lines=False,parent_lines=False):
        for record in self:
            # parent_number = 1
            updates = []
            for parent in parent_lines:
                # parent.parent_number = parent_number
                # parent_number += 1

                child_lines = component_lines.filtered(
                    lambda l: l.parent_product_id == parent.product_id.product_tmpl_id 
                    and l.order_line_id == parent.order_line_id
                )
                # ── Recompute quantities only for changed parent ──────────
                # if parent.current_change:
                #     parent.current_change = False
                #     record._compute_component_quantities(parent, child_lines)
                
                pre_proj = sys_cost = quoted = live = 0.0
                for cl in child_lines:
                    pre_proj+= cl.pre_project_cost_per_unit
                    sys_cost+= cl.system_cost_per_unit
                    quoted+= cl.quoted_cost_per_unit
                    live+= cl.live_unit_cost

                    # Build proportion updates in same loop — no second pass
                    if cl.product_id and parent.product_qty > 0:
                        new_proportion = cl.product_qty / parent.product_qty
                        def make_updater(prop):
                            def _updater(s):
                                s['proportion_factor'] = prop
                                s['custom_proportion'] = True
                            return _updater
                    
                        updates.append((
                            cl.order_line_id.id,
                            cl.product_id.id,
                            make_updater(new_proportion)
                        ))
                if parent.product_qty == 0.0:
                    parent.pre_project_cost_per_unit = 0.0
                    parent.system_cost_per_unit = 0.0
                    parent.quoted_cost_per_unit = 0.0
                    parent.live_unit_cost = 0.0 
                    # parent.manual_live_unit_cost = (live / parent.product_qty if parent.product_qty else 0.0)                       
                # Write aggregated costs to parent
                if parent.product_qty > 0.0:
                    parent.pre_project_cost_per_unit = pre_proj
                    parent.system_cost_per_unit = sys_cost
                    parent.quoted_cost_per_unit = quoted
                    parent.live_unit_cost = live
                    parent.manual_live_unit_cost = (live / parent.product_qty if parent.product_qty else 0.0)

            if updates:
                self._batch_update_state(updates)

    def _update_cost_margin(self,component_lines=False,parent_lines=False,filtered_sale_order_lines=False):
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
            sale_order_lines = sale_order.order_line

            child_lines = component_lines.filtered(lambda cl:not cl.is_parent and not cl.display_type)

            parent_product_total_sale_price = sum(parent_lines.mapped('total_sale_price'))

            total_system_cost = sum(child_lines.mapped('system_cost_per_unit'))
            total_live_cost = sum(child_lines.mapped('live_unit_cost'))
            total_quoted_cost = sum(child_lines.mapped('quoted_cost_per_unit'))
            total_pre_project_cost = sum(child_lines.mapped('pre_project_cost_per_unit'))

            total_margin_system_cost = sum(parent_lines.mapped('system_cost_per_unit'))
            total_margin_quoted_cost = sum(parent_lines.mapped('quoted_cost_per_unit'))
            total_margin_pre_project_cost = sum(parent_lines.mapped('pre_project_cost_per_unit'))
            total_margin_live_cost = sum(parent_lines.mapped('live_unit_cost'))
            
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
                
            # filtered_sale_order_lines = sale_order_lines.filtered(lambda l: l.product_id)
            for line in filtered_sale_order_lines:
                matching_bom_line = component_lines.filtered(
                    lambda l: l.order_line_id.id == line.id and l.is_parent and l.product_id.id == line.product_id.id)
                if matching_bom_line:
                    line.write({
                        'product_uom_qty': matching_bom_line.product_qty,
                        'price_unit': matching_bom_line.unit_sale_price,
                    })

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderBomComponentExt, self).default_get(fields)
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

        odoo_adjustment_product = self.env.ref('freight_out_assembly_install_feature.product_odoo_adjustment')
        products = False

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
                    'unit_component_quantity': 1.0,
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
                        multiply_qty = bom_line.product_qty * line.product_uom_qty if line.product_uom_qty > 0 else bom_line.product_qty
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
                            'product_qty': (line.product_uom_qty * bom_line.product_qty)
                            if (line.product_uom_qty * bom_line.product_qty) > 0
                            else (bom_line.product_qty if bom_line.product_qty > 0 else 1),
                            'unit_component_quantity': bom_line.product_qty if bom_line.product_qty > 0 else 1.0,
                            'system_cost_per_unit': multiply_qty * bom_line.product_id.standard_price,
                            'live_unit_cost': multiply_qty * bom_line.product_id.standard_price,
                            'manual_live_unit_cost': bom_line.product_id.standard_price,
                            'is_auto_generated': True,
                            'supplier_id': self.get_product_suppiler(bom_line.product_id),
                            'sequence': seq,
                        }))
                        seq += 1
                    if odoo_adjustment_product and line.product_id.id != odoo_adjustment_product.id and not line.product_id.is_delivery_and_installation:
                        products = self.env['product.product'].search(
                            [('is_freight_or_assembly', '=', True)]
                        )
                        for product in products:
                            multiply_qty = 1 * line.product_uom_qty if line.product_uom_qty > 0 else 1
                            new_proportion = 1

                            # Store state in initial_state dict
                            prod_key = str(product.id)
                            initial_state[line_key][prod_key] = {
                                'live_unit_cost': self._get_live_unit_for_delivery_or_installation(line.product_id,
                                                                                                   product),
                                'pre_project_cost_per_unit': 0,
                                'quoted_cost_per_unit': 0,
                                'proportion_factor': new_proportion,
                                'custom_proportion': True,
                            }

                            component_lines.append((0, 0, {
                                'is_parent': False,
                                'is_freight_or_assembly': True,
                                'is_new_bom_line': True,
                                'order_line_id': line.id,
                                'parent_product_id': line.product_id.product_tmpl_id.id,
                                'product_id': product.id,
                                'product_qty': line.product_uom_qty if line.product_uom_qty > 0 else 1.0,
                                'unit_component_quantity': 1.0,
                                'live_unit_cost': multiply_qty * self._get_live_unit_for_delivery_or_installation(
                                    line.product_id,
                                    product),
                                'manual_live_unit_cost': self._get_live_unit_for_delivery_or_installation(
                                    line.product_id,
                                    product),
                                'is_auto_generated': True,
                                'supplier_id': self.get_product_suppiler(product),
                                'sequence': seq,
                            }))
                            seq += 1

        if not component_lines:
            raise UserError(_("No Bill of Materials found for the products in this order."))

        # -------------------- CREATE STATE MODEL ----------------------------------
        state_record_result = False
        component_state_id = False
        state_record = self.env['bom.component.state'].sudo().search([('order_id', '=', order_id)], limit=1)

        if not state_record:
            state_record_result = self.env['bom.component.state'].sudo().create({
                'order_id': order_id,
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

    @api.depends('component_line_ids.total_sale_price','component_line_ids.system_cost_per_unit','component_line_ids.quoted_cost_per_unit','component_line_ids.pre_project_cost_per_unit','component_line_ids.live_unit_cost',)
    def _compute_multi_total_from_bom_lines(self):
        for record in self:
            parent_lines = False
            parent_product_total_sale_price = 0.0
            total_margin_system_cost = 0.0
            total_margin_quoted_cost = 0.0
            total_margin_pre_project_cost = 0.0
            total_margin_live_cost = 0.0
            component_lines = record.component_line_ids
            if not component_lines:
                record.total_parent_product_sale_price = parent_product_total_sale_price
                record.total_parent_system_cost_per_unit = total_margin_system_cost
                record.total_parent_quoted_cost_per_unit = total_margin_quoted_cost
                record.total_parent_pre_project_cost_per_unit = total_margin_pre_project_cost
                record.total_parent_live_unit_cost = total_margin_live_cost
            if component_lines:
                parent_lines = component_lines.filtered(lambda c:c.is_parent)
                if not parent_lines:
                    record.total_parent_product_sale_price = parent_product_total_sale_price
                    record.total_parent_system_cost_per_unit = total_margin_system_cost
                    record.total_parent_quoted_cost_per_unit = total_margin_quoted_cost
                    record.total_parent_pre_project_cost_per_unit = total_margin_pre_project_cost
                    record.total_parent_live_unit_cost = total_margin_live_cost
                if parent_lines:
                    parent_product_total_sale_price = sum(parent_lines.mapped('total_sale_price'))
                    total_margin_system_cost = sum(parent_lines.mapped('system_cost_per_unit'))
                    total_margin_quoted_cost = sum(parent_lines.mapped('quoted_cost_per_unit'))
                    total_margin_pre_project_cost = sum(parent_lines.mapped('pre_project_cost_per_unit'))
                    total_margin_live_cost = sum(parent_lines.mapped('live_unit_cost'))
                    record.total_parent_product_sale_price = parent_product_total_sale_price
                    record.total_parent_system_cost_per_unit = total_margin_system_cost
                    record.total_parent_quoted_cost_per_unit = total_margin_quoted_cost
                    record.total_parent_pre_project_cost_per_unit = total_margin_pre_project_cost
                    record.total_parent_live_unit_cost = total_margin_live_cost

    def write(self, vals):
        res = super(SaleOrderBomComponentExt, self).write(vals)
        for record in self: 
            if vals.get('component_line_ids'):
                lines_list = vals['component_line_ids']
                ids = False
                if len(lines_list) == 1:
                    ids = [item[1] for item in lines_list if item[0] == 1]
                if len(lines_list) > 1:
                    # ids = [item[1] for item in lines_list if item[0] == 1 and (item[2].get('product_qty') or (item[2].get('unit_sale_price')))]
                    ids = [item[1] for item in lines_list if item[0] == 1 and ('product_qty' in item[2] or 'unit_sale_price' in item[2])]
                    
                if isinstance(lines_list, list):
                    if all(isinstance(item, list) for item in lines_list):
                        if ids:
                            self.update_sale_order_product_qty(ids)
        return res  

    def update_sale_order_product_qty(self,bom_line_ids):
        bom_lines=False
        if bom_line_ids:
            bom_lines = self.env['sale.order.bom.component.line'].sudo().browse(bom_line_ids)  
            bom_lines = bom_lines.filtered(lambda bl:bl.is_parent)
            for line in bom_lines:
                line.order_line_id.write({
                        'product_uom_qty': line.product_qty,
                        'price_unit': line.unit_sale_price,
                    })

                
                

class SaleOrderBOMComponentLineExt(models.Model):
    _inherit = 'sale.order.bom.component.line'

    unit_component_quantity = fields.Float(string='Unit Component Quantity', default=1.0)


    @api.onchange('unit_component_quantity')
    def _onchange_unit_component_quantity(self):
        for line in self:
            if line.is_parent:
                line.product_qty = line.product_qty * line.unit_component_quantity
            if not line.is_parent:
                if line.unit_component_quantity <= 0:
                    line.unit_component_quantity = 1.0
                bom_component_lines = line.component_id.component_line_ids
                find_parent_product_line = bom_component_lines.filtered(
                    lambda l: l.is_parent and l.order_line_id == line.order_line_id)
                line.product_qty = find_parent_product_line.product_qty * line.unit_component_quantity if find_parent_product_line.product_qty > 0 else line.unit_component_quantity
    
    def recalculate_parent_total_live_cost(self):
        bom_component = self.component_id
        child_component_lines = False
        total_live_cost_of_child = 0
        if bom_component:
           child_component_lines = bom_component.component_line_ids.filtered(lambda c: not c.display_type and not c.is_parent and c.order_line_id.id == self.order_line_id.id)
           total_live_cost_of_child = sum(child_component_lines.mapped('live_unit_cost'))
           if self.product_qty > 0.0:
            self.live_unit_cost = total_live_cost_of_child
