# -*- coding: utf-8 -*-
{
    'name': "sale_order_customisation",

    'summary': "Functionality To Add Product, Add Code Directly On Sale Order Line (Groups and Codes) and Duplicate feature on SOL",

    'description': """
Functionality To Add Product, Add Code Directly On Sale Order Line (Groups and Codes) and Duplicate feature for product line on Same Sale Order or Different
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'customizations',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['sale_custom_report','bom_based_inventory'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_line_extend_view.xml',
        'wizard/sale_order_line_wizard_views.xml',
        'wizard/duplicate_sale_order_line_wizard_view.xml',
        
    ],
    "assets": {
        "web.assets_backend": [
            "sale_order_customisation/static/src/js/sale_order_line_field/*",
            "sale_order_customisation/static/src/js/*",
            "sale_order_customisation/static/src/css/style.css"
        ],
    },
    'license': 'LGPL-3',
}

