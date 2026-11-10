# -*- coding: utf-8 -*-
{
    'name': "xero_customization",

    'summary': "Xero Customization",

    'description': """
        
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customizations',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sync_xero_connector','bom_based_inventory','sale','purchase','account'],

    # always loaded
    "data": [
        "data/data.xml",
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/product_view_ext.xml",
        "views/purchase_order_views.xml",
        "views/res_config_settings_view.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/xero_account_views.xml",
        "views/xero_webhook_queue_views.xml",
        "wizards/base_partner_merge_automatic_wizard.xml"
    ],
    'license': 'LGPL-3',
}

