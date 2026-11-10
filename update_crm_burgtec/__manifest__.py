# -*- coding: utf-8 -*-
{
    'name': "update_crm_burgtec",

    'summary': "CRM will be used as a first layer in sales process linked with hubspot as deal",

    'description': """
CRM will be used as a first layer in sales process linked with hubspot as deal
    """,

    'author': "Byte Legions",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customizations',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'crm', 'sale_crm', 'sale_custom_report', 'quotation_type_customization',
                'burgtec_hubspot_customization', 'contacts','sales_team','xero_customization'],

    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "data/ir_action_data.xml",
        "views/crm_lead_view_extended.xml",
        "views/deal_stage_views.xml",
        "views/deal_location_views.xml",
        "views/deal_pipeline_stage_views.xml",
        "views/deal_type_views.xml",
        "views/res_partner_ext.xml",
        "views/sale_order_view_extended.xml",
        "views/hubspot_meeting_types.xml",
        "views/hubspot_meeting_data.xml",
        "views/res_users_ext_views.xml",
        "views/site_details_report_view.xml"
    ],

    'assets': {
        'web.assets_backend': [
            'update_crm_burgtec/static/src/components/CrmSaleController/*',
        ]
    },
    'license': 'LGPL-3',
}
