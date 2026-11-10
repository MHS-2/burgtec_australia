from odoo import http, fields, _
from odoo.http import request
import hmac
import hashlib
import base64
import logging
import json
import requests


_logger = logging.getLogger(__name__)

class XeroWebhookController(http.Controller):

    @http.route('/xero/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def xero_webhook(self, **kwargs):
        try:
            params = request.env['ir.config_parameter'].sudo()
            webhook_key = params.get_param('xero_customization.xero_webhook_key')
            xero_account = request.env['xero.account'].sudo().search([])
            xero = xero_account.xero_auth()
            # ✅ MUST be raw bytes
            raw_body = request.httprequest.get_data()

            xero_signature = request.httprequest.headers.get('x-xero-signature')

            # Generate signature
            hashed = hmac.new(
                webhook_key.encode('utf-8'),
                raw_body,
                hashlib.sha256
            ).digest()

            computed_signature = base64.b64encode(hashed).decode()

            _logger.info("RAW BODY: %s", raw_body)
            _logger.info("Computed: %s", computed_signature)
            _logger.info("Xero: %s", xero_signature)

            # ✅ SAFE compare
            if hmac.compare_digest(computed_signature, xero_signature):
                json_data = json.loads(raw_body.decode('utf-8'))
                if not json_data.get('events'):
                    # IMPORTANT → return EMPTY 200
                    return request.make_response('', status=200)
                result = request.env['xero.webhook.queue'].sudo().create({
                    'datetime': fields.Datetime.now(),
                    'payload': json_data
                })
                if result:
                    _logger.info("Xero Webhook Queue Created.: %s", result)
                    return request.make_response('', status=200)
            else:
                _logger.warning("Invalid signature")
                return request.make_response('', status=401)
        except Exception:
            _logger.exception("Webhook error")
            return request.make_response('', status=500)
    