{
    'name': "burgtec_delivery_report",
    'summary': "Detailed Report For Delivery Stage, According to the Child Purchase Order",
    'description': """
       
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Customizations',
    'version': '0.1',
    'depends': ['base', 'sale', 'web', 'purchase', 'iot', 'sale_management', 'sale_custom_report',
                'quotation_type_customization', 'bom_based_inventory','burgtec_hubspot_customization'],
    'data': [
        'data/ir_action_data.xml',
        'report/burgtec_delivery_report.xml',
        'report/delivery_label_template.xml',
        'report/burgtec_delivery_label_zpl.xml',
        'views/sale_order_ext.xml',
        'views/res_partner_ext_view.xml',

    ],
    "assets": {
        "web.assets_backend": [
            "burgtec_delivery_report/static/src/js/chatter_toggle.js",
            "burgtec_delivery_report/static/src/scss/chatter_toggle.scss",
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
