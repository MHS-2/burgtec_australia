from odoo import models, fields, api,_
from odoo.fields import Command


class SaleAdvancePaymentExt(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.depends('sale_order_ids')
    def _compute_has_down_payments(self):
        for wizard in self:
            wizard.has_down_payments = bool(
                wizard.sale_order_ids.down_payment_order_line_ids.filtered('is_downpayment')
            )
    
