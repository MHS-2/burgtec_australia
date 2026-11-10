from odoo import fields, models

class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    def sync_component_cost(self):
        for record in self:
            if record.bom_component_id:
                if record.bom_component_id.component_line_ids:
                    # Ignore Fully Approved Product, non product lines and lines with NSCR Record ID.
                    all_lines = record.bom_component_id.component_line_ids.filtered(lambda l: not l.display_type and not l.is_product_fully_approved and not l.nscr_register_id)
                    for line in all_lines:
                        if line.system_cost_per_unit == line.live_unit_cost:
                            if line.product_id.standard_price > 0.0:
                                line.system_cost_per_unit = line.product_id.standard_price
                                line.manual_live_unit_cost = line.product_id.standard_price