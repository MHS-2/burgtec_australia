from odoo import models, fields, api, _


class PurchaseOrderExt(models.Model):
    _inherit = 'purchase.order'

    shipping_address_type = fields.Selection([
        ('pickup', 'Pick Up'),
        ('burgtec_vendor', 'Burgtec Vendor'),
        ('manual', 'Manual Entry')
    ])

    manual_shipping_address = fields.Char(string='Manual Shipping Address')

    is_burgtec_vendor = fields.Boolean(string='Burgtec Vendor',compute='_compute_is_burgtec_vendor', store=True)

    po_sent_date = fields.Date()

    since_sent_days = fields.Integer(string="Since PO Sent Days")

    @api.depends('partner_id')
    def _compute_is_burgtec_vendor(self):
        for order in self:
            partner_name = order.partner_id.name or ''
            if 'burgtec' in partner_name.lower():
                order.shipping_address_type = 'burgtec_vendor'
                order.is_burgtec_vendor = True
            else:
                if not order.shipping_address_type == 'pickup':
                    order.is_burgtec_vendor = False
                    order.shipping_address_type = 'manual'
                if order.shipping_address_type == 'pickup':
                    order.is_burgtec_vendor = False
                    order.shipping_address_type = 'pickup'



    def _get_send_email_report_xmlid(self):
        self.ensure_one()
        if self.state in ('draft', 'sent'):
            return 'purchase_order_custom_report.action_burgtec_purchase_report'
        return 'purchase_order_custom_report.action_burgtec_purchase_report'

    def _build_send_email_report_attachments(self):
        Attachment = self.env['ir.attachment']
        attachment_ids = []
        for order in self:
            report = self.env.ref(order._get_send_email_report_xmlid(), raise_if_not_found=False)
            if not report:
                continue
            pdf_content, _content_type = report._render_qweb_pdf(report.report_name, [order.id])
            label = _('Request for Quotation') if order.state in ('draft', 'sent') else _('Purchase Order')
            filename = '%s - %s.pdf' % (label, (order.burgtec_purchase_reference or '').replace('/', '_'))
            attachment = Attachment.create({
                'name': filename,
                'type': 'binary',
                'raw': pdf_content,
                'res_model': 'purchase.order',
                'res_id': order.id,
                'mimetype': 'application/pdf',
            })
            attachment_ids.append(attachment.id)
        return attachment_ids

    def action_rfq_send(self):
        action = super().action_rfq_send()
        if not isinstance(action, dict) or action.get('type') != 'ir.actions.act_window':
            return action
        attachment_ids = self._build_send_email_report_attachments()
        if not attachment_ids:
            return action
        context = dict(action.get('context') or {})
        existing = list(context.get('default_attachment_ids') or [])
        for att_id in attachment_ids:
            if att_id not in existing:
                existing.append(att_id)
        context['default_attachment_ids'] = existing
        context['purchase_auto_attach_report_ids'] = attachment_ids
        action['context'] = context
        return action
    
    def set_since_sent_days(self):
        today = fields.Date.today()
        since_date = False
        purchase_orders = self.sudo().search([
            (
                'po_sent_date','!=',False
            )
        ])
        for po in purchase_orders:
            since_date = today - po.po_sent_date
            po.sudo().write({
                'since_sent_days':since_date.days
            })

