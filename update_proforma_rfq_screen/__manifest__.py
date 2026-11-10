# -*- coding: utf-8 -*-
{
    'name': "update_proforma_rfq_screen",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['web','account','quotation_type_customization','filter_one2many_fields'],

    # always loaded
    'data': [
        "security/ir.model.access.csv",
        "report/proforma_rfq_vendor_report.xml",
        "views/sale_order_bom_component_views.xml",
        'views/sale_order_bom_component_line_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'update_proforma_rfq_screen/static/src/components/section_note_button/*',
        ],
    },
    'license': 'LGPL-3',
}

