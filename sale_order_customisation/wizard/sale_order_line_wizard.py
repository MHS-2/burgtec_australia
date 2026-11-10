# Do not forget to add this file to __init__.py
# Refer to https://www.odoo.com/documentation/17.0/contributing/development/coding_guidelines.html for coding guidelines

from odoo import _, fields, models, api, _, Command
from odoo.exceptions import ValidationError, UserError


class SaleOrderLineWizard(models.TransientModel):
    _name = "sale.order.line.wizard"
    _description = "Sale Order Line Wizard"

    code_name = fields.Char(string="Code")

    type_of_addition = fields.Selection([
        ('code', 'Code'),
        ('product', 'Product'),
    ])

    sale_order_product_line_wizard_ids = fields.One2many('sale.order.product.line.wizard', 'sale_order_line_wiard_id')

    # Fields For Swapping

    sale_order_id = fields.Many2one('sale.order', readonly=True)

    active_group_id = fields.Many2one('sale.order.line', readonly=True)

    target_group_id = fields.Many2one('sale.order.line')

    active_code_id = fields.Many2one('sale.order.line', readonly=True)

    target_code_id = fields.Many2one('sale.order.line')

    acitvie_code_line_group_id_value = fields.Char(string="Active Code Line Group Id Value", related='active_code_id.line_group_id_value', store=True)

    acitvie_code_line_group_name = fields.Char(string="Active Code Line Group Name",related='active_code_id.line_group_name', store=True)

    target_code_line_group_id_value = fields.Char(string="Target Code Line Group Id Value",related='target_code_id.line_group_id_value', store=True)

    position = fields.Selection(
        [
            ('top', 'Top'),
            ('bottom', 'Bottom'),
            ('replace', 'Replace')
        ]
    )

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    pricelist_id = fields.Many2one('product.pricelist',related="sale_order_id.pricelist_id",store=True)

    date_order = fields.Datetime(related="sale_order_id.date_order",store=True)

    currency_id = fields.Many2one(
        related='sale_order_id.currency_id',
        depends=['sale_order_id.currency_id'],
        store=True, precompute=True)
    
    is_use_pop_up_configurator = fields.Boolean(default=False)

    product_model_type = fields.Selection(
        [
            ('product_template','Product Template'),
            ('product_variant','Product Variant')
        ],
        default="product_template"
    )

    product_variant_selection = fields.Selection(
        [
            ('product_variant_sel','Product Variant')
        ], default=False
    )

    product_template_selection = fields.Selection(
        [
            ('product_template_sel','Product Template')
        ], default=False
    )

    selection_text = fields.Char(compute="compute_selection_text",store=True)


    # Now By Default Show Product Template View. Rather than choice.

    is_main_product_added = fields.Boolean(default=False)

    group_name = fields.Char()

    product_sale_type = fields.Selection([
            ('burgtec','Burgtec'),
            ('dpg','DPG'),
    ], compute="compute_product_sale_type",store=True)

    @api.depends('sale_order_id')
    def compute_product_sale_type(self):
        for record in self:
            sales_order_line = False
            series = False
            sales_order = False
            sales_order_line = self.env['sale.order.line'].browse(self._context.get('active_id', []))
            if not sales_order_line:
                record.product_sale_type = False
            if sales_order_line:
                sales_order = sales_order_line.order_id
                series = sales_order.opportunity_id.series_sequence_id.sequence
                if not series == 9:
                    record.product_sale_type = 'burgtec'
                if series == 9:
                    record.product_sale_type = 'dpg'
                



    # Called by action button to show sticky notification
    def action_add_code(self):
        vals = {}
        order_lines = False
        last_line = False
        active_sale_order_line_id = self.env.context.get('active_id')
        sale_order_line_obj = self.env['sale.order.line'].sudo().browse(active_sale_order_line_id)
        group_sequence = sale_order_line_obj.sequence
        new_code_sequence = group_sequence + 1
        sale_order_obj = sale_order_line_obj.order_id
        order_lines = sale_order_obj.order_line.sorted(lambda o: o.sequence)  # Save Before Clearing.

        in_defect_group = False
        
        # If Code inside Defected Group.
        defected_lines = sale_order_obj.defected_line_ids.ids
        if defected_lines:
            if sale_order_line_obj.id in defected_lines:
                in_defect_group = True

        lines_in_group = order_lines.filtered(lambda l: int(l.line_group_id_value) == sale_order_line_obj.id)
        if lines_in_group:
            last_line = lines_in_group[-1]
            new_code_sequence = last_line.sequence + 1

        lines_to_update = order_lines.filtered(
            lambda l: l.id != active_sale_order_line_id and l.sequence >= new_code_sequence)
        if lines_to_update:
            for line in lines_to_update:
                line.sequence += 1

        if self.code_name:
            vals.update(
                {
                    'order_id': sale_order_obj.id,
                    'name': self.code_name,
                    'display_type': 'line_note',
                    'sequence': new_code_sequence,
                }
            )

            if in_defect_group:
                vals['is_defect_group_line'] = True

            new_code_record = self.env['sale.order.line'].sudo().create(vals)

            sale_order_obj.order_line = [Command.link(new_code_record.id)]


    def action_add_product(self):
        if not self.sale_order_product_line_wizard_ids:
            raise UserError(_('Kindly Add Products First!'))
        
        active_sale_order_line_id = self.env.context.get('active_id')
        sale_order_line_obj = self.env['sale.order.line'].sudo().browse(active_sale_order_line_id)
        code_sequence = sale_order_line_obj.sequence
        new_product_sequence = code_sequence + 1
        sale_order_obj = sale_order_line_obj.order_id
        order_lines = sale_order_obj.order_line.sorted(lambda o: o.sequence)
        in_defect_group = False

        # If Code inside Defected Group.
        defected_lines = sale_order_obj.defected_line_ids.ids
        if defected_lines:
            if int(sale_order_line_obj.line_group_id_value) in defected_lines:
                in_defect_group = True


        lines_in_code = order_lines.filtered(lambda l: int(l.line_section_id_value) == sale_order_line_obj.id)
        if lines_in_code:
            last_line = lines_in_code[-1]
            new_product_sequence = last_line.sequence + 1

        lines_to_update = order_lines.filtered(
            lambda l: l.id != active_sale_order_line_id and l.sequence >= new_product_sequence)
        counter = len(self.sale_order_product_line_wizard_ids)
        for line in lines_to_update:
            line.sequence += counter

        # Batch create all lines at once
        if self.sale_order_product_line_wizard_ids:
            create_commands = []
            for product_line in self.sale_order_product_line_wizard_ids:
                order_line_vals = {
                    'order_id': sale_order_obj.id,
                    'product_id': product_line.product_id.id if product_line.product_id else product_line.product_template_id.product_variant_id.id,
                    'product_uom_qty': product_line.product_uom_qty,
                    'sequence': new_product_sequence,
                }
                if product_line.sub_selection_display:
                    order_line_vals['custom_product_name'] = product_line.sub_selection_display
                
                if in_defect_group:
                    order_line_vals['price_unit'] = 0.0
                    order_line_vals['is_defect_group_line'] = True
                
                create_commands.append(Command.create(order_line_vals))
                new_product_sequence += 1
            
            # Single write operation with all create commands
            sale_order_obj.order_line = create_commands

    def action_swap_groups(self):
        # [False, '1163', '1163', '1163', '1163', '1163', '1163', '1163', '1163', False, '1289', '1289']
        active_list = []
        target_list = []
        active_group_sequence = self.active_group_id.sequence
        target_group_sequence = self.target_group_id.sequence
        order_lines = self.sale_order_id.order_line.sorted(lambda o: o.sequence)  # Save Before Clearing.
        bom_component_id = self.sale_order_id.bom_component_id

        if self.position == 'replace':
            # Code and Products Under Active Group
            active_group_code_and_products = order_lines.filtered(
                lambda l: int(l.line_group_id_value) == self.active_group_id.id)
            target_group_code_and_products = order_lines.filtered(
                lambda l: int(l.line_group_id_value) == self.target_group_id.id)

            active_list.append(self.active_group_id.id)
            target_list.append(self.target_group_id.id)

            for id in active_group_code_and_products:
                active_list.append(id.id)

            for id in target_group_code_and_products:
                target_list.append(id.id)

                # @ TOP TO BOTTOM
            if active_group_sequence < target_group_sequence:
                lines_in_between = order_lines.filtered(lambda
                                                            l: l.sequence > self.active_group_id.sequence and l.sequence < self.target_group_id.sequence and l.id not in active_list and l.id not in target_list)
            # bottom to top
            if active_group_sequence > target_group_sequence:
                lines_in_between = order_lines.filtered(lambda
                                                            l: l.sequence > self.target_group_id.sequence and l.sequence < self.active_group_id.sequence and l.id not in active_list and l.id not in target_list)

            # Group BOTTOM TO TOP
            if active_group_sequence > target_group_sequence:  # 50 > 30
                self.active_group_id.sequence = target_group_sequence  # 30
                if active_group_code_and_products:
                    for line in active_group_code_and_products:
                        target_group_sequence += 1  # 30+=1
                        line.sequence = target_group_sequence
                # print(lines_in_between.mapped('display_type'))
                # print(lines_in_between.mapped('id'))
                next_sec = target_group_sequence
                # target_code_sequence = active_code_sequence + 1
                if lines_in_between:
                    for line in lines_in_between:
                        next_sec += 1
                        line.sequence = next_sec
                    next_sec += 1
                    active_group_sequence = next_sec
                else:
                    active_group_sequence = next_sec + 1
                # active_code_sequence = target_code_sequence
                self.target_group_id.sequence = active_group_sequence
                if target_group_code_and_products:
                    for line in target_group_code_and_products:
                        active_group_sequence += 1  # 50 +=1
                        line.sequence = active_group_sequence

            # GROUP Active on TOP than Target
            if active_group_sequence < target_group_sequence:
                self.target_group_id.sequence = active_group_sequence
                if target_group_code_and_products:
                    for line in target_group_code_and_products:
                        active_group_sequence += 1
                        line.sequence = active_group_sequence

                next_sec = active_group_sequence
                # target_code_sequence = active_code_sequence + 1
                # print(lines_in_between.mapped('display_type'))
                if lines_in_between:
                    for line in lines_in_between:
                        next_sec += 1
                        line.sequence = next_sec
                    next_sec += 1
                    target_group_sequence = next_sec
                else:
                    target_group_sequence = next_sec + 1
                self.active_group_id.sequence = target_group_sequence
                if active_group_code_and_products:
                    for line in active_group_code_and_products:
                        target_group_sequence += 1
                        line.sequence = target_group_sequence
            
            if bom_component_id:
                bom_component_id.update_component_lines()


        elif self.position == 'top':
            active_group_code_and_products = order_lines.filtered(
                lambda l: int(l.line_group_id_value) == self.active_group_id.id)
            target_group_code_and_products = order_lines.filtered(
                lambda l: int(l.line_group_id_value) == self.target_group_id.id)
            active_list.append(self.active_group_id.id)
            target_list.append(self.target_group_id.id)

            for id in active_group_code_and_products:
                active_list.append(id.id)

            for id in target_group_code_and_products:
                target_list.append(id.id)

            # Update active group and it code , products sequence.
            start_sequence = target_group_sequence
            self.active_group_id.sequence = start_sequence
            start_sequence += 1
            for line in active_group_code_and_products:
                line.sequence = start_sequence
                start_sequence += 1

            lines_to_update = order_lines.filtered(
                lambda l: l.sequence >= target_group_sequence and l.id not in active_list)
            if lines_to_update:
                for line in lines_to_update:
                    line.sequence = start_sequence
                    start_sequence += 1
            # print(lines_to_update.mapped('custom_product_name'))

            # Reset Sequences.
            initial_sequence = 10
            lines_to_reset = self.sale_order_id.order_line.sorted(lambda o: o.sequence)
            if lines_to_reset:
                for line in lines_to_reset:
                    # print(line.sequence,line.display_type,line.custom_product_name)
                    line.sequence = initial_sequence
                    initial_sequence += 1
            
            if bom_component_id:
                bom_component_id.update_component_lines()

        elif self.position == 'bottom':
            active_group_code_and_products = order_lines.filtered(
                lambda l: int(l.line_group_id_value) == self.active_group_id.id)
            target_group_code_and_products = order_lines.filtered(
                lambda l: int(l.line_group_id_value) == self.target_group_id.id)
            active_list.append(self.active_group_id.id)
            target_list.append(self.target_group_id.id)

            for id in active_group_code_and_products:
                active_list.append(id.id)

            for id in target_group_code_and_products:
                target_list.append(id.id)

            # Update active group and it code , products sequence.
            # print('Records!',target_group_code_and_products)
            # print('Records!',target_group_code_and_products.mapped('custom_product_name'))
            # print('Sequence',target_group_code_and_products.mapped('sequence'))

            set_sequence = max(target_group_code_and_products.mapped('sequence'))  # Sequence of last line.
            # Going to its bottom
            start_sequence = set_sequence + 1
            self.active_group_id.sequence = start_sequence
            start_sequence += 1
            for line in active_group_code_and_products:
                line.sequence = start_sequence
                start_sequence += 1

            search_seq = set_sequence + 1
            lines_to_update = order_lines.filtered(lambda l: l.sequence >= search_seq and l.id not in active_list)
            if lines_to_update:
                for line in lines_to_update:
                    line.sequence = start_sequence
                    start_sequence += 1
            # print(lines_to_update.mapped('custom_product_name'))

            # Reset Sequences.
            initial_sequence = 10
            lines_to_reset = self.sale_order_id.order_line.sorted(lambda o: o.sequence)
            if lines_to_reset:
                for line in lines_to_reset:
                    # print(line.sequence,line.display_type,line.custom_product_name)
                    line.sequence = initial_sequence
                    initial_sequence += 1
            if bom_component_id:
                bom_component_id.update_component_lines()
            

        else:
            raise UserError(_('Kindly, set the position for the operation!'))

    def action_swap_codes(self):
        # [False, '1163', '1163', '1163', '1163', '1163', '1163', '1163', '1163', False, '1289', '1289']
        active_list = []
        target_list = []
        lines_in_between = False
        active_code_sequence = self.active_code_id.sequence
        target_code_sequence = self.target_code_id.sequence
        order_lines = self.sale_order_id.order_line.sorted(lambda o: o.sequence)  # Save Before Clearing.
        bom_component_id = self.sale_order_id.bom_component_id

        if self.position == 'replace':
            # Products Under Active and Target Code
            active_code_products = order_lines.filtered(
                lambda l: int(l.line_section_id_value) == self.active_code_id.id)
            target_code_products = order_lines.filtered(
                lambda l: int(l.line_section_id_value) == self.target_code_id.id)

            active_list.append(self.active_code_id.id)
            target_list.append(self.target_code_id.id)

            for id in active_code_products:
                active_list.append(id.id)

            for id in target_code_products:
                target_list.append(id.id)

            # @ TOP TO BOTTOM
            if active_code_sequence < target_code_sequence:
                lines_in_between = order_lines.filtered(lambda
                                                            l: l.sequence > self.active_code_id.sequence and l.sequence < self.target_code_id.sequence and l.id not in active_list and l.id not in target_list)
            # bottom to top
            if active_code_sequence > target_code_sequence:
                lines_in_between = order_lines.filtered(lambda
                                                            l: l.sequence > self.target_code_id.sequence and l.sequence < self.active_code_id.sequence and l.id not in active_list and l.id not in target_list)

            # # BOTTOM TO TOP
            if active_code_sequence > target_code_sequence:  # 50 > 30
                self.active_code_id.sequence = target_code_sequence  # 30
                if active_code_products:
                    for line in active_code_products:
                        target_code_sequence += 1  # 30+=1
                        line.sequence = target_code_sequence
                    # target_code_sequence +=1 #continued
                # self.target_code_id.sequence = active_code_sequence #50

                # print(lines_in_between.mapped('display_type'))
                # print(lines_in_between.mapped('id'))
                next_sec = target_code_sequence
                # target_code_sequence = active_code_sequence + 1
                if lines_in_between:
                    for line in lines_in_between:
                        next_sec += 1
                        line.sequence = next_sec
                    next_sec += 1
                    active_code_sequence = next_sec
                else:
                    active_code_sequence = next_sec + 1
                # active_code_sequence = target_code_sequence
                self.target_code_id.sequence = active_code_sequence
                if target_code_products:
                    for line in target_code_products:
                        active_code_sequence += 1  # 50 +=1
                        line.sequence = active_code_sequence
                        # for preceeding lines
                # target_code_sequence = active_code_sequence + 1

                # Active on TOP than Target
            if active_code_sequence < target_code_sequence:
                self.target_code_id.sequence = active_code_sequence
                if target_code_products:
                    for line in target_code_products:
                        active_code_sequence += 1
                        line.sequence = active_code_sequence

                next_sec = active_code_sequence
                # target_code_sequence = active_code_sequence + 1
                if lines_in_between:
                    for line in lines_in_between:
                        next_sec += 1
                        line.sequence = next_sec
                    next_sec += 1
                    target_code_sequence = next_sec
                else:
                    target_code_sequence = next_sec + 1
                self.active_code_id.sequence = target_code_sequence
                if active_code_products:
                    for line in active_code_products:
                        target_code_sequence += 1
                        line.sequence = target_code_sequence

            if bom_component_id:
                bom_component_id.update_component_lines()
        elif self.position == 'top':
            # Products Under Active and Target Code
            active_code_products = order_lines.filtered(
                lambda l: int(l.line_section_id_value) == self.active_code_id.id)
            target_code_products = order_lines.filtered(
                lambda l: int(l.line_section_id_value) == self.target_code_id.id)

            active_list.append(self.active_code_id.id)
            target_list.append(self.target_code_id.id)

            for id in active_code_products:
                active_list.append(id.id)

            for id in target_code_products:
                target_list.append(id.id)

            # Update active code , products sequence.
            start_sequence = target_code_sequence
            self.active_code_id.sequence = start_sequence
            start_sequence += 1
            for line in active_code_products:
                line.sequence = start_sequence
                start_sequence += 1

            lines_to_update = order_lines.filtered(
                lambda l: l.sequence >= target_code_sequence and l.id not in active_list)
            if lines_to_update:
                for line in lines_to_update:
                    line.sequence = start_sequence
                    start_sequence += 1
            # print(lines_to_update.mapped('custom_product_name'))

            # Reset Sequences.
            initial_sequence = 10
            lines_to_reset = self.sale_order_id.order_line.sorted(lambda o: o.sequence)
            if lines_to_reset:
                for line in lines_to_reset:
                    # print(line.sequence,line.display_type,line.custom_product_name)
                    line.sequence = initial_sequence
                    initial_sequence += 1
            
            if bom_component_id:
                bom_component_id.update_component_lines()
        elif self.position == 'bottom':
            active_code_products = order_lines.filtered(
                lambda l: int(l.line_section_id_value) == self.active_code_id.id)
            target_code_products = order_lines.filtered(
                lambda l: int(l.line_section_id_value) == self.target_code_id.id)

            active_list.append(self.active_code_id.id)
            target_list.append(self.target_code_id.id)

            for id in active_code_products:
                active_list.append(id.id)

            for id in target_code_products:
                target_list.append(id.id)

            set_sequence = max(target_code_products.mapped('sequence'))  # Sequence of last line.
            # Going to its bottom
            start_sequence = set_sequence + 1
            self.active_code_id.sequence = start_sequence
            start_sequence += 1
            for line in active_code_products:
                line.sequence = start_sequence
                start_sequence += 1

            search_seq = set_sequence + 1
            lines_to_update = order_lines.filtered(lambda l: l.sequence >= search_seq and l.id not in active_list)
            if lines_to_update:
                for line in lines_to_update:
                    line.sequence = start_sequence
                    start_sequence += 1
            # print(lines_to_update.mapped('custom_product_name'))

            # Reset Sequences.
            initial_sequence = 10
            lines_to_reset = self.sale_order_id.order_line.sorted(lambda o: o.sequence)
            if lines_to_reset:
                for line in lines_to_reset:
                    # print(line.sequence,line.display_type,line.custom_product_name)
                    line.sequence = initial_sequence
                    initial_sequence += 1
            if bom_component_id:
                bom_component_id.update_component_lines()
        else:
            raise UserError(_('Kindly, set the position for the operation!'))
    
    @api.onchange('sale_order_product_line_wizard_ids')
    def onchange_product_line(self):
        wizard_lines = self.sale_order_product_line_wizard_ids.filtered(lambda w:w.product_id)
        if not wizard_lines:
            self.is_main_product_added = False

        if wizard_lines:
            if len(wizard_lines) == 1 and not wizard_lines.is_select_optional_product and not self.is_main_product_added:
                self.is_main_product_added = True

    
    
    @api.onchange('product_variant_selection')
    def onchange_product_model_type_to_variant(self):
        if self.product_variant_selection == 'product_variant_sel':
            if not self.sale_order_product_line_wizard_ids:
                self.product_model_type = 'product_variant'
                self.product_template_selection = False
            else:
                raise UserError(_("You Are Not Allowed To Switch After Adding The Product(s)!"))

    @api.onchange('product_template_selection')
    def onchange_product_model_type_to_template(self):
        if self.product_template_selection == 'product_template_sel':        
            if not self.sale_order_product_line_wizard_ids:
                self.product_model_type = 'product_template'
                self.product_variant_selection = False
            else:
                raise UserError(_("You Are Not Allowed To Switch After Adding The Product(s)!"))
    
    @api.depends('product_model_type')
    def compute_selection_text(self):
        for record in self:
            if record.product_model_type and record.product_model_type == 'product_template':
                record.selection_text = _('You Will Be Choosing Product Variant From Product Template Configurator.')
            elif record.product_model_type and record.product_model_type == 'product_variant':
                record.selection_text = _('You Are Adding Product Variant Directly.')
            else:
                record.selection_text = False
    
    def action_add_group(self):
        for record in self:
            vals = {}
            sale_order_id = self.env.context.get('active_id')
            sale_order_obj = self.env['sale.order'].sudo().browse(sale_order_id)
            order_lines = sale_order_obj.order_line.sorted(lambda o: o.sequence)
            sequence = False
            if not order_lines:
                vals.update(
                    {
                        'order_id': sale_order_obj.id,
                        'name': self.group_name,
                        'display_type': 'line_section',
                    }
                )
            if order_lines:
                sequence = order_lines[-1].sequence
                sequence+=1
                vals.update(
                    {
                        'order_id': sale_order_obj.id,
                        'name': self.group_name,
                        'display_type': 'line_section',
                        'sequence': sequence,
                    }
                )

            new_code_record = self.env['sale.order.line'].sudo().create(vals)

            sale_order_obj.order_line = [Command.link(new_code_record.id)]
                

class SaleOrderProductLineWizard(models.TransientModel):
    _name = "sale.order.product.line.wizard"
    _description = "Sale Order Product Line Wizard"


    # @api.depends('sale_order_line_wiard_id.is_use_pop_up_configurator','sale_order_line_wiard_id.product_sale_type')
    def _burgtec_product_template_domain_new(self):
        return [('is_old_data', '=', False),('sale_ok', '=', True),('product_bom_type', '!=', 'components'),("product_variant_count", ">", 1),('product_sale_type','=','burgtec')]


    def _dpg_product_template_domain_new(self):
        return [('is_old_data', '=', False),('sale_ok', '=', True),('product_bom_type', '!=', 'components'),("product_variant_count", ">", 1),('product_sale_type','=','dpg')]

    def _compute_product_template_domain_new(self):
        return [('is_old_data', '=', False),('sale_ok', '=', True),('product_bom_type', '!=', 'components'),("product_variant_count", ">", 1)]
        


    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        change_default=True, ondelete='restrict',)
        # domain="[('sale_ok', '=', True),('product_bom_type', '!=', 'components')]"
        # ('product_variant_count','=',1) Removed from aboce domain as now new data products variant's sale_ok is set true and old data's sale_ok to false
    
    product_template_id = fields.Many2one(
        string="Product Template",
        comodel_name='product.template',
        compute='_compute_product_template',
        domain=lambda self: self._compute_product_template_domain_new(),
        readonly=False,
    )

    burgtec_product_template_id = fields.Many2one(
            string="Product Template",
            comodel_name='product.template',
            compute='_compute_product_template_id',
            domain=lambda self: self._burgtec_product_template_domain_new(),
            readonly=False,
        )

    dpg_product_template_id = fields.Many2one(
            string="Product Template",
            comodel_name='product.template',
            compute='_compute_product_template_id',
            domain=lambda self: self._dpg_product_template_domain_new(),
            readonly=False,
        )
    product_uom_qty = fields.Float(string='Quantity', default=1.0)
    sale_order_line_wiard_id = fields.Many2one('sale.order.line.wizard')

    product_template_attribute_value_ids = fields.Many2many(
        related='product_id.product_template_attribute_value_ids',
        depends=['product_id'])
    
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', depends=['product_id'])
    
    product_uom = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        compute='_compute_product_uom',
        store=True, readonly=False, precompute=True, ondelete='restrict',
        domain="[('category_id', '=', product_uom_category_id)]")
    
    currency_id = fields.Many2one(
        related='sale_order_line_wiard_id.currency_id',
        depends=['sale_order_line_wiard_id.currency_id'],
        store=True, precompute=True)
    
    company_id = fields.Many2one(
        related="sale_order_line_wiard_id.company_id",
        depends=['sale_order_line_wiard_id.company_id'],
        store=True, precompute=True)

    # store selected sub-attributes as a JSON string
    sub_selection_json = fields.Text(string='Sub attribute selection (JSON)')
    # human readable description of selected sub-attribute values (for UI)
    sub_selection_display = fields.Text(string='Sub attribute selection (display)')

    optional_product_widget = fields.Char()
    is_select_optional_product = fields.Boolean(default=False)



    @api.depends('product_id')
    def _compute_product_template_id(self):
        for line in self:
            if line.sale_order_line_wiard_id.product_sale_type == 'burgtec':
                line.burgtec_product_template_id = line.product_id.product_tmpl_id.id
            elif line.sale_order_line_wiard_id.product_sale_type == 'dpg':
                line.dpg_product_template_id = line.product_id.product_tmpl_id.id
    
    @api.depends('product_id')
    def _compute_product_uom(self):
        for line in self:
            if not line.product_uom or (line.product_id.uom_id.id != line.product_uom.id):
                line.product_uom = line.product_id.uom_id.id

    @api.depends('burgtec_product_template_id','dpg_product_template_id')
    def _compute_product_template(self):
        for record in self:
            if record.burgtec_product_template_id:
                record.product_template_id = record.burgtec_product_template_id.id
            elif record.dpg_product_template_id:
                record.product_template_id = record.dpg_product_template_id.id
            else:
                record.product_template_id = False
            

