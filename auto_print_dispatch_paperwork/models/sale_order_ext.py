import base64
import json
import logging
import requests
from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TOSHIBA_PRINTER_IDENTIFIER = (
    "socket19216813"
)


class SaleOrderExt(models.Model):
    _inherit = "sale.order"

    parent_purchase_order_state = fields.Selection(
        related="purchase_order_id.state",
        string='Parent Purchase Order State',
        store=True,
        readonly=True
    )

    def auto_print_to_iot(self):
        self.ensure_one()
        return self.env.ref(
            'burgtec_delivery_report.action_burgtec_delivery_report'
        ).report_action(self)
