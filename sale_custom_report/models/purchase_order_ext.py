from odoo import models, fields


class PurchaseOrderLineExt(models.Model):
    _inherit = 'purchase.order.line'

    line_group_name = fields.Char(related='sale_line_id.line_group_name')
    line_section_name = fields.Char(related='sale_line_id.line_section_name')
    line_group_name_child = fields.Char()
    line_section_name_child = fields.Char()
