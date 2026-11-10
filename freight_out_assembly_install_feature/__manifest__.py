{
    'name': "Freight Out Assembly/Install Feature",
    'summary': "",
    'description': """
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Customizations',
    'version': '0.1',
    'depends': ['bom_based_inventory','filter_one2many_fields','sale_custom_report','quotation_type_customization'],
    "data": [
        'data/product_product_data.xml',
        'views/sale_order_bom_component_view_ext.xml',
        'wizards/bulk_action_operations.xml'
    ],
    'installable': True,
    'license': 'LGPL-3',
    'auto_install': False,
}
