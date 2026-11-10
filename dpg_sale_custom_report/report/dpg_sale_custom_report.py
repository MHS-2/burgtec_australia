from odoo import api, models, _
from odoo.exceptions import UserError, ValidationError
import base64


class SaleQuoteDpgReport(models.AbstractModel):
    _name = 'report.dpg_sale_custom_report.dpg_sale_quote'
    _description = "DPG Sale Custom Report"

    def _get_report_values(self, docids, data=None):

        report = self.env['ir.actions.report']._get_report_from_name('dpg_sale_custom_report.dpg_sale_quote')
        # get the records selected for this rendering of the report
        docs = self.env[report.model].browse(docids)
        for doc in docs:
            if not doc.order_line.filtered(lambda l: not l.display_type):
                raise UserError(_("There are No Product Lines in Sale Order."))

            if not doc.opportunity_id.series_sequence_id.id == 9:
                raise ValidationError(_("This Report is only for Series Sequence 9."))

        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'company': self.env.company,
            'docs': docs
        }
