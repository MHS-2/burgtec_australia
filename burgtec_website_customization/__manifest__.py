{
    'name': "Burgtec Website Customization",
    'version': '18.0.1.0.0',
    'summary': "Customization related to Burgtec Website",
    'description': """
    This module contains all the customizations related to the Burgtec website, 
    including UI tweaks, business logic changes, and additional features 
    specific to Burgtec's requirements.
    """,
    'author': "",
    'website': "",
    'category': 'Customizations',
    'depends': ['base', 'web', 'website', 'stock', 'product', 'website_sale', 'sale_custom_report',
                'm2m_attachment_carousel_view'],
    "data": [
        "security/ir_rules.xml",
        "security/ir.model.access.csv",
        "data/ir_action_data.xml",
        "views/optional_groups_views.xml",
        "views/preconfigured_attribute_option.xml",
        "views/product_attribute_views.xml",
        "views/product_product_ext.xml",
        "views/product_template_attribute_value_view_extended.xml",
        "views/product_template_ext.xml",
        "views/material_allocation_view.xml",
        "views/sub_attribute_view.xml",
        "views/sub_attribute_type_view.xml",
        "views/website_product_category_view.xml",
        "views/zone_postal_code_views.xml",
        "views/zone_postal_views.xml"
    ],
    'installable': True,
    'license': 'LGPL-3',
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'burgtec_website_customization/static/src/js/burgtec_product_configurator_dialog.js',
            # 'burgtec_website_customization/static/src/xml/product_template_attribute_line_ext.xml',
            # 'burgtec_website_customization/static/src/scss/product_configurator_dialog_fix.scss',
        ],
    },
}
