import base64
import io

import xlsxwriter

from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_export_xlsx(self):
        self.ensure_one()
        lines = self.order_line.filtered(lambda l: not l.display_type and l.product_id)
        if not lines:
            raise UserError(_("No product lines to export."))
        no_ref = lines.product_id.filtered(lambda p: not p.default_code)
        if no_ref:
            raise UserError(_(
                "Internal Reference is required (used as the matching key).\nMissing on:\n%s",
                "\n".join(no_ref.mapped("display_name")),
            ))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Sheet1")

        base = {"text_wrap": True}
        header_fmt = workbook.add_format({"bold": True})
        text_fmt = workbook.add_format(base)
        datetime_fmt = workbook.add_format({**base, "num_format": "yyyy-mm-dd hh:mm:ss"})
        float_fmt = workbook.add_format({**base, "num_format": "#,##0.00"})

        headers = [
            "Order Reference",                          # 0
            "Order Deadline",                           # 1
            "Currency",                                 # 2
            "Order Lines/Sequence",                     # 3
            "Order Lines/Product/Internal Reference",   # 4
            "Order Lines/Product/Name",                 # 5
            "Order Lines/Quantity",                     # 6
            "Order Lines/Unit of Measure",              # 7
            "Order Lines/Unit Price",                   # 8
            "Order Lines/Taxes",                        # 9
            "Order Lines/Subtotal",                     # 10
            "Order Lines/Notes",                        # 11
            "Order Lines/Line Group Name",              # 12
            "Order Lines/Line Section Name",            # 13
        ]
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_fmt)
        sheet.set_column(0, len(headers) - 1, 30)

        # Row 2: order header data (native one2many export style)
        sheet.write(1, 0, self.burgtec_purchase_reference or "", text_fmt)
        if self.date_order:
            order_date = fields.Datetime.context_timestamp(self, self.date_order).replace(tzinfo=None)
            sheet.write_datetime(1, 1, order_date, datetime_fmt)
        sheet.write(1, 2, self.currency_id.name or "", text_fmt)

        # Row 2+: lines
        for row, line in enumerate(lines, start=1):
            sheet.write_number(row, 3, line.sequence, text_fmt)
            sheet.write(row, 4, line.product_id.default_code, text_fmt)
            sheet.write(row, 5, line.product_id.name or "", text_fmt)
            sheet.write_number(row, 6, line.product_qty, float_fmt)
            sheet.write(row, 7, line.product_uom.name or "", text_fmt)
            sheet.write_number(row, 8, line.price_unit, float_fmt)
            sheet.write(row, 9, ", ".join(line.taxes_id.mapped("name")), text_fmt)
            sheet.write_number(row, 10, line.price_subtotal, float_fmt)
            sheet.write(row, 11, line.note or "", text_fmt)
            sheet.write(row, 12, line.line_group_name_child or "", text_fmt)
            sheet.write(row, 13, line.line_section_name_child or "", text_fmt)

        workbook.close()

        attachment = self.env["ir.attachment"].create({
            "name": "%s.xlsx" % (self.burgtec_purchase_reference or self.name).replace("/", "_"),
            "type": "binary",
            "datas": base64.b64encode(output.getvalue()),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }