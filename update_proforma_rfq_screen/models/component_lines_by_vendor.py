# -*- coding: utf-8 -*-
import logging
import base64
import io

import xlsxwriter

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ComponentLinesByVendor(models.Model):
    _name = 'component.lines.by.vendor'
    _description = 'Component Lines By Vendor'

    name = fields.Char('')
    component_id = fields.Many2one('sale.order.bom.component', string='BOM Component', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product',
        string='Component',
        domain="[('product_tmpl_id.product_bom_type', '=', 'components')]",
    )
    order_line_id = fields.Many2one('sale.order.line', ondelete='cascade')
    order_id = fields.Many2one('sale.order')
    product_qty = fields.Float(string='Quantity', digits='Product Quantity', default=1)
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    note = fields.Text('Note')
    display_type = fields.Selection([
        ('line_section', "Section"),
    ], string="Display Type")
    sequence = fields.Integer("Sequence")
    is_other_than_bom = fields.Boolean(default=False)
    parent_product_code = fields.Char('Product Code', related='order_line_id.line_section_name')
    is_parent = fields.Boolean(string="Is Parent")
    unit_sale_price = fields.Float(string='Unit Sale Price', readonly=True)
    is_auto_generated = fields.Boolean(
        string="Auto-Generated",
        default=False,
        help="Technical field to identify lines created automatically"
    )
    total_live_unit_cost = fields.Float(string='Total Live Cost')
    manual_live_unit_cost = fields.Float(string='Live Unit Cost')
    partner_shipping_id = fields.Many2one(comodel_name='res.partner')
    currency_id = fields.Many2one(comodel_name='res.currency')
    parent_product_group = fields.Char(related='order_line_id.line_group_name')
    parent_product_code = fields.Char(related='order_line_id.line_section_name')


    def show_report(self):
        return self.env.ref('update_proforma_rfq_screen.action_rfq_vendor_report').report_action(self)
    
    def show_information(self):
        bom_component = self.component_id
        parent_component_line = bom_component.component_line_ids.filtered(lambda l:l.is_parent and l.order_line_id.id == self.order_line_id.id)
        view_id = self.env.ref('update_proforma_rfq_screen.vendor_wise_report_information_bom_component_lines_list_view').id
        if not parent_component_line:
            raise ValidationError(_("No Parent Product Found For The Selected Component %s",self.product_id.display_name))
        if parent_component_line:    
            return {
            'target': 'new',
            'type': 'ir.actions.act_window',
            'name': _('Parent Component Lines'),
            'res_model': 'sale.order.bom.component.line',
            'view_mode': 'list',
            'views': [(view_id, 'list')],
            'domain': [('id','=',parent_component_line.id)],
            'context': "{'create': False,'delete': False,}",
        }


    def export_vendor_components_csv(self):
        for line in self:
            vendor_component_lines = line.component_id.vendor_component_line_ids.filtered(lambda l:l.supplier_id.id == line.supplier_id.id and not l.display_type)
            no_ref = vendor_component_lines.product_id.filtered(lambda p:not p.default_code)
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
            sheet.write(1, 0, "", text_fmt)

            sheet.write(1, 1, "", datetime_fmt)
            sheet.write(1, 2, self.currency_id.name or "", text_fmt)
            # Row 2+: lines
            for row, line in enumerate(vendor_component_lines, start=1):
                sheet.write_number(row, 3, line.sequence, text_fmt)
                sheet.write(row, 4, line.product_id.default_code, text_fmt)
                sheet.write(row, 5, line.product_id.name or "", text_fmt)
                sheet.write(row, 6, line.product_qty, float_fmt)
                sheet.write(row, 7, "", text_fmt)
                sheet.write(row, 8, line.manual_live_unit_cost, float_fmt)
                sheet.write(row, 9, "", text_fmt)
                sheet.write(row, 10, "", float_fmt)
                sheet.write(row, 11, line.note or "", text_fmt)
                sheet.write(row, 12, line.parent_product_group or "", text_fmt)
                sheet.write(row, 13, line.parent_product_code or "", text_fmt)

            workbook.close()

            attachment = self.env["ir.attachment"].create({
                "name": "%s.xlsx" % (self.name).replace("/", "_"),
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
