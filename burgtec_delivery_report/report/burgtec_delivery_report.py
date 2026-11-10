from odoo import models
from odoo.exceptions import ValidationError


class BurgtecDeliveryReport(models.AbstractModel):
    _name = 'report.burgtec_delivery_report.burgtec_delivery_report'
    _description = 'Burgtec Custom Delivery Report'

    def _get_report_values(self, docids, data=None):

        report = self.env['ir.actions.report']._get_report_from_name('burgtec_delivery_report.burgtec_delivery_report')
        docs = self.env[report.model].browse(docids)

        for doc in docs:
            if not doc.location:
                raise ValidationError('Please Set the Location First!')
            if not doc.qr_url:
                raise ValidationError('Please Enter HubSpot Del.Stage ticket URL to Generate Qrcode!')
            # if not doc.delivery_stage:
            #     raise ValidationError('Please Enter the Delivery Stage Number')

            PurchaseOrder = self.env['purchase.order']
            child_pos = self.env['purchase.order']
            all_parent_po = doc._get_purchase_orders()
            if not all_parent_po:
                raise ValidationError('NO Purchase Order found,Kindly Confirm this Delivery Stage')
            if all_parent_po and all_parent_po.state not in ('purchase', 'done'):
                raise ValidationError('NO Child Purchase Order found,Kindly Confirm Parent PO')
            for picking in all_parent_po.picking_ids:
                children = PurchaseOrder.search([('origin', '=', picking.name)])
                child_pos |= children
        if child_pos:
            # Exclude POs where ALL lines are delivery/installation
            child_pos = child_pos.filtered(
                lambda po: any(not l.product_id.is_delivery_and_installation for l in po.order_line)
            )
            child_pos = child_pos.sorted(lambda po: po.id)
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'company': self.env.company,
            'docs': docs,
            'parent_po': all_parent_po,
            'child_pos': child_pos,
            'total_child_pos': len(child_pos),
        }
