from odoo import models

class SaleOrderBOMComponentLineExt(models.Model):
    _inherit = 'sale.order.bom.component.line'

    def action_open_update_parent_line(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Edit Parent Line',
            'res_model': 'sale.order.line',
            'res_id': self.order_line_id.id,
            'view_id': self.env.ref(
                'sale_custom_report.view_sale_order_line_image_description'
            ).id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
            }
        }