from odoo import models, fields, api


class PurchaseBulkDateWizard(models.TransientModel):
    _name = 'purchase.bulk.date.wizard'
    _description = 'Bulk Update Purchase Order Expected Arrival Date'

    planned_date = fields.Datetime(
        string='Expected Arrival Date',
        required=True,
        default=fields.Datetime.now
    )
    purchase_order_ids = fields.Many2many(
        'purchase.order',
        string='Purchase Orders'
    )

    def action_assign_date(self):
        """Assign the selected date to all purchase orders"""
        self.ensure_one()
        if self.purchase_order_ids and self.planned_date:
            self.purchase_order_ids.write({
                'date_planned': self.planned_date
            })
        return {'type': 'ir.actions.act_window_close'}