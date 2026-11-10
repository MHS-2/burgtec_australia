{
    'name': "Burgtec Hubspot Customization",
    'version': '18.0.1.0.0',
    'summary': "Customization related to Burgtec Hubspot",
    'description': """
    This module contains all the customizations related to the Burgtec Hubspot, 
    including UI tweaks, business logic changes, and additional features 
    specific to Burgtec's requirements.
    """,
    'author': "",
    'website': "",
    'category': 'Customizations',
    'depends': ['base', 'sale', 'sale_custom_report', 'purchase', 'quotation_type_customization','mail'],
    'data': [
        'security/products_security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        "data/ir_action_data.xml",
        'views/res_config_settings_views.xml',
        'views/hubspot_ticket_data.xml',
        'views/sale_order_ext.xml',
        'views/purchase_order_ext.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
    'auto_install': False,
}
