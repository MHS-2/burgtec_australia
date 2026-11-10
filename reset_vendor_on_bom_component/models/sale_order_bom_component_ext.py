from odoo import api, fields, models, tools


class SaleOrderBomComponentExt(models.Model):
    _inherit = 'sale.order.bom.component'

    def action_reset_bom_component_vendors(self):
        for rec in self:
            if rec.freeze_sale_order or rec.auto_lock_sales_quote_upon_project_creation or rec.state == 'sale':
                return
            bom_component_lines = rec.component_line_ids
            if bom_component_lines:
                unfreeze_bom_component_lines = bom_component_lines.filtered(
                    lambda l: not l.display_type and not l.is_product_fully_approved
                )
                if unfreeze_bom_component_lines:
                    for line in unfreeze_bom_component_lines:
                        line.write({
                            'supplier_id': rec.get_product_suppiler(line.product_id),
                        })

    def get_product_suppiler(self, product_id):
        return product_id.seller_ids[:1].partner_id.id

