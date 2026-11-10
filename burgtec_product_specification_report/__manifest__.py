{
    'name': "product_specification_report",
    'summary': "Product Specification Detailed Report For Sale Order",
    'description': """
       
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Customizations',
    'version': '0.1',
    'depends': ['base', 'sale', 'web', 'purchase', 'sale_custom_report'],
    'data': [
        'security/ir.model.access.csv',
        'view/sale_order_ext.xml',
        'report/burgtec_product_specification_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
             'burgtec_product_specification_report/static/src/**',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
