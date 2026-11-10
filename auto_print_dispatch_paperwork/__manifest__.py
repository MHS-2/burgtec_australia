{
    'name': 'Auto Print Dispatch Paperwork',
    'version': '18.1',
    'summary': 'Auto Print Dispatch Paperwork',
    'sequence': -1,
    'description': """

            """,
    'category': 'Customizations',
    'website': '',
    'depends': ['base', 'sale_management', 'sale', 'burgtec_hubspot_customization', 'burgtec_delivery_report'],
    'data': [
        'views/sale_order_ext.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
