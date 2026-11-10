{
    'name': 'BOM Based Inventory',
    'version': '18.1',
    'summary': 'BOM based price',
    'sequence': -1,
    'description': """
    
            """,
    'category': 'Customizations',
    'website': '',
    'depends': ['web', 'base', 'project', 'product', 'sale_project', 'sale_management', 'mrp', 'sale', 'purchase','stock','account','mail'],
    "data": [
        "data/ir_action_data.xml",
        "security/ir.model.access.csv",
        "security/products_security.xml",
        "views/account_move_ext.xml",
        "views/account_payment_term_views.xml",
        "views/components_on_sale_report.xml",
        "views/mail_compose_ext.xml",
        "views/mrp_bom_form_view_ext.xml",
        "views/product_price_list_view_ext.xml",
        "views/productc_template_ext.xml",
        "views/project_project_ext.xml",
        "views/purchase_order_line_.xml",
        "views/sale_order_bom_componenet.xml",
        "views/sale_order_bom_component_line_view.xml",
        "views/sale_order_ext.xml",
        "views/split_delivery_order.xml",
        "views/product_certification_view.xml",
        "report/sale_report_views.xml",
        "wizard/bom_component_wizard.xml"
    ],
    'assets': {
        'web.assets_backend': [
            'bom_based_inventory/static/src/css/style.css',
            'bom_based_inventory/static/src/js/disable_list_view_sort.js',
            'bom_based_inventory/static/src/xml/sale_product_field_override.xml',
            'bom_based_inventory/static/src/js/sale_product_field_override.js',
        ]
    },
    'license': 'LGPL-3',
}
