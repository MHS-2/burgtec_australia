{
    'name': 'List View User Preferences',
    'version': '18.0.2.0.0',
    'category': 'Technical',
    'summary': 'Per-user list view column preferences (visibility + width) stored on the server',
    'description': """
List View User Preferences
==========================
Saves each user's list view column preferences on the server so they persist
across browsers, devices and sessions.

Features
--------
- Optional column show/hide, per user, restored on login from any device.
- Column WIDTH, per user: resize a column once and it keeps that exact width
  (login/logout, reload, filters, grouping, window resize).
- Works on regular list views and on x2many (one2many/many2many) sub-lists,
  each keyed separately (core `createViewKey`).
- Non-blocking: if the server is unreachable, Odoo's native behaviour applies.

How the width part works
------------------------
Odoo 18 sizes columns in `web/static/src/views/list/column_width_hook.js`.
`getWidthSpecs()` treats an arch attribute `width="130px"` as minWidth == maxWidth,
i.e. a pinned column that the layout algorithm may neither shrink nor expand.
This module injects the user's saved width as that attribute at render time,
so the native algorithm enforces it and redistributes the remaining space over
the other columns. No DOM patching, no re-apply loops.
    """,
    'author': '',
    'website': '',
    'depends': ['web','sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/list_view_preference.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'list_view_user_preferences/static/src/js/list_view_preference_service.js',
            'list_view_user_preferences/static/src/js/list_renderer_patch.js',
            'list_view_user_preferences/static/src/js/list_column_width_patch.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
