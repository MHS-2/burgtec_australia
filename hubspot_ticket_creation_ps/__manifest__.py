{
    'name': 'Hubspot Ticket Creation From Planning Screen',
    'version': '18.0.1.0',
    'summary': 'Hubspot Ticket Creation PS',
    'description': '''
        Hubspot Ticket Creation PS
    ''',
    'category': 'Customizations',
    'author': '',
    'company': '',
    'maintainer': '',
    'website': '',
    'depends': ['sale_order_customisation', 'burgtec_hubspot_customization','new_delivery_stage_feature', 'quotation_type_customization', 'account'],
    'data': [
        'views/planning_screen_ext.xml',
        'views/res_partner_view_ext.xml',
        'views/sale_order_bom_component_view_ext.xml',
    ],
    "assets": {
    "web.assets_backend": [
        ("after", "sale_order_customisation/static/src/js/sale_order_line_field/*", "hubspot_ticket_creation_ps/static/src/js/*"),

    ],
},
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
