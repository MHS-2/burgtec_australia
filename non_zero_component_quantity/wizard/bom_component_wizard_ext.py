from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.fields import Many2one


class BOMComponentWizardExt(models.TransientModel):
    _inherit = 'bom.component.wizard'

    def action_add_components(self):
        """Add selected components to the BOM"""
        if not self.component_line_ids:
            raise ValidationError("Please add at least one component.")

        # Filter out section lines and get only actual component lines
        component_lines_to_add = self.component_line_ids.filtered(
            lambda line: line.display_type != 'line_section' and line.product_id and line.product_qty > 0
        )

        if not component_lines_to_add:
            raise ValidationError("Please add at least one valid component.")

        product_ids = component_lines_to_add.mapped('product_id').ids

        if len(component_lines_to_add) != len(product_ids):
            raise ValidationError(_("You cannot add the same component more than once."))

        parent_bom_line_id = self.parent_line_id
        child_lines = self.component_id.component_line_ids.filtered(
            lambda l: not l.is_parent and l.parent_product_id == parent_bom_line_id.product_id.product_tmpl_id
                      and l.order_line_id == parent_bom_line_id.order_line_id)
        child_product_ids = child_lines.mapped('product_id')

        already_exists = component_lines_to_add.filtered(
            lambda line: line.product_id in child_product_ids
        )
        if already_exists:
            product_names = '\n- '.join(already_exists.mapped('product_id.display_name'))
            raise ValidationError(
                f"The following product(s) are already added as components:\n- {product_names}"
            )

        # Count how many lines we're adding
        lines_to_add_count = len(component_lines_to_add)

        # Shift existing lines down to make room for new lines
        # Find all lines that come after the parent line
        existing_lines = self.env['sale.order.bom.component.line'].search([
            ('component_id', '=', self.component_id.id),
            ('sequence', '>', self.parent_line_sequence)
        ])

        # Update sequences of existing lines (shift them down)
        for line in existing_lines:
            line.sequence += lines_to_add_count

        # Create new component lines with sequential numbering
        sequence_counter = self.parent_line_sequence + 1

        for line in component_lines_to_add:
            self.env['sale.order.bom.component.line'].create({
                'component_id': self.component_id.id,
                'parent_product_id': self.parent_product_id.id if self.parent_product_id else False,
                'order_line_id': self.parent_line_id.order_line_id.id if self.parent_line_id.order_line_id else False,
                'product_id': line.product_id.id,
                'product_qty': line.product_qty * self.parent_line_id.product_qty if self.parent_line_id.product_qty else line.product_qty,
                'unit_component_quantity': line.product_qty,
                # Fixed: Use list_price instead of price_unit
                # 'unit_sale_price' : line.product_id.list_price,
                # 'total_sale_price': (line.product_qty * self.parent_line_id.product_qty) * line.product_id.list_price,
                'system_cost_per_unit': (line.product_qty * self.parent_line_id.product_qty) * (
                        line.product_id.standard_price or 0.0),
                'manual_live_unit_cost': line.product_id.standard_price or 0.0,
                'live_unit_cost': (line.product_qty * self.parent_line_id.product_qty) * (
                        line.product_id.standard_price or 0.0),
                'is_parent': False,
                'is_other_than_bom': True,
                'sequence': sequence_counter,
                'supplier_id': self.get_product_suppiler(line.product_id),

            })
            sequence_counter += 1
        self.component_id.onchange_component_line_ids()

        return {'type': 'ir.actions.act_window_close'}

    def get_product_suppiler(self, product_id):
        if product_id.seller_ids:
            return product_id.seller_ids[0].partner_id.id
        return False
