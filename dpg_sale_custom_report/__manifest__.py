{
    'name': "DPG Sale Custom Report",
    'summary': "Detailed DPG Custom Report For Sale Order, According to the Project Reference in Sale Order",
    'description': """
        DPG Sale Quote Report, according to burgtec bussiness logic.
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Customizations',
    'version': '0.1',
    'depends': ['base','project','sale', 'bom_based_inventory','web','burgtec_simple_quote'],
    "data": [
        "report/dpg_sale_custom_report.xml",
        "report/dpg_system_delivery_docket_report.xml",
        "report/dpg_invoice_report.xml",
        "views/simple_sale_quote_views.xml",
        "report/dpg_sale_confirmation_report.xml",
    ],
    "assets": {
        "web.report_assets_common" : [
            "/dpg_sale_custom_report/static/src/less/fonts.less",
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
