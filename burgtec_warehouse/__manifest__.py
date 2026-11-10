# -*- coding: utf-8 -*-
{
    'name': "burgtec_warehouse",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Inventory/Purchase',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','update_crm_burgtec','purchase'],

    # always loaded
    'data': [
        'security/burgtec_warehouse_groups.xml',
        "security/ir.model.access.csv",
        "data/burgtec_warehouse_sequence.xml",
        "views/warehouse_receiving_views.xml",
        'views/warehouse_dispatching_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'burgtec_warehouse/static/src/components/live_warehouse_receiving/live_warehouse_receiving.js',
            'burgtec_warehouse/static/src/components/live_warehouse_receiving/live_warehouse_receiving.xml',
            'burgtec_warehouse/static/src/components/live_warehouse_receiving/live_warehouse_receiving.scss',
            'burgtec_warehouse/static/src/components/live_warehouse_dispatching/live_warehouse_dispatching.js',
            'burgtec_warehouse/static/src/components/live_warehouse_dispatching/live_warehouse_dispatching.scss',
            'burgtec_warehouse/static/src/components/live_warehouse_dispatching/live_warehouse_dispatching.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

