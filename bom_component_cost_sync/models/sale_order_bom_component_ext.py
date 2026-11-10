from odoo import fields, models, _
from odoo.exceptions import ValidationError, UserError


class SaleOrderBOMComponentExt(models.Model):
    _inherit = 'sale.order.bom.component'

    def sync_component_cost(self):
        for record in self:
            if record.component_line_ids:
                # Ignore Fully Approved Product, non product lines and lines with NSCR Record ID.
                all_lines = record.component_line_ids.filtered(
                    lambda l: not l.display_type and not l.is_product_fully_approved and not l.nscr_register_id)
                for line in all_lines:
                    if line.system_cost_per_unit == line.live_unit_cost:
                        if line.product_id.standard_price > 0.0:
                            line.system_cost_per_unit = line.product_id.standard_price
                            line.manual_live_unit_cost = line.product_id.standard_price


    def action_bulk_update_component_cost(self):
        for rec in self:
            bom_component_lines = rec.component_line_ids
            if not bom_component_lines:
                raise UserError(_("Dont have any component lines"))
            selected_component_lines = bom_component_lines.filtered(lambda l: l.is_component_line_selected)
            if not selected_component_lines:
                raise UserError(_("You do not have selected any component lines!"))
            return {
                'type': 'ir.actions.act_window',
                'name': 'Bulk Cost Update',
                'res_model': 'bom.component.bulk.cost.update.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_component_id': self.id,
                    'active_id': self.id,
                    'default_bom_component_lines_ids': selected_component_lines.ids,
                    'active_model': 'sale.order.bom.component',
                    'dialog_size': 'extra-large',
                }
            }


class SaleOrderBOMComponentLineExt(models.Model):
    _inherit = 'sale.order.bom.component.line'

    is_component_line_selected = fields.Boolean(string='Select Component')
