from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    number_of_areas = fields.Integer(
        string='Number of Areas',
        default=0,
        copy=False
    )
    area_ids = fields.One2many(
        'sale.order.area',
        'order_id',
        string='Areas'
    )
    area_allocation_ids = fields.One2many(
        'sale.order.area.allocation',
        'order_id',
        string='Area Allocations'
    )

    def write(self, vals):
        res = super().write(vals)
        if 'number_of_areas' in vals:
            self._sync_areas()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.number_of_areas > 0:
                order._sync_areas()
        return orders

    def _sync_areas(self):
        """Synchronize area records based on number_of_areas."""
        for order in self:
            current_areas = order.area_ids.sorted('sequence')
            current_count = len(current_areas)
            target_count = max(order.number_of_areas, 0)

            if current_count < target_count:
                # Add missing areas
                for i in range(current_count, target_count):
                    self.env['sale.order.area'].create({
                        'order_id': order.id,
                        'name': 'Level %02d' % (i + 1),
                        'sequence': (i + 1) * 10,
                    })
            elif current_count > target_count:
                # Remove excess areas (from the end)
                areas_to_remove = current_areas[target_count:]
                areas_to_remove.unlink()
            
            elif current_count == target_count:
                continue

    def get_area_matrix_data(self):
        """Return matrix data for the area allocation widget."""
        self.ensure_one()
        # Aggregate order line quantities by product template
        products = {}
        order_line = self.order_line 
        for line in order_line:
            product = line.product_id
            if not product:
                continue
            if product.type in ('combo','service'):
                continue
            if product.is_delivery_and_installation:
                continue
            # if product.id not in products:
            if line.id not in products: # Each Sale Order Line with product is treated seperately whether the product was same or not.
                products[line.id] = {
                    'order_line_id':line.id,
                    'product_identifier':line.product_identifier,
                    'code': line.line_section_name,
                    'product_id': product.id,
                    'display_name': product.display_name,
                    'product_custom_name': line.custom_product_name,
                    'total_qty': 0.0,
                }
            products[line.id]['total_qty'] += line.product_uom_qty

        # Get areas sorted by sequence
        areas = [{
            'id': area.id,
            'name': area.name,
            'sequence': area.sequence,
        } for area in self.area_ids.sorted('sequence')]

        # Get allocations as {template_id}_{area_id} -> qty
        allocations = {}
        for alloc in self.area_allocation_ids:
            # key = '%s_%s' % (alloc.product_id.id, alloc.area_id.id)
            # Each Sale Order Line with product is treated seperately whether the product was same or not.
            key = '%s_%s' % (alloc.order_line_id.id, alloc.area_id.id)
            allocations[key] = alloc.allocated_qty

        # Compute available qty per product template
        product_list = []
        for pid, pdata in products.items():
            allocated_total = sum(
                allocations.get('%s_%s' % (pid, a['id']), 0.0)
                for a in areas
            )
            pdata['available_qty'] = pdata['total_qty'] - allocated_total
            product_list.append(pdata)

        return {
            'areas': areas,
            'products': product_list,
            'allocations': allocations,
        }

    def save_area_allocation(self, productorderline_id, product_id, area_id, qty):
        """Save or update an area allocation for a product template."""
        self.ensure_one()
        qty = max(float(qty), 0.0)

        alloc = self.area_allocation_ids.filtered(
            lambda a: a.product_id.id == product_id
            and a.area_id.id == area_id and a.order_line_id.id == productorderline_id
        )
        if alloc:
            if qty == 0:
                alloc.unlink()
            else:
                alloc.allocated_qty = qty
        elif qty > 0:
            self.env['sale.order.area.allocation'].create({
                'order_line_id': productorderline_id,
                'order_id': self.id,
                'product_id': product_id,
                'area_id': area_id,
                'allocated_qty': qty,
            })

        # Validate total allocation does not exceed order line qty
        self._validate_area_allocations()
        return self.get_area_matrix_data()

    def save_area_name(self, area_id, name):
        """Update an area's name."""
        self.ensure_one()
        area = self.area_ids.filtered(lambda a: a.id == area_id)
        if area:
            area.name = name
        return True

    def _validate_area_allocations(self):
        """Validate that allocations don't exceed total quantities."""
        for order in self:
            products = {}
            order_line = order.order_line 
            for line in order_line:
                # prod_id = line.product_id.id
                # Each Sale Order Line with product is treated seperately whether the product was same or not.
                order_line_id = line.id
                if order_line_id not in products:
                    products[order_line_id] = {
                        'name': line.product_id.display_name,
                        'total_qty': 0.0,
                    }
                products[order_line_id]['total_qty'] += line.product_uom_qty

            for alloc in order.area_allocation_ids:
                # prod_id = alloc.product_id.id
                # Each Sale Order Line with product is treated seperately whether the product was same or not.
                order_line_id = alloc.order_line_id.id
                if order_line_id in products:
                    products[order_line_id].setdefault('allocated', 0.0)
                    products[order_line_id]['allocated'] += alloc.allocated_qty

            for order_line_id, data in products.items():
                allocated = data.get('allocated', 0.0)
                if allocated > data['total_qty']:
                    raise ValidationError(
                        _('Total allocated quantity (%(allocated)s) for "%(product)s" '
                          'exceeds the order quantity (%(total)s).',
                          allocated=allocated,
                          product=data['name'],
                          total=data['total_qty'],
                        )
                    )
    
    def copy(self, default=None):
        sale_order_area_object =  self.env['sale.order.area']
        sale_area_allocation_object = self.env['sale.order.area.allocation']
        source_areas = self.area_ids
        source_allocations = self.area_allocation_ids
        area_vals = []
        allocation_vals = source_allocations.copy_data()
        copied_sale_order = super().copy(default)
        original_order_lines = self.order_line.filtered(lambda o:o.product_id and not o.product_id.is_delivery_and_installation).mapped('id')
        copied_order_lines = copied_sale_order.order_line.filtered(lambda o:o.product_id and not o.product_id.is_delivery_and_installation).mapped('id')
        map_order_lines = {}
        for i in range(len(copied_order_lines)):
            map_order_lines[original_order_lines[i]] = copied_order_lines[i]
        for area in source_areas:
            area_vals.append({'order_id': copied_sale_order.id, 'name': area.name, 'sequence': area.sequence, 'parent_area': area.id})
        area_res = sale_order_area_object.sudo().create(area_vals)
        for alloc in allocation_vals:
            alloc['order_line_id'] = map_order_lines[alloc['order_line_id']]
            alloc['order_id'] = copied_sale_order.id
            alloc['area_id'] = area_res.filtered(lambda a:int(a.parent_area) == alloc['area_id']).id
        allocation_res = sale_area_allocation_object.sudo().create(allocation_vals)
        for new_alloc in allocation_res:
            sale_order_area_object.sudo().search([('id','=',new_alloc.area_id.id)])
            sale_order_area_object.allocation_ids = [(4,new_alloc.id,0)]
        copied_sale_order.number_of_areas = self.number_of_areas
        return copied_sale_order

