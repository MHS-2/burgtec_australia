{
    'name': 'BOM Based Floating Table',
    'version': '18.0.1.0.0',
    'summary': 'Floating margin analysis panel on Sale Orders',
    'sequence': 10,
    'description': """
        Shows a floating margin analysis panel on the right side
        of the sale order form when chatter is hidden.
    """,
    'category': 'Sales',
    'depends': ['sale_management', 'bom_based_inventory'],
    'data': [
        'views/sale_order_ext.xml',
        'views/sale_order_bom_component_ext.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'bom_based_floating_table/static/src/components/margin_floating_panel/margin_floating_panel.js',
            'bom_based_floating_table/static/src/components/margin_floating_panel/margin_floating_panel.scss',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
