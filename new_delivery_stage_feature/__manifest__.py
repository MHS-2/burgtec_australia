# -*- coding: utf-8 -*-
{
    'name': "new_delivery_stage_feature",

    'summary': "This Module modifies Sale Order Functionality. ",

    'description': """
                    This Module modifies Sale Order Functionality. Making a link between (Source) Sale Order (Sale Quote) and Child Sale Orders (Project Quote)
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customizations',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['sale_custom_report','bom_based_inventory'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_form_view_inherit.xml',
        'views/planning_screen_view.xml',
    ],
        'assets': {
        'web.assets_backend': [
            # 'new_delivery_stage_feature/static/src/js/*.js',
            'new_delivery_stage_feature/static/src/**/*.js',
            # 'new_delivery_stage_feature/static/src/views/**/*',
        ]
    },
    'license': 'LGPL-3',
}

