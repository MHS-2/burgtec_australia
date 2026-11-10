from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestAreaAllocation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer',
        })
        cls.product_template = cls.env['product.template'].create({
            'name': 'Test Product',
            'list_price': 100.0,
            'type': 'consu',
        })
        cls.product = cls.product_template.product_variant_ids[0]
        cls.product_template_2 = cls.env['product.template'].create({
            'name': 'Test Product 2',
            'list_price': 200.0,
            'type': 'consu',
        })
        cls.product_2 = cls.product_template_2.product_variant_ids[0]

    def _create_sale_order(self, lines=None):
        """Helper to create a sale order with order lines."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        if lines is None:
            lines = [(self.product, 10.0)]
        for product, qty in lines:
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': product.id,
                'product_uom_qty': qty,
            })
        return order

    def test_sync_areas_on_write(self):
        """Test that areas are created when number_of_areas is set."""
        order = self._create_sale_order()
        order.number_of_areas = 3
        self.assertEqual(len(order.area_ids), 3)
        self.assertEqual(order.area_ids[0].name, 'Level 01')
        self.assertEqual(order.area_ids[1].name, 'Level 02')
        self.assertEqual(order.area_ids[2].name, 'Level 03')

    def test_sync_areas_increase(self):
        """Test adding more areas preserves existing ones."""
        order = self._create_sale_order()
        order.number_of_areas = 2
        self.assertEqual(len(order.area_ids), 2)

        # Rename first area
        order.area_ids[0].name = 'Ground Floor'
        order.number_of_areas = 3
        self.assertEqual(len(order.area_ids), 3)
        # Existing areas should be preserved
        self.assertEqual(order.area_ids.sorted('sequence')[0].name, 'Ground Floor')

    def test_sync_areas_decrease(self):
        """Test removing areas deletes excess ones."""
        order = self._create_sale_order()
        order.number_of_areas = 3
        self.assertEqual(len(order.area_ids), 3)

        order.number_of_areas = 1
        self.assertEqual(len(order.area_ids), 1)

    def test_sync_areas_to_zero(self):
        """Test setting areas to zero removes all."""
        order = self._create_sale_order()
        order.number_of_areas = 2
        order.number_of_areas = 0
        self.assertEqual(len(order.area_ids), 0)

    def test_get_area_matrix_data(self):
        """Test the matrix data method returns correct structure."""
        order = self._create_sale_order([
            (self.product, 10.0),
            (self.product_2, 5.0),
        ])
        order.number_of_areas = 2

        data = order.get_area_matrix_data()
        self.assertEqual(len(data['areas']), 2)
        self.assertEqual(len(data['products']), 2)
        self.assertIsInstance(data['allocations'], dict)

        # Check product totals
        prod1 = next(
            p for p in data['products']
            if p['template_id'] == self.product_template.id
        )
        self.assertEqual(prod1['total_qty'], 10.0)
        self.assertEqual(prod1['available_qty'], 10.0)

    def test_get_area_matrix_data_groups_same_template(self):
        """Test that order lines with same product template are grouped."""
        order = self._create_sale_order([
            (self.product, 5.0),
            (self.product, 3.0),
        ])
        order.number_of_areas = 1

        data = order.get_area_matrix_data()
        self.assertEqual(len(data['products']), 1)
        self.assertEqual(data['products'][0]['total_qty'], 8.0)

    def test_save_area_allocation(self):
        """Test saving an allocation."""
        order = self._create_sale_order()
        order.number_of_areas = 2
        area = order.area_ids.sorted('sequence')[0]

        data = order.save_area_allocation(
            self.product_template.id, area.id, 5.0
        )
        self.assertEqual(len(order.area_allocation_ids), 1)
        self.assertEqual(order.area_allocation_ids.allocated_qty, 5.0)

        # Check available qty
        prod = next(
            p for p in data['products']
            if p['template_id'] == self.product_template.id
        )
        self.assertEqual(prod['available_qty'], 5.0)

    def test_save_area_allocation_update(self):
        """Test updating an existing allocation."""
        order = self._create_sale_order()
        order.number_of_areas = 1
        area = order.area_ids[0]

        order.save_area_allocation(self.product_template.id, area.id, 5.0)
        order.save_area_allocation(self.product_template.id, area.id, 7.0)

        self.assertEqual(len(order.area_allocation_ids), 1)
        self.assertEqual(order.area_allocation_ids.allocated_qty, 7.0)

    def test_save_area_allocation_remove_on_zero(self):
        """Test that setting qty to 0 removes the allocation record."""
        order = self._create_sale_order()
        order.number_of_areas = 1
        area = order.area_ids[0]

        order.save_area_allocation(self.product_template.id, area.id, 5.0)
        self.assertEqual(len(order.area_allocation_ids), 1)

        order.save_area_allocation(self.product_template.id, area.id, 0)
        self.assertEqual(len(order.area_allocation_ids), 0)

    def test_allocation_exceeds_total_raises_error(self):
        """Test that over-allocation raises ValidationError."""
        order = self._create_sale_order([(self.product, 10.0)])
        order.number_of_areas = 2
        areas = order.area_ids.sorted('sequence')

        order.save_area_allocation(self.product_template.id, areas[0].id, 6.0)
        with self.assertRaises(ValidationError):
            order.save_area_allocation(
                self.product_template.id, areas[1].id, 5.0
            )

    def test_partial_allocation_allowed(self):
        """Test that partial allocation (available qty > 0) is allowed."""
        order = self._create_sale_order([(self.product, 10.0)])
        order.number_of_areas = 2
        area = order.area_ids.sorted('sequence')[0]

        data = order.save_area_allocation(
            self.product_template.id, area.id, 3.0
        )
        prod = next(
            p for p in data['products']
            if p['template_id'] == self.product_template.id
        )
        self.assertEqual(prod['available_qty'], 7.0)

    def test_save_area_name(self):
        """Test updating area name."""
        order = self._create_sale_order()
        order.number_of_areas = 1
        area = order.area_ids[0]

        order.save_area_name(area.id, 'Ground Floor')
        self.assertEqual(area.name, 'Ground Floor')

    def test_negative_allocation_prevented(self):
        """Test that negative allocation qty is prevented."""
        order = self._create_sale_order()
        order.number_of_areas = 1
        area = order.area_ids[0]

        # save_area_allocation converts negative to 0
        order.save_area_allocation(self.product_template.id, area.id, -5.0)
        self.assertEqual(len(order.area_allocation_ids), 0)

    def test_cascade_delete_on_area_removal(self):
        """Test that allocations are deleted when area is removed."""
        order = self._create_sale_order()
        order.number_of_areas = 2
        areas = order.area_ids.sorted('sequence')

        order.save_area_allocation(self.product_template.id, areas[0].id, 3.0)
        order.save_area_allocation(self.product_template.id, areas[1].id, 2.0)
        self.assertEqual(len(order.area_allocation_ids), 2)

        # Reduce to 1 area - should cascade delete allocations for area 2
        order.number_of_areas = 1
        self.assertEqual(len(order.area_ids), 1)
        self.assertEqual(len(order.area_allocation_ids), 1)

    def test_create_order_with_areas(self):
        """Test creating an order directly with number_of_areas."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'number_of_areas': 2,
        })
        self.assertEqual(len(order.area_ids), 2)
