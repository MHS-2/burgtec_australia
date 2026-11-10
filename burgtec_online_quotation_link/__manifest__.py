{
    'name': "Burgtec Online Quotation Link",
    'summary': "Public no-login quotation review page (tokenized link)",
    'author': "Byte Legions",
    'category': 'Sales/Sales',
    'version': '18.0.1.1.0',
    'depends': [
        'sale_management',
        'portal',
        'bom_based_inventory',
        'dpg_sale_custom_report',
        'auto_lock_sales_quote_upon_project_creation',
    ],
    'data': [
        'views/sale_order_ext_view.xml',
        'views/quotation_review_template.xml',
        'views/planning_screen_view_ext.xml',
    ],
    'assets': {

        'web.assets_frontend': [
            'burgtec_online_quotation_link/static/src/quotation_data/quotation_data.js',
            'burgtec_online_quotation_link/static/src/quotation_data/quotation_data.xml',
            'burgtec_online_quotation_link/static/src/quotation_data/quotation_data.scss',
            'burgtec_online_quotation_link/static/src/custom_dialog/custom_dialog.js',
            'burgtec_online_quotation_link/static/src/custom_dialog/custom_dialog.xml',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
