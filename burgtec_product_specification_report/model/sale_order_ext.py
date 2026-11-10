import base64
from odoo import fields, models, api, _, Command
from odoo.modules.module import get_module_resource

class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    product_specification_report_line_ids = fields.One2many(
        'product.specification.report.line',
        'order_id',
        compute='_compute_product_specification_report_line_ids',
        store=True
    )



    @api.depends('order_line', 'order_line.product_template_id')
    def _compute_product_specification_report_line_ids(self):
        for order in self:
            existing_product_ids = set(order.product_specification_report_line_ids.mapped('product_template_id.id'))
            # order.product_specification_report_line_ids = [Command.clear()]

            unique_products = {}
            for line in order.order_line:
                if line.product_template_id and not line.display_type:
                    product_id = line.product_template_id.id
                    if product_id not in unique_products:
                        unique_products[product_id] = line

            new_product_ids = set(unique_products.keys()) - existing_product_ids


            spec_lines = []
            for product_id in new_product_ids:
                original_line = unique_products[product_id]
                spec_lines.append(Command.create({
                    'original_line_id': original_line.id,
                    'product_template_id': original_line.product_template_id.id,
                    'custom_product_name': original_line.custom_product_name,
                    'name': original_line.name,
                    'is_show': True,
                }))

            if spec_lines:
                order.product_specification_report_line_ids = [(0, 0, line[2]) for line in spec_lines]


    def get_office_interior_image(self):
        image_path = get_module_resource(
            'burgtec_product_specification_report',
            'static/img',
            'office_interior.png'
        )
        if image_path:
            try:
                with open(image_path, 'rb') as image_file:
                    return base64.b64encode(image_file.read()).decode('utf-8')
            except:
                return False
        return False

    def get_footer_logo_image(self):
        image_path = get_module_resource(
            'burgtec_product_specification_report',
            'static/img',
            'afrdi-logo-black.png'
        )
        if image_path:
            try:
                with open(image_path, 'rb') as image_file:
                    return base64.b64encode(image_file.read()).decode('utf-8')
            except:
                return False
        return False
    
    def _force_create_product_specification_report_line_ids(self):
        for order in self:
            # existing_product_ids = set(order.product_specification_report_line_ids.mapped('product_template_id.id'))
            order.product_specification_report_line_ids = [Command.clear()]

            unique_products = {}
            for line in order.order_line:
                if line.product_template_id and not line.display_type:
                    product_id = line.product_template_id.id
                    if product_id not in unique_products:
                        unique_products[product_id] = line

            new_product_ids = set(unique_products.keys())

            spec_lines = []
            for product_id in new_product_ids:
                original_line = unique_products[product_id]
                spec_lines.append(Command.create({
                    'original_line_id': original_line.id,
                    'product_template_id': original_line.product_template_id.id,
                    'custom_product_name': original_line.custom_product_name,
                    'name': original_line.name,
                    'is_show': True,
                }))

            if spec_lines:
                order.product_specification_report_line_ids = [(0, 0, line[2]) for line in spec_lines]
