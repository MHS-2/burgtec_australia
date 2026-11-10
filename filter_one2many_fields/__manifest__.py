# -*- coding: utf-8 -*-
{
    'name': "filter_one2many_fields",

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
    'depends': ['sale_custom_report','sale_order_customisation','bom_based_floating_table'],

    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "wizards/bulk_action_operations.xml",
        "views/sale_order_bom_component_ext_view.xml",
        "views/sale_order_extended_view.xml",
    ],
    'license': 'LGPL-3',
}

