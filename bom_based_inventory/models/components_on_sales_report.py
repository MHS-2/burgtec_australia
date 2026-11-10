from odoo import fields, models, api
from odoo.exceptions import UserError, AccessError, ValidationError


class ComponentsOnReport(models.Model):
    _name = 'components.on.report'
    _description = 'Components On Report'

    component_line_ids = fields.One2many('components.on.report.line', 'report_id', string="Component Lines")

    @api.model
    def default_get(self, fields):
        res = super(ComponentsOnReport, self).default_get(fields)
        context = self.env.context
        order_id = context.get('sale_order')
        if not order_id:
            return res
        sale_order = self.env['sale.order'].browse(order_id)
        parent_po = sale_order.purchase_order_id
        child_purchase_order = self.env['purchase.order']
        if parent_po.picking_ids:
            picking_name = parent_po.picking_ids[0].display_name
            child_purchase_order = self.env['purchase.order'].search([('origin', '=', picking_name)])
        if sale_order.bom_component_id:
            component_lines = []
            for line in sale_order.bom_component_id.component_line_ids:
                if not line.is_parent:
                    matching_po = child_purchase_order.filtered(lambda po: any(
                        ol.product_id.id == line.product_id.id for ol in po.order_line
                    ) and po.partner_id.id == line.supplier_id.id)
                    matching_po = matching_po[0] if matching_po else False
                    delivery_date = matching_po.date_planned if matching_po else False
                    component_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_reference': line.product_reference,
                        'product_qty': line.product_qty,
                        'live_unit_cost': line.live_unit_cost,
                        'system_cost_per_unit': line.system_cost_per_unit,
                        'quoted_cost_per_unit': line.quoted_cost_per_unit,
                        'pre_project_cost_per_unit': line.pre_project_cost_per_unit,
                        'supplier_id': line.supplier_id.id,
                        'delivery_date': delivery_date,
                        'purchase_order_id': matching_po.id if matching_po else False,
                    }))
            res.update({
                'component_line_ids': component_lines,
            })
        return res


class ComponentsOnReportLine(models.Model):
    _name = 'components.on.report.line'
    _description = 'Components On Report Line'

    report_id = fields.Many2one('components.on.report')
    product_id = fields.Many2one('product.product')
    parent_product_id = fields.Many2one('product.template')
    product_qty = fields.Float(string='Quantity', digits='Product Quantity')
    update_qty = fields.Float(string='Update Quantity')
    product_reference = fields.Char(string='Product Reference')
    parent_product_reference = fields.Char('Parent Product Reference')
    live_unit_cost = fields.Float(string='Live Unit Cost')
    system_cost_per_unit = fields.Float(string='System Cost per Unit')
    quoted_cost_per_unit = fields.Float(string='Quoted Cost per Unit')
    pre_project_cost_per_unit = fields.Float(string='Pre-Project Cost per Unit')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    delivery_date = fields.Datetime(string='Delivery Date')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
