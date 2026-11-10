import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError, RedirectWarning

_logger = logging.getLogger(__name__)


class SaleOrderBomComponentExt(models.Model):
    _inherit = 'sale.order.bom.component'

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
        odoo_adjustment_product = self.env.ref('freight_out_assembly_install_feature.product_odoo_adjustment')
        freight_assembly_products = self.env['product.product'].search(
            [('is_freight_or_assembly', '=', True)]
        )

        filtered_sale_order_lines = sale_order_line.sorted(lambda o: o.sequence).filtered(lambda l: l.product_id)

        for line in filtered_sale_order_lines:
            pair_key = (line.product_id.id, line.id)

            if pair_key in already_added_pairs:
                section_line = component_lines.filtered(
                    lambda
                        s: s.display_type == 'line_section' and s.name == line.product_id.name and s.line_id == line.id
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

            # Collect Section line values
            new_records_vals.append({
                'component_id': self.id,
                'display_type': 'line_section',
                'name': line.product_id.name,
                'sequence': set_seq,
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
                        'component_id': self.id,
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
            if odoo_adjustment_product and line.product_id.id != odoo_adjustment_product.id and not line.product_id.is_delivery_and_installation:
                # Collect freight/assembly lines for new parent only
                for product in freight_assembly_products:
                    multiply_qty = 1 * line.product_uom_qty
                    proportion = 1
                    batch_updates.append((
                            line.id,
                            product.id,
                            make_bom_updater(self._get_live_unit_for_delivery_or_installation(line.product_id,product), proportion)
                        ))
                    new_records_vals.append({
                        'component_id': self.id,
                        'is_parent': False,
                        'is_freight_or_assembly': True,
                        'is_new_bom_line': True,
                        'order_line_id': line.id,
                        'parent_product_id': line.product_id.product_tmpl_id.id,
                        'product_id': product.id,
                        'product_qty': multiply_qty,
                        'live_unit_cost': multiply_qty * self._get_live_unit_for_delivery_or_installation(
                            line.product_id, product
                        ),
                        'manual_live_unit_cost': self._get_live_unit_for_delivery_or_installation(
                            line.product_id, product
                        ),
                        'is_auto_generated': True,
                        'supplier_id': self.get_product_suppiler(product),
                        'sequence': set_seq,
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
                    if odoo_adjustment_product and line.product_id.id != odoo_adjustment_product.id and not line.product_id.is_delivery_and_installation:
                        products = self.env['product.product'].search(
                            [('is_freight_or_assembly', '=', True)]
                        )
                        for product in products:
                            multiply_qty = 1 * line.product_uom_qty
                            new_proportion = 1

                            # Store state in initial_state dict
                            prod_key = str(product.id)
                            initial_state[line_key][prod_key] = {
                                'live_unit_cost': self._get_live_unit_for_delivery_or_installation(line.product_id,product),
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
                                'product_qty': multiply_qty,
                                'live_unit_cost': multiply_qty * self._get_live_unit_for_delivery_or_installation(line.product_id,
                                                                                                product),
                                'manual_live_unit_cost': self._get_live_unit_for_delivery_or_installation(line.product_id,
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

    def _get_live_unit_for_delivery_or_installation(self, parent_product, product):
        if not parent_product.variant_delivery_code_selection_id:
            return 0.0 
        if parent_product.variant_delivery_code_selection_id:
            if product.default_code == 'freight-out':
                return parent_product.variant_delivery_code_selection_id.delivery_code_cost
            elif product.default_code == 'assy-inst':
                return parent_product.variant_delivery_code_selection_id.installation_cost
            else:
                return 0.0


class SaleOrderBOMComponentLineExt(models.Model):
    _inherit = 'sale.order.bom.component.line'

    is_freight_or_assembly = fields.Boolean(string='Freight or Assembly')

    def unlink(self):
        for record in self:
            if not record._context.get('force_delete') and record.is_freight_or_assembly:
                raise UserError(
                    'You Cannot Delete the Freight or Assembly Component'
                )
        return super(SaleOrderBOMComponentLineExt, self).unlink()

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
