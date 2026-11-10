# -*- coding: utf-8 -*-
{
    'name': "burgtec_list_views",

    'summary': "This Module will be used to show all fields from different odoo modules of Sales and Purchase In One List View.",

    'description': """
This Module will be used to show all fields from different odoo modules of Sales and Purchase In One List View.
    """,

    'author': "Byte Legions",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'website_sale', 'sale_custom_report', 'quotation_type_customization',
                'burgtec_hubspot_customization',
                'purchase_order_custom_report', 'purchase_back_order_report', 'purchase_order_down_payment',
                'artwork_url_attachment_for_screens','dpg_sale_custom_report'],

    # always loaded
    'data': [
        'views/views.xml',
        'views/planning_screen_view_ext.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'burgtec_list_views/static/src/js/sticky_planning_lines.js',
            'burgtec_list_views/static/src/scss/sticky_planning_lines.scss',
        ],
    },
    'license': 'LGPL-3',

}
