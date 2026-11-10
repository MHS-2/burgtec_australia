{
    'name': 'Sale Area Allocation',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Allocate product quantities across areas on sales quotations',
    'description': """
        Adds a "Products Area Wise" tab on Sales Quotations/Orders allowing
        users to allocate product quantities across configurable areas.
        Features:
        - Dynamic area columns based on Number of Areas field
        - Editable area names (e.g., Level 01, Level 02)
        - Real-time available quantity tracking
        - Validation to prevent over-allocation
    """,
    'author': 'DearERP',
    'website': 'https://www.dearerp.com',
    'depends': ['sale_management','bom_based_inventory','sale_order_customisation','sale_custom_report'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_area_allocation/static/src/components/area_allocation_matrix.js',
            'sale_area_allocation/static/src/components/area_allocation_matrix.xml',
            'sale_area_allocation/static/src/components/area_allocation_matrix.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
