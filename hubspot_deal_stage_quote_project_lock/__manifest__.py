{
    "name": "HubSpot Project Quotation Lock",
    "version": "18.0.1.0.0",
    "category": "Customizations",
    "summary": "Lock Project based on the HubSpot Deal Stage of the Associated Deal",
    "description": """
Locks Sales Quotations based on the related HubSpot Deal stage.
Useful to prevent edits once a deal reaches defined stages (e.g., Negotiation, Closed Won).
""",
    "author": "Your Company",
    "website": "https://yourcompany.example.com",
    "license": "LGPL-3",
    "depends": [
        "quotation_type_customization",
        "update_crm_burgtec",
        "sale_custom_report",
        "account",
        'new_delivery_stage_feature',
        'hubspot_ticket_creation_ps',
        "bom_based_inventory",
        "sale_order_customisation",
    ],
    "data": [
        'data/data.xml',
        "views/sale_order_ext.xml",
        "views/sale_order_bom_component_view_ext.xml",
        "views/planning_screen_ext.xml",
        "views/delivery_code_calculation_view_ext.xml",
        # "views/view_split_do_form_ext.xml",

    ],
    "assets": {
        "web.assets_backend": [
            ("after", "hubspot_ticket_creation_ps/static/src/js/*",
             "hubspot_deal_stage_quote_project_lock/static/src/js/*"),
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
}
