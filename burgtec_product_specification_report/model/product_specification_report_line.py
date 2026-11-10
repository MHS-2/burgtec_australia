from odoo import fields,models


class ProductSpecificationReportLine(models.Model):
    _name = 'product.specification.report.line'
    _description = 'Product Specification Report Line'
    _rec_name = 'product_template_id'

    original_line_id = fields.Many2one('sale.order.line', string='Original Line')
    order_id = fields.Many2one('sale.order', string='Sale Order')
    product_template_id = fields.Many2one('product.template', string='Product')
    is_show = fields.Boolean("Show Report", default=True)
    custom_product_name = fields.Char(string="Product Name")
    name = fields.Text(string="Decription")





