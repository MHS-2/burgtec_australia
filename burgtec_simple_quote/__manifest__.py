# -*- coding: utf-8 -*-
{
    'name': "burgtec_simple_quote",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customizations',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'update_crm_burgtec', 'update_proforma_rfq_screen', 'sale_order_customisation',
                'non_zero_component_quantity', 'auto_lock_sales_quote_upon_project_creation', 'sale_area_allocation',
                'crm_onedrive_integration'],

    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/crm_lead_view_ext.xml",
        "views/sale_order_series_view_ext.xml",
        # "wizards/simple_quote_entry_wizard.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'burgtec_simple_quote/static/src/scss/simple_wizard.scss',
            'burgtec_simple_quote/static/src/components/margin_floating_panel/margin_floating_panel.js',

        ]
    },
    'license': 'LGPL-3',
    'application': True,
    'installable': True,

}
