# -*- coding: utf-8 -*-
{
    'name': "purchase_list_report",

    'summary': "Reporting module to give list reports for Sale, Purchase and Accounting.",

    'description': """
        List Report for Sales, Purchase and Accounts.
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customizations',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','bom_based_inventory','sale_custom_report','burgtec_hubspot_customization','quotation_type_customization','account', 'purchase_order_custom_report','purchase_order_down_payment'],

    # always loaded
    'data': [
        "views/purchase_list_report_view.xml"
    ],
    'license': 'LGPL-3',
}

