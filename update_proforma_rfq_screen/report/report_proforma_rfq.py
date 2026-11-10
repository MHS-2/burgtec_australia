# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields


class ReportProformaRfqVendor(models.AbstractModel):
    _name = 'report.update_proforma_rfq_screen.rfq_vendor_report'
    _description = "Report Proforma RFQ Vendor"

    
    def _get_report_values(self, docids, data=None):
        docs = self.env['component.lines.by.vendor'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'component.lines.by.vendor',
            'docs': docs,
            'current_date': fields.Datetime.now(),
            'datetime': datetime,

        }
