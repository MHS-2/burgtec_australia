# -*- coding: utf-8 -*-
{
    'name': "burgtec_registers_customization",

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
    'depends': ['base','bom_based_inventory','quotation_type_customization','mail'],

    # always loaded
    "data": [
        "data/burgtec_registers_customization_sequence.xml",
        "security/ir.model.access.csv",
        "views/icr_register_views.xml",
        "views/nscr_register_view.xml",
        "views/product_product_views.xml",
        "views/sale_order_bom_component_views.xml",
        "views/sale_order_view_ext.xml",
        "wizard/component_existing_nscr_selection.xml",
        "wizard/nscr_creation_choice.xml"
    ],
    'license': 'LGPL-3',
}

