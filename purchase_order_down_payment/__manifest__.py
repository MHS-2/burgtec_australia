# -*- coding: utf-8 -*-
{
    'name': "purchase_order_down_payment",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['purchase','bom_based_inventory'],

    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "wizards/account_move_reversal_view.xml",
        "wizards/purchase_order_advance_payment.xml",
        "views/purchase_order_views.xml",
        "views/res_config_settings_views.xml",
    ],
    'license': 'LGPL-3',
}

