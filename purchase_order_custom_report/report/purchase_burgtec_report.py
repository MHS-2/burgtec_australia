from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PurchaseBurgtecReport(models.AbstractModel):
    _name = 'report.purchase_order_custom_report.burgtec_purchase_report'
    _description = 'Burgtec Custom Purchase Report'

    def _get_report_values(self, docids, data=None):
        # get the report action back as we will need its data
        report = self.env['ir.actions.report']._get_report_from_name('purchase_order_custom_report.burgtec_purchase_report')
        # get the records selected for this rendering of the report
        docs = self.env[report.model].browse(docids)
        for order in docs:
            if order.shipping_address_type == 'manual' and not order.manual_shipping_address:
                raise UserError(_(
                    "Please Add Manual Shipping Address First!!"))

        return {
            'doc_ids': docids,
            'doc_model': 'purchase.order',
            'company': self.env.company,
            'docs': docs,
        }