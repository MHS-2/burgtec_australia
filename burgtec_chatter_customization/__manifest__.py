{
    'name': "burgtec_chatter_customization",
    'summary': "Burgtec Chatter Customization",
    'description': """
    """,
    'author': "",
    'website': "",
    'category': '',
    'version': '0.1',
    'depends': ['base','bom_based_inventory','sale_quote_planning_screen','quotation_type_customization','new_delivery_stage_feature','bom_based_floating_table','hubspot_deal_stage_quote_project_lock','auto_lock_sales_quote_upon_project_creation','mail'],
    'data': [
        'views/sale_order_bom_component_view_ext.xml',
        'views/planning_screen_view_ext.xml',
        'views/preplanning_screen_view_ext.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

