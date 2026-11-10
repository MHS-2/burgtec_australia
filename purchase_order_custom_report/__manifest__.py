# -*- coding: utf-8 -*-
{
    'name': "purchase_order_custom_report",

    'summary': "Customising Purchase Order Report For Burgtec",

    'description': """
        Custom PDF Report For Purchase Order
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customizations',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'purchase', 'bom_based_inventory','sale_custom_report'],

    # always loaded
    "data": [
        # "security/ir.model.access.csv",
        "data/mail_template_data.xml",
        "data/purchase_mail_template_data.xml",
        "data/purchase_cron.xml",
        "views/purchase_view_ext.xml",
        "report/purchase_burgtec_report.xml"
    ],
    'license': 'LGPL-3',
}

