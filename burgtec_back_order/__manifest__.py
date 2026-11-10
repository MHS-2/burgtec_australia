# -*- coding: utf-8 -*-
{
    'name': "burgtec_back_order",

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
    'depends': ['stock','quotation_type_customization'],

    # always loaded
    'data': [
        "security/ir.model.access.csv",
        "views/back_order_planning_view.xml",
        "views/planning_screen_views.xml",
        'views/back_order_color_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'burgtec_back_order/static/src/xml/custom_color_picker_widget.xml',
            'burgtec_back_order/static/src/js/custom_color_picker_widget.js',
            'burgtec_back_order/static/src/css/color_picker.css',
            ('after', 'web/static/src/views/list/list_renderer.xml', 'burgtec_back_order/static/src/xml/color_picker.xml'),
            'burgtec_back_order/static/src/js/color_picker.js',
            'burgtec_back_order/static/src/components/back_order_allocation_matrix.js',
            'burgtec_back_order/static/src/components/back_order_allocation_matrix.xml',
            'burgtec_back_order/static/src/components/back_order_allocation_matrix.scss',
        ]
    },
    'license': 'LGPL-3',
}

