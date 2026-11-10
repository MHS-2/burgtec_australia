import base64
import logging
import uuid as uuid_lib

from odoo import api, models

_logger = logging.getLogger(__name__)


class BurgtecDeliveryLabelZplReport(models.AbstractModel):
    _name = "report.burgtec_delivery_report.burgtec_delivery_label_zpl"
    _description = "Burgtec Delivery Label (ZPL)"

    @api.model
    def _get_report_values(self, docids, data=None):
        pos = self.env["purchase.order"].browse(docids)
        po_ref_clean = pos.burgtec_purchase_reference.split("-", 1)[1]
        po_vendor_short_name = pos[0].partner_id.short_name
        if not po_vendor_short_name:
            po_vendor_short_name = 'EX'

        sale_order_id = (
            self.env.context.get("sale_order_id")
            or (data or {}).get("sale_order_id")
        )
        sale_order = (
            self.env["sale.order"].browse(sale_order_id)
            if sale_order_id
            else self.env["sale.order"]
        )
        location_label = ""
        if sale_order and sale_order.location:
            location_label = dict(
                sale_order.fields_get(["location"])["location"]["selection"]
            ).get(sale_order.location, sale_order.location)

        return {
            "doc_ids": docids,
            "docs": pos,
            "purchase_ref": po_ref_clean,
            "vendor_short_name": po_vendor_short_name,
            "sale_order": sale_order,
            "location_label": location_label,
            "company": self.env.company,
        }

    @api.model
    def print_zpl_via_iot(self, po_id, sale_order_id=None):
        """
        Send ZPL label to the Zebra printer via the Odoo IoT bus channel.

        Direct HTTP from the Odoo server to the IoT box fails when the server
        is cloud/remote: the IoT box sits behind NAT at 192.168.x.x and is
        unreachable inbound.

        The IoT box solves this by keeping a persistent OUTBOUND websocket
        connection to the Odoo server.  Publishing to the iot_channel on the
        bus delivers the message through that existing connection with no
        direct connectivity needed — the same mechanism the action button uses.
        """
        report_action = self.env.ref(
            "burgtec_delivery_report.action_burgtec_delivery_label_zpl",
            raise_if_not_found=False,
        )

        if not report_action:
            return False, "Report action not found"

        if not report_action.device_ids:
            return False, "No IoT printer configured on the ZPL label report"

        # Render ZPL — pass sale_order_id via context so _get_report_values
        # can populate the Project field on the label
        try:
            zpl_bytes, _ = report_action.with_context(
                sale_order_id=sale_order_id,
            )._render(
                report_action.report_name,
                [po_id],
                data={"sale_order_id": sale_order_id},
            )
            zpl_b64 = base64.b64encode(zpl_bytes).decode("utf-8")
        except Exception:
            _logger.exception("Failed to render ZPL for PO %s", po_id)
            return False, "Failed to render label"

        # The IoT box subscribes to this channel on boot via /iot/setup.
        # get_iot_channel() without check=True always returns the name.
        iot_channel = self.env["iot.channel"].sudo().get_iot_channel()
        if not iot_channel:
            return False, "IoT channel unavailable — ensure the IoT box is connected"

        # Build device payload — same format as render_and_send(websocket=True)
        devices = report_action.get_devices_from_ids(report_action.device_ids.ids)
        # iot_identifiers = list({d["iotIdentifier"] for d in devices})
        print_uuid = str(uuid_lib.uuid4())

        # Publish to the bus. IoT box receives this via its outbound WS connection
        # and dispatches the ZPL to socket192168155 (Zebra at 192.168.1.55).
        # self.env["bus.bus"]._sendone(
        #     iot_channel,
        #     "iot_action",
        #     {
        #         "iotDevice": {
        #             "iotIdentifiers": iot_identifiers,
        #             "identifiers": [
        #                 {"identifier": d["identifier"], "id": d["id"]}
        #                 for d in devices
        #             ],
        #         },
        #         "print_id": print_uuid,
        #         "document": zpl_b64,
        #     },
        # )
        for device in devices:
            self.env["bus.bus"]._sendone(
                iot_channel,
                "iot_action",
                {
                    "iot_identifier": device["iotIdentifier"],
                    "device_identifier": device["identifier"],
                    "print_id": print_uuid,
                    "document": zpl_b64,
                },
            )

        _logger.info(
            "ZPL dispatched via IoT bus channel '%s' for PO %s (devices: %s)",
            iot_channel, po_id, [d["identifier"] for d in devices],
        )
        return True, "Label dispatched to printer"