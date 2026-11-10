# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, tagged

PDF = b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n'


@tagged('post_install', '-at_install')
class TestWordpressDealApi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Key = cls.env['wordpress.api.key']
        future = fields.Datetime.now() + timedelta(days=1)
        cls.key_rec, cls.key = Key._generate('test key', future)
        cls.expired_rec, cls.expired_key = Key._generate(
            'expired key', fields.Datetime.now() - timedelta(minutes=1))
        cls.revoked_rec, cls.revoked_key = Key._generate('revoked key', future)
        cls.revoked_rec.active = False
        # A genuine, valid native Odoo API key of the administrator.
        admin = cls.env.ref('base.user_admin')
        cls.admin_key = cls.env['res.users.apikeys'].with_user(admin).sudo()._generate(
            None, 'native', datetime.now() + timedelta(days=1))
        cls.plain_user = cls.env['res.users'].create({
            'name': 'Plain User', 'login': 'wp_plain_user',
            'groups_id': [Command.set([cls.env.ref('base.group_user').id])],
        })
        cls.lead = cls.env['crm.lead'].create({
            'name': 'WP Test Deal',
            'project_name': 'WP Test Project',
            'odoo_deal_number_6digit': '999001',
            'location': 'nsw',
        })

    def _headers(self, key=None, **extra):
        headers = dict(extra)
        if key:
            headers['Authorization'] = 'Bearer %s' % key
        return headers

    def _get(self, path, key=None):
        return self.url_open(path, headers=self._headers(key))

    def _post_note(self, deal_id, payload, key=None):
        return self.url_open(
            '/api/wp/v1/deals/%s/notes' % deal_id,
            data=json.dumps(payload),
            headers=self._headers(key or self.key, **{'Content-Type': 'application/json'}),
        )

    def _post_pdf(self, deal_id, filename='quote.pdf', content=PDF, data=None):
        return self.url_open(
            '/api/wp/v1/deals/%s/attachments' % deal_id,
            data=data or {},
            files={'file': (filename, content, 'application/pdf')},
            headers=self._headers(self.key),
        )

    # -- authentication ---------------------------------------------------
    def test_no_key_is_rejected(self):
        response = self._get('/api/wp/v1/deals')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error']['code'], 'unauthorized')
        self.assertEqual(response.headers.get('WWW-Authenticate'), 'Bearer')

    def test_wrong_key_is_rejected(self):
        self.assertEqual(self._get('/api/wp/v1/deals', 'wpk_not-a-real-key').status_code, 401)
        self.assertEqual(self._get('/api/wp/v1/deals', 'whatever').status_code, 401)

    def test_expired_key_is_rejected(self):
        self.assertEqual(self._get('/api/wp/v1/deals', self.expired_key).status_code, 401)

    def test_revoked_key_is_rejected(self):
        self.assertEqual(self._get('/api/wp/v1/deals', self.revoked_key).status_code, 401)

    def test_native_odoo_key_is_not_accepted(self):
        """Even an administrator's real Odoo API key must not open this API."""
        self.assertEqual(self._get('/api/wp/v1/deals', self.admin_key).status_code, 401)

    def test_wordpress_key_is_useless_for_odoo_rpc(self):
        """The whole point: this key cannot be used for Odoo's standard RPC."""
        self.assertFalse(
            self.env['res.users.apikeys']._check_credentials(scope='rpc', key=self.key))

    def test_key_is_stored_hashed_only(self):
        self.assertNotEqual(self.key_rec.key_hash, self.key)
        self.assertEqual(self.key_rec.key_hint, self.key[:8])
        self.assertTrue(self.key.startswith('wpk_'))
        self.assertEqual(
            self.env['wordpress.api.key'].sudo().search_count([('key_hash', '=', self.key)]), 0)

    def test_only_admin_can_see_keys(self):
        with self.assertRaises(AccessError):
            self.env['wordpress.api.key'].with_user(self.plain_user).search([])

    def test_last_used_is_recorded(self):
        self.key_rec.last_used = False
        self.assertEqual(self._get('/api/wp/v1/deals?limit=1', self.key).status_code, 200)
        self.assertTrue(self.key_rec.last_used)

    # -- generation wizard ------------------------------------------------
    def test_wizard_generates_a_working_key_shown_once(self):
        wizard = self.env['wordpress.api.key.wizard'].create({'name': 'wizard key', 'validity_days': 30})
        wizard.action_generate()
        self.assertEqual(wizard.state, 'done')
        token = wizard.key
        self.assertTrue(token.startswith('wpk_'))
        self.assertEqual(self._get('/api/wp/v1/deals?limit=1', token).status_code, 200)
        wizard.action_close()
        self.assertFalse(wizard.key)  # wiped after closing
        self.assertEqual(self._get('/api/wp/v1/deals?limit=1', token).status_code, 200)  # key itself still valid

    def test_wizard_validity_limits(self):
        wizard = self.env['wordpress.api.key.wizard'].create({'name': 'x', 'validity_days': 4000})
        with self.assertRaises(Exception):
            wizard.action_generate()

    # -- reading ----------------------------------------------------------
    def test_list_and_filter(self):
        response = self._get('/api/wp/v1/deals?deal_number=999001', self.key)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['id'], self.lead.id)
        self.assertEqual(data['results'][0]['project_name'], 'WP Test Project')

    def test_list_search_and_paging(self):
        response = self._get('/api/wp/v1/deals?q=WP Test&limit=1&offset=0', self.key)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['results']), 1)

    def test_bad_paging_values(self):
        self.assertEqual(self._get('/api/wp/v1/deals?limit=abc', self.key).status_code, 400)
        self.assertEqual(self._get('/api/wp/v1/deals?limit=1000', self.key).status_code, 400)

    def test_get_deal_and_missing(self):
        response = self._get('/api/wp/v1/deals/%s' % self.lead.id, self.key)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['deal']['deal_number'], '999001')
        self.assertEqual(self._get('/api/wp/v1/deals/999999999', self.key).status_code, 404)

    def test_only_whitelisted_fields_returned(self):
        deal = self._get('/api/wp/v1/deals/%s' % self.lead.id, self.key).json()['deal']
        self.assertNotIn('expected_revenue', deal)
        self.assertNotIn('site_contact_mobile', deal)

    # -- notes ------------------------------------------------------------
    def test_note_is_posted_as_internal_note(self):
        response = self._post_note(self.lead.id, {'body': 'Hello <b>site</b>'})
        self.assertEqual(response.status_code, 201)
        message = self.env['mail.message'].browse(response.json()['message_id'])
        self.assertEqual(message.model, 'crm.lead')
        self.assertEqual(message.res_id, self.lead.id)
        self.assertEqual(message.author_id, self.env.ref('wordpress_deal_api.partner_wordpress_api'))
        self.assertIn('&lt;b&gt;', message.body)  # HTML escaped
        self.assertTrue(message.subtype_id.internal)

    def test_note_validation(self):
        self.assertEqual(self._post_note(self.lead.id, {'body': '  '}).status_code, 400)
        self.assertEqual(self._post_note(self.lead.id, {}).status_code, 400)
        self.assertEqual(self._post_note(999999999, {'body': 'x'}).status_code, 404)

    def test_note_idempotent_with_external_ref(self):
        first = self._post_note(self.lead.id, {'body': 'once', 'external_ref': 'wp-1'})
        second = self._post_note(self.lead.id, {'body': 'once', 'external_ref': 'wp-1'})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()['duplicate'])
        self.assertEqual(first.json()['message_id'], second.json()['message_id'])

    # -- attachments ------------------------------------------------------
    def test_pdf_is_attached(self):
        response = self._post_pdf(self.lead.id, data={'note': 'Signed quote'})
        self.assertEqual(response.status_code, 201)
        attachment = self.env['ir.attachment'].browse(response.json()['attachment_id'])
        self.assertEqual(attachment.res_model, 'crm.lead')
        self.assertEqual(attachment.res_id, self.lead.id)
        self.assertEqual(attachment.name, 'quote.pdf')

    def test_non_pdf_rejected(self):
        self.assertEqual(self._post_pdf(self.lead.id, filename='x.exe').status_code, 400)
        self.assertEqual(
            self._post_pdf(self.lead.id, filename='fake.pdf', content=b'not a pdf').status_code, 400)

    def test_missing_file_rejected(self):
        response = self.url_open(
            '/api/wp/v1/deals/%s/attachments' % self.lead.id,
            data={'note': 'no file'},
            headers=self._headers(self.key),
        )
        self.assertEqual(response.status_code, 400)

    def test_path_in_filename_is_stripped(self):
        response = self._post_pdf(self.lead.id, filename='..\\..\\evil.pdf')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['filename'], 'evil.pdf')

    # -- audit log --------------------------------------------------------
    def test_calls_are_logged_with_the_key(self):
        Log = self.env['wordpress.api.log']
        before = Log.search_count([])
        self._get('/api/wp/v1/deals/%s' % self.lead.id, self.key)
        self._get('/api/wp/v1/deals/999999999', self.key)
        self._get('/api/wp/v1/deals', 'wpk_bad')
        logs = Log.search([], limit=3)
        self.assertEqual(Log.search_count([]), before + 3)
        self.assertEqual(sorted(logs.mapped('status')), [200, 401, 404])
        ok = logs.filtered(lambda r: r.status == 200)
        self.assertEqual(ok.key_id, self.key_rec)
        self.assertEqual(ok.key_name, 'test key')
        self.assertFalse(logs.filtered(lambda r: r.status == 401).key_id)

    # -- nothing else is exposed ------------------------------------------
    def test_write_methods_not_available(self):
        for method in ('PUT', 'DELETE', 'PATCH'):
            response = self.opener.request(
                method, self.base_url() + '/api/wp/v1/deals/%s' % self.lead.id,
                headers=self._headers(self.key))
            self.assertIn(response.status_code, (404, 405))
