from odoo import models, fields, api, _
class SaleOrderBOMComponentExt(models.Model):
    _inherit = 'sale.order.bom.component'

    code_sale_order_line_id = fields.Many2one('sale.order.line')

    code_id_value = fields.Char(compute="_compute_code_id_value",store=True)

    filtered_component_line_ids = fields.One2many(
        'sale.order.bom.component.line',
        'component_id',
        domain=lambda self: self._compute_code_domain()
    )

    @api.depends('code_sale_order_line_id')
    def _compute_code_domain(self):
        for record in self:
            if record.code_sale_order_line_id:
                return [('line_section_id_value', '=', record.code_id_value)]
            else:
                return []

    @api.depends('code_sale_order_line_id')
    def _compute_code_id_value(self):
        for record in self:
            if record.code_sale_order_line_id:
                record.code_id_value = str(record.code_sale_order_line_id.id)
            else:
                record.code_id_value = False
    


    @api.onchange('component_line_ids')
    def onchange_component_line_ids(self,changed_order_lines=False):
        # print("<<<<<>>>>>>>  onchange_component_line_ids")
        sequence_val = False
        order_line_val = False
        parent_product = False
        children_index = {}   # (parent_tmpl_id, order_line_id) -> [child lines]
        all_parents    = []
        key = False
        changed_bom_parent_lines = False

        if not changed_order_lines:
            changed_bom_parent_lines = self.component_line_ids.filtered(lambda l: l.product_id and l.is_parent and ( l.product_qty  != l._origin.product_qty or l.unit_sale_price != l._origin.unit_sale_price))

        changed_ids = changed_order_lines._origin.ids if changed_order_lines else []
        # map order_line_id -> the specific changed line, since changed_order_lines
        # may hold multiple records and .product_uom_qty/.price_unit/etc. need a singleton
        changed_by_id = {}
        if changed_order_lines:
            for cl in changed_order_lines:
                changed_by_id[cl._origin.id] = cl

        for record in self:
            component_lines = record.component_line_ids.sorted(lambda o: o.sequence)
            if not component_lines:
                continue
            if component_lines:
                for line in component_lines:
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
                        if not changed_order_lines and not changed_bom_parent_lines:
                            all_parents.append(line)    
                        if changed_bom_parent_lines and line.order_line_id.id in changed_bom_parent_lines.order_line_id.ids:
                            all_parents.append(line)  
                        # Picks Up Specific Parent Line Changed                        # 
                        if changed_order_lines and line.order_line_id.id in changed_ids:
                            matched = changed_by_id[line.order_line_id.id]
                            line.product_qty = matched.product_uom_qty
                            line.unit_sale_price = matched.price_unit
                            line.total_sale_price = matched.price_subtotal
                            line.current_change = True
                            all_parents.append(line)
                            # line.product_qty = changed_order_lines.product_uom_qty
                            # line.unit_sale_price = changed_order_lines.price_unit
                            # line.total_sale_price = changed_order_lines.price_subtotal
                            # line.current_change = True
                            # all_parents.append(line)
                    if not line.display_type and not line.is_parent:
                        sequence_val = sequence_val + 1
                        line.sequence = sequence_val
                        line.parent_product_id = parent_product
                        line.order_line_id = order_line_val
                        # index built in same pass — no second filtered() needed
                        if not changed_order_lines and not changed_bom_parent_lines:
                            key = (line.parent_product_id.id, line.order_line_id.id)
                            children_index.setdefault(key, []).append(line) 
                        if changed_bom_parent_lines and line.order_line_id.id in changed_bom_parent_lines.order_line_id.ids:
                            key = (line.parent_product_id.id, line.order_line_id.id)
                            children_index.setdefault(key, []).append(line)
                        # Picks Up Specific Parent Line Changed , childs. 
                        if changed_order_lines and line.order_line_id.id in changed_ids:
                            key = (line.parent_product_id.id, line.order_line_id.id)
                            children_index.setdefault(key, []).append(line)
                if not all_parents:
                    return

                updates = []

                for parent in all_parents:
                    key = (parent.product_id.product_tmpl_id.id, parent.order_line_id.id)
                    child_lines = children_index.get(key, [])

                    # ── Recompute quantities only for changed parent ──────────
                    if parent.current_change:
                        parent.current_change = False
                        record._compute_component_quantities(parent, child_lines)
                    
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
    
    @api.onchange('filtered_component_line_ids')
    def onchange_filtered_component_line_ids(self,changed_order_lines=False):
        # print("<<<<<>>>>>>>  onchange_filtered_component_line_ids")
        sequence_val = False
        order_line_val = False
        parent_product = False
        children_index = {}   # (parent_tmpl_id, order_line_id) -> [child lines]
        all_parents    = []
        key = False
        changed_bom_parent_lines = False

        if not changed_order_lines:
            changed_bom_parent_lines = self.component_line_ids.filtered(lambda l: l.product_id and l.is_parent and ( l.product_qty  != l._origin.product_qty or l.unit_sale_price != l._origin.unit_sale_price))

        changed_ids = changed_order_lines._origin.ids if changed_order_lines else []
        # map order_line_id -> the specific changed line, since changed_order_lines
        # may hold multiple records and .product_uom_qty/.price_unit/etc. need a singleton
        changed_by_id = {}
        if changed_order_lines:
            for cl in changed_order_lines:
                changed_by_id[cl._origin.id] = cl

        for record in self:
            component_lines = record.component_line_ids.sorted(lambda o: o.sequence)
            if not component_lines:
                continue
            if component_lines:
                for line in component_lines:
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
                        if not changed_order_lines and not changed_bom_parent_lines:
                            all_parents.append(line)    
                        if changed_bom_parent_lines and line.order_line_id.id in changed_bom_parent_lines.order_line_id.ids:
                            all_parents.append(line)  
                        # Picks Up Specific Parent Line Changed                        # 
                        if changed_order_lines and line.order_line_id.id in changed_ids:
                            matched = changed_by_id[line.order_line_id.id]
                            line.product_qty = matched.product_uom_qty
                            line.unit_sale_price = matched.price_unit
                            line.total_sale_price = matched.price_subtotal
                            line.current_change = True
                            all_parents.append(line)
                            # line.product_qty = changed_order_lines.product_uom_qty
                            # line.unit_sale_price = changed_order_lines.price_unit
                            # line.total_sale_price = changed_order_lines.price_subtotal
                            # line.current_change = True
                            # all_parents.append(line)
                    if not line.display_type and not line.is_parent:
                        sequence_val = sequence_val + 1
                        line.sequence = sequence_val
                        line.parent_product_id = parent_product
                        line.order_line_id = order_line_val
                        # index built in same pass — no second filtered() needed
                        if not changed_order_lines and not changed_bom_parent_lines:
                            key = (line.parent_product_id.id, line.order_line_id.id)
                            children_index.setdefault(key, []).append(line) 
                        if changed_bom_parent_lines and line.order_line_id.id in changed_bom_parent_lines.order_line_id.ids:
                            key = (line.parent_product_id.id, line.order_line_id.id)
                            children_index.setdefault(key, []).append(line)
                        # Picks Up Specific Parent Line Changed , childs. 
                        if changed_order_lines and line.order_line_id.id in changed_ids:
                            key = (line.parent_product_id.id, line.order_line_id.id)
                            children_index.setdefault(key, []).append(line)
                if not all_parents:
                    return

                updates = []

                for parent in all_parents:
                    key = (parent.product_id.product_tmpl_id.id, parent.order_line_id.id)
                    child_lines = children_index.get(key, [])

                    # ── Recompute quantities only for changed parent ──────────
                    if parent.current_change:
                        parent.current_change = False
                        record._compute_component_quantities(parent, child_lines)
                    
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
   
class SaleOrderBOMComponentLineExt(models.Model):
    _inherit = 'sale.order.bom.component.line'


    line_group_id_value = fields.Char(related='order_line_id.line_group_id_value', store=True)

    line_section_id_value = fields.Char(related='order_line_id.line_section_id_value', store=True)




