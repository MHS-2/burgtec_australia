from odoo import _, fields, models, api, _, Command
from odoo.exceptions import ValidationError, UserError


class SaleOrderLineWizard(models.TransientModel):
    _inherit='sale.order.line.wizard'

    simple_quote_entry_id = fields.Many2one('simple.quote.entry.wizard')

    pricelist_id = fields.Many2one()
    
    date_order = fields.Datetime()

    currency_id = fields.Many2one()


    def action_add_simple_product(self):
        if not self.sale_order_product_line_wizard_ids:
            raise UserError(_('Kindly Add Products First!'))
        # active_sale_order_line_id = self.env.context.get('active_id')
        # sale_order_line_obj = self.env['sale.order.line'].sudo().browse(active_sale_order_line_id)
        active_simple_order_line_id = self.env.context.get('active_id')
        simple_order_line_obj = self.env['simple.quote.entry.order.line'].sudo().browse(active_simple_order_line_id)
        code_sequence = simple_order_line_obj.sequence
        new_product_sequence = code_sequence + 1
        simple_entry_obj = self.simple_quote_entry_id
        simple_order_lines = simple_entry_obj.simple_quote_entry_order_line_ids.sorted(lambda o: o.sequence)  # Save Before Clearing.

        lines_in_code = simple_order_lines.filtered(lambda l: int(l.line_code_id_value) == simple_order_line_obj.id)
        if lines_in_code:
            last_line = lines_in_code[-1]
            new_product_sequence = last_line.sequence + 1

        lines_to_update = simple_order_lines.filtered(
            lambda l: l.id != active_simple_order_line_id and l.sequence >= new_product_sequence)
        counter = len(self.sale_order_product_line_wizard_ids)
        for line in lines_to_update:
            line.sequence += counter

        # Batch create all lines at once
        if self.sale_order_product_line_wizard_ids:
            create_commands = []
            for product_line in self.sale_order_product_line_wizard_ids:
                simple_order_line_vals = {
                    'simple_quote_entry_id': simple_entry_obj.id,
                    'product_id': product_line.product_id.id if product_line.product_id else product_line.product_template_id.product_variant_id.id,
                    'product_uom_qty': product_line.product_uom_qty,
                    'sequence': new_product_sequence,
                } 
                create_commands.append(Command.create(simple_order_line_vals))
                new_product_sequence += 1
            
            # Single write operation with all create commands
            simple_entry_obj.simple_quote_entry_order_line_ids = create_commands

            return {
                'name': 'Create Quotation Simple Wizard',
                'type': 'ir.actions.act_window',
                'res_model': 'simple.quote.entry.wizard',  # Uses the current wizard transient model
                'view_mode': 'form',
                'res_id': simple_entry_obj.id,        # Keeps the exact same record open
                'target': 'new',          # Forces it to stay/reopen in a pop-up modal
            }