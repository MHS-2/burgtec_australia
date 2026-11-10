import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class LabelPrintController(http.Controller):

    @http.route(
        "/label/print/<int:sale_id>/<int:po_id>",
        type="http",
        auth="user",
        website=False,
    )
    def print_label(self, sale_id, po_id, **kwargs):

        sale_order = request.env["sale.order"].sudo().browse(sale_id)
        po = request.env["purchase.order"].sudo().browse(po_id)

        if not sale_order.exists() or not po.exists():
            return request.not_found()

        try:
            report = request.env[
                "report.burgtec_delivery_report.burgtec_delivery_label_zpl"
            ].sudo()

            success, msg = report.print_zpl_via_iot(
                po_id=po.id,
                sale_order_id=sale_order.id,
            )

            if not success:
                _logger.error("QR PRINT FAILED: %s", msg)
                return request.make_response(
                    f"<h2>Print Failed</h2><p>{msg}</p>",
                    status=500,
                    headers=[("Content-Type", "text/html")],
                )

            # Required: commit before returning success response
            request.env.cr.commit()

            _logger.info(
                "QR PRINT COMMITTED: sale_order=%s po_order=%s",
                sale_order.burgtec_quote_reference,
                po.burgtec_purchase_reference,
            )

            return request.make_response(
                f"""
                <html>
                    <body style="font-family:sans-serif;text-align:center;padding:40px;">
                        <h2 style="color:green;">Label Sent to Printer Successfully</h2>
                        <p>Purchase Order: {po.burgtec_purchase_reference}</p>
                        <p>Sales Order: {sale_order.burgtec_quote_reference}</p>
                    </body>
                </html>
                """,
                headers=[("Content-Type", "text/html")],
            )

        except Exception:
            _logger.exception("QR printing crashed")
            return request.make_response(
                "Internal Server Error",
                status=500,
            )