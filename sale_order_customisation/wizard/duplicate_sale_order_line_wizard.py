# -*- coding: utf-8 -*-
from email.policy import default
import logging
_logger = logging.getLogger(__name__)
from odoo import api, fields, models, _
from odoo.addons.sale_purchase_inter_company_rules.models.sale_order import sale_order
from odoo.exceptions import UserError


class DuplicateQuotationLineWizard(models.TransientModel):
    """ This model represents duplicate.quotation.line.wizard."""
    _name = 'duplicate.quotation.line.wizard'
    _description = 'DuplicateQuotationLineWizard'

    show_warning = fields.Boolean(default=False)
    display_name = fields.Char("Name")
    order_id = fields.Many2one('sale.order', string='Sale Order', required=True)
    order_id_onchanged = fields.Many2one('sale.order', string='Sale Order Changed', required=True)
    order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line',domain="[('order_id', '=', order_id)]", required=True)
    group_id = fields.Many2one(
        'sale.order.line',
        string='Group',
        domain="[('order_id', '=', order_id), ('display_type', '=', 'line_section')]", required=True
    )
    line_group_id_value = fields.Integer(string='Line Group Id Value', related='group_id.id',store=True)
    section_id = fields.Many2one(
        'sale.order.line',
        string='Code',
        domain="[('order_id', '=', order_id), ('display_type', '=', 'line_note'),('line_group_id_value', '=', group_id) ]", required=True
    )

    quote_type = fields.Selection([
        ('sales_quote','Sales Quote'),
        ('project_quote','Project Quote'),
    ])

    is_admin = fields.Boolean(default=False)

    is_no_admin_right = fields.Boolean(default=False)

    def action_duplicate(self):
        self.ensure_one()
        original_line = self.order_line_id
        sale_order = self.order_id
        bom_id = original_line.order_id.bom_component_id # Active Sale Order BOM ID
        bom_component_line_ids = bom_id.component_line_ids
        new_line_sequence = 10

        if not bom_id:
            raise UserError(_('Kindly Save BOM Components for this qoute before duplicating a product!'))
        if not original_line.order_id.id == sale_order.id: #Duplicating to a different sale order.
            if not sale_order.bom_component_id:
                raise UserError(_('Kindly Save BOM Component of the selected Sale Order -> %s before duplicating a product!', sale_order.display_name))
        max_seq = max(bom_component_line_ids.mapped('sequence'))
        bom_component_lines = bom_component_line_ids.filtered(lambda l:l.order_line_id.id == original_line.id)



        # print(bom_component_lines.mapped('product_id.name'))
        # print(bom_component_lines.mapped('is_parent'))

        # Create a copy of the original line
        new_line_vals = original_line.copy_data()[0]  # Returns a list of dicts
        new_bom_line_vals = bom_component_lines.copy_data()
        # print('New Line Vals',new_line_vals)
        new_line_vals['order_id'] = sale_order.id

        new_line_sequence = self.section_id.sequence + 1

        lines_in_code = sale_order.order_line.sorted(lambda o: o.sequence).filtered(lambda l: int(l.line_section_id_value) ==  self.section_id.id)
        if lines_in_code:
            last_line = lines_in_code[-1]
            new_line_sequence = last_line.sequence + 1


        new_line_vals['sequence'] = new_line_sequence
        for line in sale_order.order_line:
            if line.sequence >= new_line_sequence:
                line.sequence += 1
        



        # new_line_vals['line_group_id_value'] = self.group_id.id
        new_line_vals.pop('id', None)
        # Create the new sale order line
        res = self.env['sale.order.line'].create(new_line_vals)

        for bom_val_dict in new_bom_line_vals:
            if not original_line.order_id.id == sale_order.id: #Duplicating to a different sale order.
                bom_val_dict['component_id'] = sale_order.bom_component_id.id
            bom_val_dict['order_line_id'] = res.id
            max_seq +=1
            bom_val_dict['sequence'] = max_seq


        # print(new_bom_line_vals)
        bom_res = self.env['sale.order.bom.component.line'].sudo().create(new_bom_line_vals)

        if bom_res:
            _logger.info(" ---->  Updating Component Lines After Duplicating! <----")
            bom_res.component_id.update_component_lines()
            _logger.info(" ---->  Component Lines Updated After Duplicating! <----")

        # bom_id.update_component_lines()


        return {'type': 'ir.actions.act_window_close'}


    @api.onchange('order_id')
    def onchange_sale_order(self):
        if self.order_id.id != self.order_id_onchanged.id:
            self.show_warning = True
        else:
            self.show_warning = False

        if self.order_id.id != self.group_id.order_id.id:
            self.group_id = None
        if self.order_id.id != self.section_id.order_id.id:
            self.section_id = None

    @api.onchange('group_id')
    def onchange_group_id(self):
        section_group_id = int(self.section_id.line_group_id_value)
        current_group_id = self.group_id.id
        if section_group_id != current_group_id:
            self.section_id = None
