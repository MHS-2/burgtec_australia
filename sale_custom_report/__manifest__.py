{
    'name': "sale_custom_report",
    'summary': "Detailed Custom Report For Sale Order, According to the Project Reference in Sale Order",
    'description': """
        Sale Quote Report, according to burgtec bussiness logic. Fetches all Sale Order and Lines depending on the Project Reference and display them in single report.
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Customizations',
    'version': '0.1',
    'depends': ['base','project','sale', 'bom_based_inventory','web'],
    "data": [
        "data/ir_action_data.xml",
        "data/sequence_data.xml",
        "security/ir.model.access.csv",
        "views/delivery_code_calculation_view.xml",
        "views/product_delivery_cost_group_code.xml",
        "views/product_product_views.xml",
        "views/product_template_extended.xml",
        "views/project_project_extended.xml",
        "views/purchase_order_ext_view.xml",
        "views/sale_order_bom_component_line_ext.xml",
        "views/sale_order_extended.xml",
        "report/sale_quote_burgtec_report.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "/sale_custom_report/static/src/js/web_widget_image_paste_upload.js",
            "/sale_custom_report/static/src/xml/web_widget_image_paste_upload.xml",
        ],
        "web.report_assets_common" : [
            "/sale_custom_report/static/src/less/fonts.less",
        ],
        # "web.report_assets_pdf": [
        #     "/sale_custom_report/static/src/less/fonts.less",
        # ],
    },
    'installable': True,
    'license': 'LGPL-3',
}

