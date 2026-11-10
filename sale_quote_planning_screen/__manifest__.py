# -*- coding: utf-8 -*-
{
    'name': "Sale Quote Planning Screen",
    'summary': "This module allows you to manage planning screen of sale quotes",
    'description': """""",
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Customizations',
    'version': '0.1',
    'depends': ['base', 'bom_based_inventory', 'quotation_type_customization', 'burgtec_registers_customization'],

    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_ext.xml',
        'views/sale_quote_planning_screen.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_quote_planning_screen/static/src/js/url_field_warning.js',
            'sale_quote_planning_screen/static/src/xml/url_field_warning.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
