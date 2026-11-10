# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from markupsafe import Markup
from odoo.http import request
import math


_logger = logging.getLogger(__name__)


class BulkActionOperations(models.TransientModel):
    _name = 'bulk.action.operations'
    _description = 'BulkActionOperations'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    bulk_lines = fields.One2many('bulk.action.operation.line', 'bulk_action_operation_id')
    operation_type = fields.Selection([('delete', 'Delete'), ('duplicate_with_group_and_code', 'Duplicate with Group & Code'), ('duplicate', 'Duplicate'), ('add_margin', 'Add Margin')],
                                      string='Operation Type')
    global_select = fields.Boolean(default=False, string='Global Select')
    margin_percentage = fields.Float(string='Margin %')

    target_sale_order_id = fields.Many2one('sale.order', string="Target Sale Order")
    line_group_id_value = fields.Integer(string='Line Group Id Value', related='group_id.id',store=True)

    group_id = fields.Many2one(
        'sale.order.line',
        string='Group',
        domain="[('order_id', '=', target_sale_order_id), ('display_type', '=', 'line_section')]"
    )
    section_id = fields.Many2one(
        'sale.order.line',
        string='Code',
        domain="[('order_id', '=', target_sale_order_id), ('display_type', '=', 'line_note'),('line_group_id_value', '=', group_id) ]"
    )

    quote_type = fields.Selection([
        ('sales_quote','Sales Quote'),
        ('project_quote','Project Quote'),
    ])

    is_admin = fields.Boolean()

    is_no_admin_right = fields.Boolean()

    show_warning = fields.Boolean(default=False)

    @api.onchange('target_sale_order_id')
    def onchange_sale_order(self):
        if self.target_sale_order_id.id != self.sale_order_id.id:
            self.show_warning = True
        else:
            self.show_warning = False

        if self.target_sale_order_id.id != self.group_id.order_id.id:
            self.group_id = None
        if self.target_sale_order_id.id != self.section_id.order_id.id:
            self.section_id = None
    
    @api.onchange('group_id')
    def onchange_group_id(self):
        section_group_id = int(self.section_id.line_group_id_value)
        current_group_id = self.group_id.id
        if section_group_id != current_group_id:
            self.section_id = None


    @api.onchange('global_select')
    def _onchange_is_check(self):
        for rec in self:
            product_lines = rec.bulk_lines.filtered(lambda l: not l.display_type)
            if product_lines:
                if rec.global_select:
                    product_lines.update({
                        'is_check': True,
                    })
                else:
                    product_lines.update({
                        'is_check': False,
                    })

    def action_add_bulk_margin(self):
        sale_order  = self.sale_order_id
        applied_margin = self.margin_percentage
        if applied_margin < 0:
            raise ValidationError('Applied Margin Cant be Negative')
        applied_margin_in_decimal = applied_margin / 100
        new_applied_margin = 1 - applied_margin_in_decimal
        selected_lines_to_add_margin = self.bulk_lines.filtered(lambda l: l.is_check)
        if not selected_lines_to_add_margin:
            raise UserError('You Have not Selected Any Lines')
        for line in selected_lines_to_add_margin:
            matching_bom_line = sale_order.bom_component_id.component_line_ids.filtered(lambda l:l.is_parent and line.order_line_id == l.order_line_id)
            if matching_bom_line:
                matching_bom_line_manual_live_unt_cost = matching_bom_line.manual_live_unit_cost
                resultant_margin = matching_bom_line_manual_live_unt_cost / new_applied_margin if new_applied_margin else 0.0
                sale_price_rounded_off = math.floor((resultant_margin + 5) / 10) * 10
                line.order_line_id.sudo().write({
                    'price_unit' : sale_price_rounded_off,
                    'applied_margin' : applied_margin / 100,
                })
        if sale_order.bom_component_id:
            sale_order.bom_component_id.update_component_lines()
        message_body = Markup(f"""
                       <div style="background-color: #27D3F5; border: 2px solid #009EC4; border-radius: 5px; padding: 15px; margin: 10px 0;">
                           <h4 style="color: #c62828; margin: 0 0 10px 0;">
                               <span style="font-size: 18px;">📈</span> Margin Applied Action
                           </h4>
                           <p style="margin: 5px 0; color: #333; font-weight: bold;">
                               A Margin of {int(applied_margin)}% has been Successfully Applied on the Sale Order Lines
                           </p>
                           <p style="margin: 10px 0 0 0; font-size: 12px; color: #333;">
                               Margin Applied by: {self.env.user.name} on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                           </p>
                       </div>
                   """)
        sale_order.message_post(
            body=message_body,
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def default_get(self, fields_list):
        """Populate wizard lines from sale order"""
        res = super(BulkActionOperations, self).default_get(fields_list)

        quote_type = False
        is_admin=False
        is_no_admin_right = False
        if self.env.user.has_group('sales_team.group_sale_manager') and self.env.user.has_group('project.group_project_manager'):
            # quote_type = False
            quote_type = 'sales_quote'
            is_admin= True
        elif self.env.user.has_group('sales_team.group_sale_manager') and not self.env.user.has_group('project.group_project_manager'):
            # print("Sales Admin") ONly
            quote_type = 'sales_quote'

        elif self.env.user.has_group('project.group_project_manager') and not self.env.user.has_group('sales_team.group_sale_manager'):
            # print("Project Admin") only
            quote_type = 'project_quote'
        else:
            is_no_admin_right = True

        # Get the active sale order
        sale_order_id = self.env.context.get('active_id')
        if not sale_order_id:
            raise UserError(_('No Sale Order found in context.'))

        sale_order = self.env['sale.order'].browse(sale_order_id)
        res['sale_order_id'] = sale_order_id
        sale_order_lines = sale_order.order_line

        # Prepare lines from sale order lines
        line_vals = []
        for line in sale_order_lines:
            line_vals.append((0, 0, {
                'sequence': line.sequence,
                'name': line.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'currency_id': line.currency_id.id,
                'custom_product_name': line.custom_product_name,
                'order_line_id': line.id,
                'display_type': line.display_type,
                'is_check': False,
                'line_group_id_value':line.line_group_id_value,
                'line_section_id_value': line.line_section_id_value,
            }))

        # res['bulk_lines'] = line_vals
        res.update({
            'bulk_lines': line_vals,
            'quote_type':quote_type,
            'is_admin':is_admin,
            'is_no_admin_right':is_no_admin_right,
            'target_sale_order_id':sale_order_id
        })

        return res

    def action_bulk_delete(self):
        """Delete selected lines from sale order"""
        selected_lines = self.bulk_lines.filtered(lambda l: l.is_check)
        if not selected_lines:
            raise UserError(_('No lines selected for deletion.'))

        # Get the original sale order lines
        order_lines_to_delete = selected_lines.mapped('order_line_id')
        count = len(order_lines_to_delete)

        # Prepare product list
        product_list = ''
        for line in order_lines_to_delete:
            product_name = line.product_id.display_name or line.name or 'N/A'
            qty = line.product_uom_qty
            product_list += f'<li>{product_name} (Qty: {qty})</li>'

        # Delete from sale order
        order_lines_to_delete.unlink()

        # Post message on sale order
        message_body = Markup(f"""
            <div style="background-color: #ffcdd2; border: 2px solid #c62828; border-radius: 5px; padding: 15px; margin: 10px 0;">
                <h4 style="color: #c62828; margin: 0 0 10px 0;">
                    <span style="font-size: 18px;">🗑️</span> Bulk Delete Action
                </h4>
                <p style="margin: 5px 0; color: #333; font-weight: bold;">
                    {count} Sale Order Line(s) have been deleted.
                </p>
                <details style="margin-top: 10px;">
                    <summary style="cursor: pointer; color: #c62828; font-weight: bold;">
                        View Deleted Products
                    </summary>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        {product_list}
                    </ul>
                </details>
                <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
                    Deleted by: {self.env.user.name} on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        """)

        self.sale_order_id.message_post(
            body=message_body,
            subject='Bulk Delete Action',
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        # Close wizard and reload sale order
        return {'type': 'ir.actions.act_window_close'}

    def action_duplicate(self):
        """Duplicate selected lines from sale order and theri bom component lines."""
        selected_lines = self.bulk_lines.filtered(lambda l: l.is_check)
        if not selected_lines:
            raise UserError(_('No lines selected for duplication.'))
        
        if not self.operation_type == 'duplicate_with_group_and_code' and not self.group_id:
            raise UserError(_('Group is not selected!.'))
        if not self.operation_type == 'duplicate_with_group_and_code' and not self.section_id:
            raise UserError(_('Code is not selected!.'))
        # original_line = self.order_line_id
        root_url = request.httprequest.url_root
        sale_order = self.sale_order_id
        target_sale_order = self.target_sale_order_id
        target_sale_order_lines = target_sale_order.order_line
        bom_id = sale_order.bom_component_id # Active Sale Order BOM ID
        bom_component_line_ids = bom_id.component_line_ids
        new_line_sequence = 10
        # Get the original sale order lines
        order_lines_to_duplicate = selected_lines.mapped('order_line_id')
        count = len(order_lines_to_duplicate)
        duplication_statement = f"{count} Sale Order Line(s) have been duplicated."
        groupid = False
        sectionid = False
        groups_list = selected_lines.mapped('line_group_id_value')
        sections_list = selected_lines.mapped('line_section_id_value')
        groups_list = [int(item) for item in groups_list]
        sections_list = [int(item) for item in sections_list]
        selected_lines_with_group_and_code = False


        if not bom_id:
            raise UserError(_('Kindly Save BOM Components for this qoute before duplicating a product!'))
        if target_sale_order.id != sale_order.id: #Duplicating to a different sale order.
            duplication_statement = f"{count} Sale Order Line(s) have been duplicated to <a href='{root_url}/odoo/sale.order/{target_sale_order.id}'>{target_sale_order.burgtec_quote_reference}</a>."
            if not target_sale_order.bom_component_id:
                raise UserError(_('Kindly Save BOM Component of the selected Sale Order -> %s before duplicating a product!', target_sale_order.burgtec_quote_reference))
        max_seq = max(bom_component_line_ids.mapped('sequence'))

        if self.operation_type == 'duplicate_with_group_and_code':
            group_code_record = self.bulk_lines.filtered(lambda b:not b.is_check and (b.order_line_id.id in groups_list or b.order_line_id.id in sections_list))  
            group_code_record.write({
                'is_check':True
            })
            selected_lines_with_group_and_code = self.bulk_lines.filtered(lambda l: l.is_check)
            order_lines_to_duplicate = selected_lines_with_group_and_code.mapped('order_line_id')
            count = len(order_lines_to_duplicate)
            duplication_statement = f"{count} Sale Order Line(s) have been duplicated."
            if target_sale_order.id != sale_order.id: #Duplicating to a different sale order.
                duplication_statement = f"{count} Sale Order Line(s) have been duplicated to <a href='{root_url}/odoo/sale.order/{target_sale_order.id}'>{target_sale_order.burgtec_quote_reference}</a>."
            new_line_vals = False
            last_target_order_line = False

            # Prepare product list
            product_list = ''
            for line in order_lines_to_duplicate:
                product_name = line.product_id.display_name or line.name or 'N/A'
                qty = line.product_uom_qty
                if not line.display_type:
                    product_list += f'<li>{product_name} (Qty: {qty})</li>'
                if line.display_type == 'line_section':
                    product_list += f'<li>{product_name} <strong>(Group)</strong></li>'
                if line.display_type == 'line_note':
                    product_list += f'<li>{product_name} <strong>(Code)</strong></li>'

            # Post message on sale order
            message_body = Markup(f"""
                <div style="background-color: #f0cffa; border: 2px solid #d75bfc; border-radius: 5px; padding: 15px; margin: 10px 0;">
                    <h4 style="color: #2d003b; margin: 0 0 10px 0;">
                        <span style="font-size: 18px;"> <i class="fa fa-clone" aria-hidden="true"></i> </span> Bulk Duplicate With Group & Code Action
                    </h4>
                    <p style="margin: 5px 0; color: #000000; font-weight: bold;">
                        {duplication_statement}
                    </p>
                    <details style="margin-top: 10px;">
                        <summary style="cursor: pointer; color: #2d003b; font-weight: bold;">
                            View Duplicated Line(s) Details
                        </summary>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            {product_list}
                        </ul>
                    </details>
                    <p style="margin: 10px 0 0 0; font-size: 12px; color: #000000;">
                        Duplicated by: {self.env.user.name} on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>
            """)

            if target_sale_order_lines:
                last_target_order_line = target_sale_order_lines.sorted(lambda o:o.sequence)[-1] 
                if last_target_order_line.display_type not in ('line_note','line_section'): # PRODUCT LINE.
                    new_line_sequence = last_target_order_line.sequence + 1
                else:
                    line_type = 'Group' if last_target_order_line.display_type == 'line_section' else 'Code'
                    raise UserError(_(
                        "Cannot Add Lines to The Sale Order\n\n"
                        "The last order line must be a product line, but the following %(line_type)s line was found:\n"
                        "→ %(line_name)s\n\n"
                        "Please ensure the sale order ends with a product line before proceeding.",
                        line_type=line_type,
                        line_name=last_target_order_line.name or _("(Unnamed Line)"),
                    ))
            for original_line in order_lines_to_duplicate:
                if original_line.display_type in ('line_note','line_section'):
                    new_line_vals = original_line.copy_data()[0]  # Returns a list of dicts
                    new_line_vals['order_id'] = target_sale_order.id
                    new_line_vals['sequence'] = new_line_sequence
                    new_line_vals.pop('id', None)
                    # Create the new sale order line
                    res = self.env['sale.order.line'].create(new_line_vals)
                    new_line_sequence+=1
                    continue
                else:
                    bom_component_lines = bom_component_line_ids.filtered(lambda l:l.order_line_id.id == original_line.id)
                    # Create a copy of the original line
                    new_line_vals = original_line.copy_data()[0]  # Returns a list of dicts
                    new_bom_line_vals = bom_component_lines.copy_data()
                    # print('New Line Vals',new_line_vals)
                    new_line_vals['order_id'] = target_sale_order.id
                    new_line_vals['sequence'] = new_line_sequence

                    new_line_vals.pop('id', None)
                    # Create the new sale order line
                    res = self.env['sale.order.line'].create(new_line_vals)
                    new_line_sequence+=1

                    for bom_val_dict in new_bom_line_vals:
                        if target_sale_order.id != sale_order.id: #Duplicating to a different sale order.
                            bom_val_dict['component_id'] = target_sale_order.bom_component_id.id
                        bom_val_dict['order_line_id'] = res.id
                        max_seq +=1
                        bom_val_dict['sequence'] = max_seq


                    # print(new_bom_line_vals)
                    bom_res = self.env['sale.order.bom.component.line'].sudo().create(new_bom_line_vals)

                    # if bom_res:

            _logger.info(f" ---->  Updating Component Lines After Duplicating %d Sale Order Lines! <----",count)
            target_sale_order.bom_component_id.update_component_lines()
            _logger.info(" ---->  Component Lines Updated After Duplicating %d Sale Order Lines! <----",count)

            self.sale_order_id.message_post(
            body=message_body,
            subject='Bulk Duplicate Action',
            message_type='notification',
            subtype_xmlid='mail.mt_note',)




        if self.operation_type == 'duplicate':
             # Prepare product list
            product_list = ''
            for line in order_lines_to_duplicate:
                product_name = line.product_id.display_name or line.name or 'N/A'
                qty = line.product_uom_qty
                product_list += f'<li>{product_name} (Qty: {qty})</li>'

            # Post message on sale order
            message_body = Markup(f"""
                <div style="background-color: #B8FFB8; border: 2px solid #7CA37C; border-radius: 5px; padding: 15px; margin: 10px 0;">
                    <h4 style="color: #114F11; margin: 0 0 10px 0;">
                        <span style="font-size: 18px;"> <i class="fa fa-clone" aria-hidden="true"></i> </span> Bulk Duplicate Action
                    </h4>
                    <p style="margin: 5px 0; color: #000000; font-weight: bold;">
                        {duplication_statement}
                    </p>
                    <details style="margin-top: 10px;">
                        <summary style="cursor: pointer; color: #114F11; font-weight: bold;">
                            View Duplicated Products
                        </summary>
                        <p style="margin: 10px 0; padding-left: 20px; color: #850000;">
                            <strong>Group :</strong> {self.group_id.name}
                        </p>
                        <p style="margin: 10px 0; padding-left: 20px; color: #004CA3;">
                            <strong>Code :</strong> {self.section_id.name}
                        </p>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            {product_list}
                        </ul>
                    </details>
                    <p style="margin: 10px 0 0 0; font-size: 12px; color: #000000;">
                        Duplicated by: {self.env.user.name} on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>
            """)
            for original_line in order_lines_to_duplicate:
                bom_component_lines = bom_component_line_ids.filtered(lambda l:l.order_line_id.id == original_line.id)
                # print(bom_component_lines.mapped('product_id.name'))
                # print(bom_component_lines.mapped('is_parent'))

                # Create a copy of the original line
                new_line_vals = original_line.copy_data()[0]  # Returns a list of dicts
                new_bom_line_vals = bom_component_lines.copy_data()
                # print('New Line Vals',new_line_vals)
                new_line_vals['order_id'] = target_sale_order.id

                new_line_sequence = self.section_id.sequence + 1

                lines_in_code = target_sale_order.order_line.sorted(lambda o: o.sequence).filtered(lambda l: int(l.line_section_id_value) ==  self.section_id.id)
                if lines_in_code:
                    last_line = lines_in_code[-1]
                    new_line_sequence = last_line.sequence + 1


                new_line_vals['sequence'] = new_line_sequence
                for line in target_sale_order_lines:
                    if line.sequence >= new_line_sequence:
                        line.sequence += 1
                



                # new_line_vals['line_group_id_value'] = self.group_id.id
                new_line_vals.pop('id', None)
                # Create the new sale order line
                res = self.env['sale.order.line'].create(new_line_vals)

                for bom_val_dict in new_bom_line_vals:
                    if target_sale_order.id != sale_order.id: #Duplicating to a different sale order.
                        bom_val_dict['component_id'] = target_sale_order.bom_component_id.id
                    bom_val_dict['order_line_id'] = res.id
                    max_seq +=1
                    bom_val_dict['sequence'] = max_seq


                # print(new_bom_line_vals)
                bom_res = self.env['sale.order.bom.component.line'].sudo().create(new_bom_line_vals)

                # if bom_res:

            _logger.info(f" ---->  Updating Component Lines After Duplicating %d Sale Order Lines! <----",count)
            target_sale_order.bom_component_id.update_component_lines()
            _logger.info(" ---->  Component Lines Updated After Duplicating %d Sale Order Lines! <----",count)

            self.sale_order_id.message_post(
            body=message_body,
            subject='Bulk Duplicate Action',
            message_type='notification',
            subtype_xmlid='mail.mt_note',)

                # bom_id.update_component_lines()


        return {'type': 'ir.actions.act_window_close'}


class BulkActionOperationLines(models.TransientModel):
    _name = 'bulk.action.operation.line'
    _description = 'BulkAction Operation Line'

    is_check = fields.Boolean()
    name = fields.Char()
    sequence = fields.Integer()
    product_id = fields.Many2one('product.product')
    product_uom_qty = fields.Float()
    price_unit = fields.Float()
    price_subtotal = fields.Monetary()
    currency_id = fields.Many2one('res.currency')
    custom_product_name = fields.Char()
    order_line_id = fields.Many2one('sale.order.line')
    display_type = fields.Selection(
        selection=[
            ('line_section', "Section"),
            ('line_note', "Note"),
        ])
    bulk_action_operation_id = fields.Many2one('bulk.action.operations')
    line_group_id_value = fields.Char()
    line_section_id_value = fields.Char()


    @api.onchange('is_check')
    def onchange_check(self):
        if self.is_check and self.bulk_action_operation_id.operation_type == 'duplicate_with_group_and_code':
            group_code_record = self.bulk_action_operation_id.bulk_lines.filtered(lambda b:not b.is_check and (b.order_line_id.id == int(self.line_group_id_value) or b.order_line_id.id == int(self.line_section_id_value)))
            if group_code_record:
                for rec in group_code_record:
                    rec.is_check = True
