from odoo import api, fields, models


class ListViewUserPreference(models.Model):
    _name = 'list.view.user.preference'
    _description = 'List View User Column Preference'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
        index=True,
        default=lambda self: self.env.user,
    )
    view_key = fields.Char(
        string='View Key',
        required=True,
        index=True,
        help='Unique key identifying the list view (model, view ID, field names). '
             'Prefixed by the preference type: "optional_fields," or "column_widths,".',
    )
    active_fields = fields.Text(
        string='Active Optional Fields',
        help='Comma-separated list of optional field names that are visible',
    )
    column_widths = fields.Json(
        string='Column Widths',
        help='{field_name: width_in_px} set by the user by dragging the column border. '
             'Width excludes the cell padding, same unit as arch width="Npx".',
    )

    _sql_constraints = [
        (
            'user_view_key_unique',
            'UNIQUE(user_id, view_key)',
            'A preference record must be unique per user and view key.',
        ),
    ]

    @api.model
    def _set_for_user(self, view_key, vals):
        """Create or update the current user's preference row for `view_key`."""
        pref = self.search([
            ('user_id', '=', self.env.uid),
            ('view_key', '=', view_key),
        ], limit=1)
        if pref:
            pref.write(vals)
        else:
            self.create(dict(vals, user_id=self.env.uid, view_key=view_key))
        return True
