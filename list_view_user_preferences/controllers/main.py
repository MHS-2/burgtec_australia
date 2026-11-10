from odoo import http
from odoo.http import request


class ListViewPreferenceController(http.Controller):

    # ------------------------------------------------------------------
    # Optional columns (show/hide) - UNCHANGED payload shape and route
    # names, so the existing JS keeps working as-is.
    # ------------------------------------------------------------------

    @http.route('/web/list_view/load_all_preferences', type='json', auth='user')
    def load_all_preferences(self):
        """Load all list view column preferences for the current user.

        :return: {view_key: 'field_a,field_b'}
        """
        preferences = request.env['list.view.user.preference'].search([
            ('user_id', '=', request.env.uid),
            ('active_fields', '!=', False),
        ])
        return {pref.view_key: pref.active_fields or '' for pref in preferences}

    @http.route('/web/list_view/save_preference', type='json', auth='user')
    def save_preference(self, view_key, active_fields):
        """Save a list view column preference for the current user."""
        return request.env['list.view.user.preference']._set_for_user(
            view_key, {'active_fields': active_fields},
        )

    # ------------------------------------------------------------------
    # Column widths - separate routes, separate rows (view_key prefixed
    # 'column_widths,'), separate column. Nothing above is touched.
    # ------------------------------------------------------------------

    @http.route('/web/list_view/load_all_column_widths', type='json', auth='user')
    def load_all_column_widths(self):
        """Load all manually resized column widths for the current user.

        :return: {view_key: {field_name: width_in_px}}
        """
        preferences = request.env['list.view.user.preference'].search([
            ('user_id', '=', request.env.uid),
            ('column_widths', '!=', False),
        ])
        return {pref.view_key: pref.column_widths for pref in preferences}

    @http.route('/web/list_view/save_column_widths', type='json', auth='user')
    def save_column_widths(self, view_key, widths):
        """Save the manually resized column widths of one list view."""
        return request.env['list.view.user.preference']._set_for_user(
            view_key, {'column_widths': widths or False},
        )
