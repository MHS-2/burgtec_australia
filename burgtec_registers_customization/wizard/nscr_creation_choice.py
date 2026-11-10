from odoo import models, fields, _


class NscrCreationChoice(models.TransientModel):
    _name = 'nscr.creation.choice'
    _description = 'NSCR Creation Choice Wizard'

    bom_component_line_id = fields.Many2one('sale.order.bom.component.line', string='BOM Component Line')

    def create_new_nscr_register_entry(self):
        """Opens the NSCR Register form to create a new entry"""
        self.ensure_one()
        bom_line = self.bom_component_line_id
        return {
            'name': _('NSCR Register Entry'),
            'res_id': bom_line.nscr_register_id.id,
            'view_mode': 'form',
            'res_model': 'nscr.register',
            'type': 'ir.actions.act_window',
            'context': {
                'active_id': bom_line.id,
                'default_order_id': bom_line.component_id.order_id.id,
                'default_order_line_id': bom_line.order_line_id.id,
                'default_bom_component_id': bom_line.component_id.id,
                'default_bom_component_line_id': bom_line.id,
                'default_nscr_date': fields.Datetime.now(),
                'default_product_variant_id': bom_line.order_line_id.product_id.id,
                'default_product_component_id': bom_line.product_id.id,
                'default_user_id': self.env.user.id,
            }
        }

    def assign_existing_nscr_register_entry(self):
        """Opens the existing NSCR selection wizard"""
        self.ensure_one()
        bom_line = self.bom_component_line_id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'component.existing.nscr.selection',
            'view_id': self.env.ref(
                'burgtec_registers_customization.view_component_existing_nscr_selection_wizard_form').id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': bom_line.id,
                'default_product_component_id': bom_line.product_id.id,
                'dialog_size': 'extra-large',
                'default_bom_component_line_id': bom_line.id
            }
        }