from odoo import models, fields, api
import qrcode
from io import BytesIO
import base64
from odoo.exceptions import UserError


class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    qr_url = fields.Char(related='hubspot_ticket_id.hubspot_ticket_url', store=True,
                         string='HubSpot Del. Stage ticket URL')
    qr_code = fields.Binary(
        string="QR Code",
        attachment=False,
        store=True,
        readonly=True,
        compute='_compute_qr_code',
    )

    @api.depends('qr_url')
    def _compute_qr_code(self):
        for rec in self:
            if rec.qr_url:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=3,
                    border=4,
                )
                qr.add_data(f"{rec.qr_url}")
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                temp = BytesIO()
                img.save(temp, format="PNG")
                qr_image = base64.b64encode(temp.getvalue())
                rec.qr_code = qr_image
            else:
                rec.qr_code = False

    def action_preview_burgtec_delivery_pdf_report(self):
        if self.quote_type != 'delivery_stage':
            raise UserError('This Action is Only Applicable on Delivery Stage')
        if self.state != 'sale':
            raise UserError('First Confirm This Delivery Stage')
        if not self.location:
            raise UserError('Please Set the Location First!')
        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/pdf/burgtec_delivery_report.action_burgtec_delivery_report/{self.id}',
            'target': 'new',
        }

    def pass_project_name_to_delivery_stage(self):
        for rec in self:
            data = {}
            project_name=False
            source_id = int(rec.source_sale_order_id)
            if source_id:
                data = rec.env['sale.order'].search_read(domain=[('id','=',source_id)], fields=['project_name'])
                if data and len(data) == 1:
                    for p_name in data:
                        # Safely access the value using the key
                        project_name = p_name['project_name']
                        if project_name:
                            rec.project_name = project_name


    def action_confirm(self):
        for order in self:
            if order.quote_type == 'delivery_stage' and not order.location:
                raise UserError('Please Set the Location First!')

        return super(SaleOrderExt, self).action_confirm()
