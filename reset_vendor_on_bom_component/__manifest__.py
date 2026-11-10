{
    'name': "Reset Vendor On Bom Component",
    'version': '18.0.1.0.0',
    'summary': "This module allows you to reset Vendor On Bom Component",
    'description': """
    """,
    'author': "",
    'website': "",
    'category': 'Customizations',
    'depends': ['bom_based_inventory','auto_lock_sales_quote_upon_project_creation'],
    'data': [
        'views/sale_order_bom_component_view_ext.xml'

    ],
    'installable': True,
    'license': 'LGPL-3',
    'auto_install': False,
}
