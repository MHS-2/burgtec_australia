# -*- coding: utf-8 -*-
"""REST API used by the Burgtec WordPress website.

Authentication: a dedicated WordPress API key, ``Authorization: Bearer <key>``
(see ``wordpress.api.key``). It is not an Odoo user key, so Odoo's standard RPC
interface rejects it and a leaked key can only reach the routes below.

Routes are ``auth='public'`` and check the key themselves. Data access is done
with ``sudo()`` on purpose, behind a fixed whitelist of fields and three actions
(read deals, post a note, attach a PDF).
"""
import base64
import logging
import os
import re

from odoo import SUPERUSER_ID, api, http
from odoo.http import request
from odoo.tools import plaintext2html

_logger = logging.getLogger(__name__)

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 50
MAX_NOTE_LENGTH = 20000
MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_REF_LENGTH = 128


class ApiError(Exception):
    """Raised by handlers to return a clean JSON error."""

    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class WordpressDealApi(http.Controller):

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    @http.route('/api/wp/v1/deals', type='http', auth='public',
                methods=['GET'], csrf=False, save_session=False)
    def list_deals(self, **params):
        return self._handle(
            'GET /deals', lambda ctx: self._list_deals(params, ctx))

    @http.route('/api/wp/v1/deals/<int:deal_id>', type='http', auth='public',
                methods=['GET'], csrf=False, save_session=False)
    def get_deal(self, deal_id, **params):
        return self._handle(
            'GET /deals/<id>', lambda ctx: self._get_deal(deal_id, ctx))

    @http.route('/api/wp/v1/deals/<int:deal_id>/notes', type='http',
                auth='public', methods=['POST'], csrf=False,
                save_session=False)
    def add_note(self, deal_id, **params):
        return self._handle(
            'POST /deals/<id>/notes', lambda ctx: self._add_note(deal_id, ctx))

    @http.route('/api/wp/v1/deals/<int:deal_id>/attachments', type='http',
                auth='public', methods=['POST'], csrf=False,
                save_session=False)
    def add_attachment(self, deal_id, **params):
        return self._handle(
            'POST /deals/<id>/attachments',
            lambda ctx: self._add_attachment(deal_id, ctx))

    # ------------------------------------------------------------------
    # Request wrapper: key check, uniform JSON errors, audit log
    # ------------------------------------------------------------------
    def _handle(self, endpoint, func):
        ctx = {}
        headers = None
        key = request.env['wordpress.api.key']._authenticate(self._bearer_token())
        key_id, key_name = key.id, key.name
        if not key:
            status = 401
            ctx['detail'] = 'Invalid, expired or missing API key'
            payload = {'ok': False, 'error': {
                'code': 'unauthorized',
                'message': 'Invalid, expired or missing API key.'}}
            headers = [('WWW-Authenticate', 'Bearer')]
        else:
            try:
                status, payload = func(ctx)
            except ApiError as err:
                request.env.cr.rollback()
                status = err.status
                ctx['detail'] = err.message
                payload = {'ok': False,
                           'error': {'code': err.code, 'message': err.message}}
            except Exception:  # pylint: disable=broad-except
                request.env.cr.rollback()
                _logger.exception('WordPress API unexpected error on %s', endpoint)
                status = 500
                ctx['detail'] = 'Unexpected error'
                payload = {'ok': False,
                           'error': {'code': 'server_error',
                                     'message': 'Unexpected error. See the API log.'}}
        self._log(key_id, key_name, endpoint, status, ctx)
        return request.make_json_response(payload, status=status, headers=headers)

    @staticmethod
    def _bearer_token():
        match = re.match(r'^Bearer\s+(\S+)$',
                         request.httprequest.headers.get('Authorization', ''),
                         re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def _author_id():
        return request.env.ref('wordpress_deal_api.partner_wordpress_api').sudo().id

    @staticmethod
    def _log(key_id, key_name, endpoint, status, ctx):
        """Write the audit line in its own transaction so failures are kept."""
        try:
            method, _sep, path = endpoint.partition(' ')
            with request.env.registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env['wordpress.api.log'].create({
                    'key_id': key_id or False,
                    'key_name': key_name or False,
                    'method': method,
                    'endpoint': path,
                    'status': status,
                    'deal_id': ctx.get('deal_id') or 0,
                    'external_ref': ctx.get('external_ref'),
                    'message_id': ctx.get('message_id') or 0,
                    'ip_address': request.httprequest.remote_addr,
                    'detail': (ctx.get('detail') or '')[:250],
                })
        except Exception:  # pylint: disable=broad-except
            _logger.exception('WordPress API: could not write the audit log')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _int_param(value, name, default, minimum, maximum=None):
        if value in (None, ''):
            return default
        try:
            number = int(value)
        except (TypeError, ValueError):
            raise ApiError(400, 'invalid_parameter', '%s must be an integer.' % name)
        if number < minimum or (maximum is not None and number > maximum):
            raise ApiError(400, 'invalid_parameter',
                           '%s is out of range.' % name)
        return number

    @staticmethod
    def _clean_ref(value):
        if value in (None, ''):
            return None
        if not isinstance(value, str) or len(value) > MAX_REF_LENGTH:
            raise ApiError(400, 'invalid_parameter',
                           'external_ref must be text up to %s characters.' % MAX_REF_LENGTH)
        return value.strip() or None

    @staticmethod
    def _get_lead(deal_id, ctx):
        ctx['deal_id'] = deal_id
        lead = request.env['crm.lead'].sudo().search([('id', '=', deal_id)])
        if not lead:
            raise ApiError(404, 'not_found', 'Deal not found.')
        return lead

    @staticmethod
    def _previous_success(endpoint, deal_id, ref):
        """Return the earlier successful log line for the same external_ref."""
        if not ref:
            return None
        return request.env['wordpress.api.log'].sudo().search([
            ('endpoint', '=', endpoint),
            ('deal_id', '=', deal_id),
            ('external_ref', '=', ref),
            ('status', 'in', (200, 201)),
        ], limit=1, order='id desc')

    @staticmethod
    def _iso(value):
        return value.isoformat() + 'Z' if value else None

    def _serialize(self, lead):
        """Fixed whitelist. Add fields here deliberately, never dynamically."""
        return {
            'id': lead.id,
            'deal_number': lead.odoo_deal_number_6digit or None,
            'hubspot_deal_id': lead.id_of_hubspot_deal or None,
            'name': lead.name or None,
            'project_name': lead.project_name or None,
            'customer': lead.partner_id.name or None,
            'series': lead.series_sequence_id.display_name or None,
            'deal_stage': lead.deal_stage_id.name or None,
            'pipeline': lead.deal_pipeline or None,
            'deal_type': lead.deal_type_id.name or None,
            'territory': lead.deal_territory_id.name or None,
            'deal_owner': lead.deal_owner or None,
            'created_at': self._iso(lead.create_date),
            'updated_at': self._iso(lead.write_date),
        }

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def _list_deals(self, params, ctx):
        limit = self._int_param(params.get('limit'), 'limit',
                                DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE)
        offset = self._int_param(params.get('offset'), 'offset', 0, 0)
        domain = []
        query = (params.get('q') or '').strip()
        if query:
            domain += ['|', '|', '|',
                       ('odoo_deal_number_6digit', 'ilike', query),
                       ('project_name', 'ilike', query),
                       ('name', 'ilike', query),
                       ('partner_id.name', 'ilike', query)]
        deal_number = (params.get('deal_number') or '').strip()
        if deal_number:
            domain.append(('odoo_deal_number_6digit', '=', deal_number))
        hubspot_id = (params.get('hubspot_deal_id') or '').strip()
        if hubspot_id:
            domain.append(('id_of_hubspot_deal', '=', hubspot_id))

        leads_model = request.env['crm.lead'].sudo()
        total = leads_model.search_count(domain)
        leads = leads_model.search(domain, limit=limit, offset=offset, order='id desc')
        return 200, {
            'ok': True,
            'count': total,
            'limit': limit,
            'offset': offset,
            'results': [self._serialize(lead) for lead in leads],
        }

    def _get_deal(self, deal_id, ctx):
        lead = self._get_lead(deal_id, ctx)
        return 200, {'ok': True, 'deal': self._serialize(lead)}

    def _add_note(self, deal_id, ctx):
        lead = self._get_lead(deal_id, ctx)
        payload = request.httprequest.get_json(silent=True)
        if not isinstance(payload, dict):
            raise ApiError(400, 'invalid_json', 'The body must be a JSON object.')
        body = payload.get('body')
        if not isinstance(body, str) or not body.strip():
            raise ApiError(400, 'invalid_parameter', 'body is required.')
        if len(body) > MAX_NOTE_LENGTH:
            raise ApiError(400, 'invalid_parameter',
                           'body is longer than %s characters.' % MAX_NOTE_LENGTH)
        ref = self._clean_ref(payload.get('external_ref'))
        ctx['external_ref'] = ref

        previous = self._previous_success('/deals/<id>/notes', deal_id, ref)
        if previous:
            ctx['message_id'] = previous.message_id
            return 200, {'ok': True, 'duplicate': True,
                         'message_id': previous.message_id}

        message = lead.message_post(
            body=plaintext2html(body.strip()),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
            author_id=self._author_id(),
        )
        ctx['message_id'] = message.id
        return 201, {'ok': True, 'message_id': message.id}

    def _add_attachment(self, deal_id, ctx):
        lead = self._get_lead(deal_id, ctx)
        length = request.httprequest.content_length
        if length and length > MAX_FILE_SIZE + 1024 * 1024:
            raise ApiError(413, 'file_too_large',
                           'The PDF must be %s MB or smaller.' % (MAX_FILE_SIZE // 1024 // 1024))
        upload = request.httprequest.files.get('file')
        if not upload:
            raise ApiError(400, 'invalid_parameter',
                           'Send the PDF as multipart/form-data in the "file" field.')
        filename = os.path.basename((upload.filename or '').replace('\\', '/'))
        if not filename.lower().endswith('.pdf'):
            raise ApiError(400, 'invalid_file', 'Only .pdf files are accepted.')
        content = upload.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            raise ApiError(413, 'file_too_large',
                           'The PDF must be %s MB or smaller.' % (MAX_FILE_SIZE // 1024 // 1024))
        if not content.startswith(b'%PDF-'):
            raise ApiError(400, 'invalid_file', 'The file is not a valid PDF.')
        note = (request.httprequest.form.get('note') or '').strip()
        if len(note) > MAX_NOTE_LENGTH:
            raise ApiError(400, 'invalid_parameter',
                           'note is longer than %s characters.' % MAX_NOTE_LENGTH)
        ref = self._clean_ref(request.httprequest.form.get('external_ref'))
        ctx['external_ref'] = ref
        ctx['detail'] = filename

        previous = self._previous_success('/deals/<id>/attachments', deal_id, ref)
        if previous:
            ctx['message_id'] = previous.message_id
            return 200, {'ok': True, 'duplicate': True,
                         'message_id': previous.message_id}

        attachment = request.env['ir.attachment'].sudo().create({
            'name': filename,
            'datas': base64.b64encode(content),
            'mimetype': 'application/pdf',
            'res_model': 'crm.lead',
            'res_id': lead.id,
        })
        message = lead.message_post(
            body=plaintext2html(note or 'PDF received from the WordPress website: %s' % filename),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
            author_id=self._author_id(),
            attachment_ids=[attachment.id],
        )
        ctx['message_id'] = message.id
        return 201, {'ok': True, 'message_id': message.id,
                     'attachment_id': attachment.id, 'filename': filename}
