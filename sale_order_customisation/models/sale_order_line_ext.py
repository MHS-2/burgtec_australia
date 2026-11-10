from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, RedirectWarning


class SaleOrderLineExt(models.Model):
    _inherit = 'sale.order.line'

    product_identifier = fields.Integer(compute="_set_unique_identifiers")

    is_defect_group_line = fields.Boolean()

    @api.depends('order_id')
    def _set_unique_identifiers(self):
        set_value = 1
        group_lines = self.order_id.order_line.sorted(lambda o: o.sequence).filtered(lambda l:l.display_type == 'line_section')
        code_lines = self.order_id.order_line.sorted(lambda o: o.sequence).filtered(lambda l:l.display_type == 'line_note')
        product_lines = self.order_id.order_line.sorted(lambda o: o.sequence).filtered(lambda l: not l.display_type)
        
        for line in group_lines:
            line.product_identifier = set_value
            set_value +=1
        set_value = 1

        for line in code_lines:
            line.product_identifier = set_value
            set_value +=1
        set_value = 1

        for line in product_lines:
            line.product_identifier = set_value
            set_value +=1
    # Called by action button to show a wizard
    def action_show_wizard_to_add_code(self):
        # Don't include res_id key for wizards.
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': 'Perform Add Code Action',
            'view_id': self.env.ref('sale_order_customisation.sale_order_line_wizard_add_code_form_view').id,
            'view_mode': 'form',
            'res_model': 'sale.order.line.wizard',
            'context': {
                'dialog_size': 'extra-large',
            }
        }

    def action_show_wizard_to_add_product(self):
        # Don't include res_id key for wizards.
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': 'Perform Add Product Action',
            'view_id': self.env.ref('sale_order_customisation.sale_order_line_wizard_add_product_form_view').id,
            'view_mode': 'form',
            'res_model': 'sale.order.line.wizard',
            'context': {
                'dialog_size': 'extra-large',
                'default_pricelist_id': self.order_id.pricelist_id.id,
                'default_date_order': self.order_id.date_order,
                'default_currency_id': self.currency_id.id,
            }
        }

    def action_show_wizard_to_swap_groups(self):
        # Don't include res_id key for wizards.
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': 'Perform Swap Group Action',
            'view_id': self.env.ref('sale_order_customisation.sale_order_line_wizard_swap_group_form_view').id,
            'view_mode': 'form',
            'res_model': 'sale.order.line.wizard',
            'context': {
                'default_active_group_id': self.id,
                'default_sale_order_id': self.order_id.id,
                'dialog_size': 'extra-large',
            }
        }

    def action_show_wizard_to_swap_codes(self):
        # Don't include res_id key for wizards.
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': 'Perform Swap Code Action',
            'view_id': self.env.ref('sale_order_customisation.sale_order_line_wizard_swap_code_form_view').id,
            'view_mode': 'form',
            'res_model': 'sale.order.line.wizard',
            'context': {
                'default_active_code_id': self.id,
                'default_sale_order_id': self.order_id.id,
                'dialog_size': 'extra-large',
            }
        }
    
    def _compute_display_name(self):
        for record in self:
            if record:
                if record.env.context.get('group_swap'):
                    record.display_name = f"{record.product_identifier} - {record.name}"
                elif record.env.context.get('duplicate_line'):
                    record.display_name = record.product_template_id.name or record.custom_product_name
                else:
                    return super(SaleOrderLineExt,self)._compute_display_name()


    def action_open_copy_wizard(self):
        group = self.env['sale.order.line'].search([
            ('id', '=', self.line_group_id_value)
        ], limit=1)
        section = self.env['sale.order.line'].search([
            ('id', '=', int(self.line_section_id_value))
        ], limit=1)

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


        
        return {
            'name': 'Duplicate Quotation Lines',
            'type': 'ir.actions.act_window',
            'res_model': 'duplicate.quotation.line.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.order_id.id,
                'default_order_id_onchanged': self.order_id.id,
                'default_order_line_id': self.id,
                'default_group_id': group.id,
                'default_section_id': section.id,
                'default_display_name': self.order_id.name,
                'default_quote_type': quote_type,
                'default_is_admin': is_admin,
                'default_is_no_admin_right': is_no_admin_right,
            }
        }
    
    @api.onchange('sequence')
    def _sequence_validation(self):
        error_msg = _('You are not allowed to drag lines manually!. Reload the page to proceed further!')
        reload_view = {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        if self._origin.display_type in ('line_note','line_section'):
            # raise UserError(_('You can not drag Group or Code lines!'))
            raise RedirectWarning(error_msg, reload_view, _('Reload Page'))
    

    @api.model
    def get_add_code_form_view_id(self):
        """Get the form view ID from ir.model.data"""
        view = self.env.ref('sale_order_customisation.sale_order_line_wizard_add_code_form_view', raise_if_not_found=False)
        return view.id if view else False

    @api.model
    def get_swap_group_form_view_id(self):
        """Get the form view ID from ir.model.data"""
        view = self.env.ref('sale_order_customisation.sale_order_line_wizard_swap_group_form_view', raise_if_not_found=False)
        # print(view.id)
        return view.id if view else False

    @api.model
    def get_add_product_form_view_id(self):
        """Get the form view ID from ir.model.data"""
        view = self.env.ref('sale_order_customisation.sale_order_line_wizard_add_product_form_view', raise_if_not_found=False)
        # print(view.id)
        return view.id if view else False
    
    @api.model
    def get_swap_code_form_view_id(self):
        """Get the form view ID from ir.model.data"""
        view = self.env.ref('sale_order_customisation.sale_order_line_wizard_swap_code_form_view', raise_if_not_found=False)
        # print(view.id)
        return view.id if view else False