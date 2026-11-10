{
    'name': 'CRM OneDrive Folder Integration',
    'version': '18.0.1.1.0',
    'category': 'Sales/CRM',
    'summary': 'Automatically create a OneDrive folder when a CRM lead is created',
    'description': """
CRM OneDrive Folder Integration
================================
Automatically creates a folder in OneDrive (via Microsoft Graph API) named after
the CRM lead whenever a new lead is created. Stores the resulting folder URL on
the lead so the team can jump straight into it.

Configuration is done in Settings -> CRM with the Azure AD application
Tenant ID, Client ID, Client Secret, and the target OneDrive user.
    """,
    'author': '',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['update_crm_burgtec'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/crm_lead_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
