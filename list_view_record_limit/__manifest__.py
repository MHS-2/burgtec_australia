{
    # Module Info
    'name': "List View Record Limit",
    'version': '18.0.1.0.0',
    'summary': """Control number of records are displayed in Odoo list (tree) views.""",
    "description": """
        This module allows users to set a record limit for list/tree views in Odoo. 
        By limiting the number of records shown, it helps improve screen performance, reduce load time, 
        and keep large datasets easier to manage. The limit can be configured based on business needs without changing core Odoo code.
    """,
    'license': 'LGPL-3',


    # Author
    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Dependencies
    'depends': [
        "base",
        "web",
        "bom_based_inventory"
    ],

    'data': [
        "views/sale_order_bom_component_views.xml"
    ],

    'assets': {
        'web.assets_backend': [
            'list_view_record_limit/static/src/js/list_limit.js',
        ]
    },


    # Technical Spec
    'installable': True,
    'application': False,
    'auto_install': False,
}

