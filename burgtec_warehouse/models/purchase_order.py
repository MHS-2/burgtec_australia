# -*- coding: utf-8 -*-
import logging
from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_purchase_lines_fetched_for_bo = fields.Boolean()


    @api.depends_context('burgtec_po_reference')
    def _compute_display_name(self):
        for record in self:
            if record.env.context.get('burgtec_po_reference'):
                if record.burgtec_purchase_reference:
                    record.display_name = record.burgtec_purchase_reference
                else:
                    return super()._compute_display_name()

            else:
                return super()._compute_display_name()

    def get_po_reference(self):
        for record in self:
            return f"{self.burgtec_purchase_reference}"

    def create_and_set_attachments(self,warehouse_id,base64_image):
        warehouseobj = self.env['warehouse.receiving'].sudo().browse(warehouse_id)
        attachment_name = f"{warehouseobj.name} - {self.burgtec_purchase_reference} - Attachment"
        vals = {
            'name': attachment_name,
            'type': 'binary',
            'datas': base64_image,
        }
        res = self.env['ir.attachment'].sudo().create(vals)
        message_body = Markup(f"""
                <div style="background-color: #f8f8ff; border: 2px solid #dcdcdc; border-radius: 5px; padding: 15px; margin: 10px 0;">
                    <h4 style="color: #2d003b; margin: 0 0 10px 0;">
                        <span style="font-size: 18px;"> <i class="fa fa-plus" aria-hidden="true"></i> </span> File Attached.
                    </h4>
                    <p style="margin: 5px 0; color: #000000; font-weight: bold;">
                        {attachment_name}
                    </p>
                    <p style="margin: 10px 0 0 0; font-size: 12px; color: #000000;">
                        Attached by: {self.env.user.name} on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>
            """)
        # if not res:
        #     return f"Failed to attach Image to the following Purhcase Order {self.burgtec_purchase_reference}"
        if res:        
            self.message_post(
                body=message_body,
                attachment_ids=[res.id]
            )
            # return f"Image attached successfully to the following Purchase Order {self.burgtec_purchase_reference}"
        
