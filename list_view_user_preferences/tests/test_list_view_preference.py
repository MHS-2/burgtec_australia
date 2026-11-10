import json

from odoo.tests.common import TransactionCase, HttpCase, tagged


@tagged('post_install', '-at_install')
class TestListViewUserPreference(TransactionCase):
    """Test the list.view.user.preference model."""

    def setUp(self):
        super().setUp()
        self.Preference = self.env['list.view.user.preference']
        self.user = self.env.ref('base.user_admin')

    def test_create_preference(self):
        """Test creating a new preference record."""
        pref = self.Preference.create({
            'user_id': self.user.id,
            'view_key': 'optional_fields,sale.order,list,42,amount_total,partner_id',
            'active_fields': 'amount_total,partner_id,date_order',
        })
        self.assertTrue(pref.id)
        self.assertEqual(pref.user_id, self.user)
        self.assertEqual(pref.active_fields, 'amount_total,partner_id,date_order')

    def test_unique_constraint(self):
        """Test that duplicate user + view_key raises an error."""
        self.Preference.create({
            'user_id': self.user.id,
            'view_key': 'optional_fields,res.partner,list,10',
            'active_fields': 'email,phone',
        })
        with self.assertRaises(Exception):
            self.Preference.create({
                'user_id': self.user.id,
                'view_key': 'optional_fields,res.partner,list,10',
                'active_fields': 'email',
            })

    def test_update_preference(self):
        """Test updating an existing preference."""
        pref = self.Preference.create({
            'user_id': self.user.id,
            'view_key': 'optional_fields,account.move,list,55',
            'active_fields': 'amount_total',
        })
        pref.write({'active_fields': 'amount_total,partner_id'})
        self.assertEqual(pref.active_fields, 'amount_total,partner_id')

    def test_delete_on_user_cascade(self):
        """Test that preferences are deleted when user is deleted."""
        test_user = self.env['res.users'].create({
            'name': 'Test Pref User',
            'login': 'test_pref_user',
        })
        pref = self.Preference.create({
            'user_id': test_user.id,
            'view_key': 'optional_fields,sale.order,list,1',
            'active_fields': 'name',
        })
        pref_id = pref.id
        test_user.unlink()
        self.assertFalse(self.Preference.search([('id', '=', pref_id)]))

    def test_empty_active_fields(self):
        """Test preference with no active fields (all optional columns hidden)."""
        pref = self.Preference.create({
            'user_id': self.user.id,
            'view_key': 'optional_fields,purchase.order,list,99',
            'active_fields': '',
        })
        self.assertEqual(pref.active_fields, '')


@tagged('post_install', '-at_install')
class TestListViewPreferenceController(HttpCase):
    """Test the JSON-RPC controller endpoints."""

    def test_save_and_load_preferences(self):
        """Test saving and loading preferences via controller."""
        self.authenticate('admin', 'admin')

        # Save a preference
        save_response = self.url_open(
            '/web/list_view/save_preference',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'id': 1,
                'params': {
                    'view_key': 'optional_fields,sale.order,list,42',
                    'active_fields': 'amount_total,partner_id',
                },
            }),
            headers={'Content-Type': 'application/json'},
        )
        save_result = save_response.json()
        self.assertTrue(save_result.get('result'))

        # Load all preferences
        load_response = self.url_open(
            '/web/list_view/load_all_preferences',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'id': 2,
                'params': {},
            }),
            headers={'Content-Type': 'application/json'},
        )
        load_result = load_response.json()
        prefs = load_result.get('result', {})
        self.assertIn('optional_fields,sale.order,list,42', prefs)
        self.assertEqual(
            prefs['optional_fields,sale.order,list,42'],
            'amount_total,partner_id',
        )

    def test_update_existing_preference(self):
        """Test that saving again updates instead of duplicating."""
        self.authenticate('admin', 'admin')

        for active_fields in ['field_a', 'field_a,field_b']:
            self.url_open(
                '/web/list_view/save_preference',
                data=json.dumps({
                    'jsonrpc': '2.0',
                    'method': 'call',
                    'id': 1,
                    'params': {
                        'view_key': 'optional_fields,test.model,list,1',
                        'active_fields': active_fields,
                    },
                }),
                headers={'Content-Type': 'application/json'},
            )

        # Load and verify only latest value exists
        load_response = self.url_open(
            '/web/list_view/load_all_preferences',
            data=json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'id': 2,
                'params': {},
            }),
            headers={'Content-Type': 'application/json'},
        )
        prefs = load_response.json().get('result', {})
        self.assertEqual(
            prefs.get('optional_fields,test.model,list,1'),
            'field_a,field_b',
        )


@tagged('post_install', '-at_install')
class TestListViewColumnWidth(TransactionCase):
    """Per-user column widths, and non-regression of the optional columns."""

    def setUp(self):
        super().setUp()
        self.Preference = self.env['list.view.user.preference']
        self.base_key = 'sale.order.line,list,order_line,list,name,price_unit'

    def test_set_for_user_creates_then_updates(self):
        key = 'column_widths,' + self.base_key
        self.Preference._set_for_user(key, {'column_widths': {'price_unit': 130}})
        pref = self.Preference.search([
            ('user_id', '=', self.env.uid), ('view_key', '=', key),
        ])
        self.assertEqual(len(pref), 1)
        self.assertEqual(pref.column_widths, {'price_unit': 130})

        self.Preference._set_for_user(
            key, {'column_widths': {'price_unit': 130, 'name': 240}})
        pref = self.Preference.search([
            ('user_id', '=', self.env.uid), ('view_key', '=', key),
        ])
        self.assertEqual(len(pref), 1, "must update, not duplicate")
        self.assertEqual(pref.column_widths, {'price_unit': 130, 'name': 240})

    def test_widths_are_per_user(self):
        key = 'column_widths,res.partner,list,42,email,name'
        other = self.env['res.users'].create({
            'name': 'Other Width User', 'login': 'other_width_user',
        })
        self.Preference._set_for_user(key, {'column_widths': {'name': 300}})
        self.Preference.with_user(other)._set_for_user(key, {'column_widths': {'name': 90}})

        mine = self.Preference.search([('user_id', '=', self.env.uid), ('view_key', '=', key)])
        theirs = self.Preference.search([('user_id', '=', other.id), ('view_key', '=', key)])
        self.assertEqual(mine.column_widths, {'name': 300})
        self.assertEqual(theirs.column_widths, {'name': 90})

    def test_widths_and_optional_fields_never_collide(self):
        """Widths and optional columns live in separate rows and columns."""
        self.Preference._set_for_user(
            'optional_fields,' + self.base_key, {'active_fields': 'price_unit'})
        self.Preference._set_for_user(
            'column_widths,' + self.base_key, {'column_widths': {'price_unit': 130}})

        opt = self.Preference.search([
            ('user_id', '=', self.env.uid), ('view_key', '=', 'optional_fields,' + self.base_key),
        ])
        wid = self.Preference.search([
            ('user_id', '=', self.env.uid), ('view_key', '=', 'column_widths,' + self.base_key),
        ])
        self.assertEqual(len(opt), 1)
        self.assertEqual(len(wid), 1)
        # saving one never blanks the other
        self.assertEqual(opt.active_fields, 'price_unit')
        self.assertFalse(opt.column_widths)
        self.assertEqual(wid.column_widths, {'price_unit': 130})
        self.assertFalse(wid.active_fields)

    def test_resaving_widths_keeps_active_fields(self):
        """Width rows and optional-field rows are independent even on rewrite."""
        key_opt = 'optional_fields,' + self.base_key
        self.Preference._set_for_user(key_opt, {'active_fields': 'a,b'})
        self.Preference._set_for_user('column_widths,' + self.base_key,
                                      {'column_widths': {'a': 120}})
        self.Preference._set_for_user('column_widths,' + self.base_key,
                                      {'column_widths': {'a': 120, 'b': 200}})
        opt = self.Preference.search([
            ('user_id', '=', self.env.uid), ('view_key', '=', key_opt),
        ])
        self.assertEqual(opt.active_fields, 'a,b')


@tagged('post_install', '-at_install')
class TestOptionalFieldsPayloadNonRegression(HttpCase):
    """The optional-columns endpoint must keep its original flat payload."""

    def test_payload_shape_unchanged_and_excludes_width_rows(self):
        self.authenticate('admin', 'admin')
        admin = self.env['res.users'].search([('login', '=', 'admin')], limit=1)
        Pref = self.env['list.view.user.preference']
        Pref.create({
            'user_id': admin.id,
            'view_key': 'optional_fields,res.partner,list,7,email,name',
            'active_fields': 'email',
        })
        Pref.create({
            'user_id': admin.id,
            'view_key': 'column_widths,res.partner,list,7,email,name',
            'column_widths': {'email': 150},
        })
        self.env.cr.flush()

        response = self.url_open(
            '/web/list_view/load_all_preferences',
            data=json.dumps({
                'jsonrpc': '2.0', 'method': 'call', 'id': 1, 'params': {},
            }),
            headers={'Content-Type': 'application/json'},
        )
        prefs = response.json().get('result', {})
        # flat {view_key: "a,b"} exactly as before
        self.assertEqual(prefs.get('optional_fields,res.partner,list,7,email,name'), 'email')
        # width-only rows must not leak in (they would read as "all columns hidden")
        self.assertNotIn('column_widths,res.partner,list,7,email,name', prefs)
