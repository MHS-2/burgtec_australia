# -*- coding: utf-8 -*-
import hashlib
import secrets
from datetime import timedelta

from odoo import api, fields, models

KEY_PREFIX = 'wpk_'
LAST_USED_GRANULARITY = timedelta(minutes=5)


def hash_token(token):
    """SHA-256 is enough here: the token is 256 bits of randomness, so there is
    nothing to brute force (unlike a human password)."""
    return hashlib.sha256(token.encode()).hexdigest()


class WordpressApiKey(models.Model):
    """Credential for the WordPress API only.

    Unlike a native Odoo API key it is not tied to an Odoo user and is not
    accepted by Odoo's standard RPC interface, so a leaked key can never read
    contacts, products or anything else outside /api/wp/v1.
    Only a hash is stored; the key itself is shown once when it is generated.
    """
    _name = 'wordpress.api.key'
    _description = 'WordPress API Key'
    _order = 'id desc'

    name = fields.Char(required=True, help='What this key is used for, e.g. "WordPress production".')
    key_hint = fields.Char('Starts With', readonly=True, copy=False)
    key_hash = fields.Char(readonly=True, copy=False, index=True)
    expiration_date = fields.Datetime(required=True)
    active = fields.Boolean(default=True, help='Untick (archive) to revoke the key immediately.')
    last_used = fields.Datetime(readonly=True, copy=False)
    state = fields.Selection(
        [('active', 'Active'), ('expired', 'Expired'), ('revoked', 'Revoked')],
        compute='_compute_state')

    _sql_constraints = [
        ('key_hash_uniq', 'unique(key_hash)', 'This key already exists.'),
    ]

    @api.depends('active', 'expiration_date')
    def _compute_state(self):
        now = fields.Datetime.now()
        for key in self:
            if not key.active:
                key.state = 'revoked'
            elif key.expiration_date and key.expiration_date <= now:
                key.state = 'expired'
            else:
                key.state = 'active'

    @api.model
    def _generate(self, name, expiration_date):
        """Create a key and return ``(record, plain_token)``.

        The plain token exists only in the return value; it is never stored.
        """
        token = KEY_PREFIX + secrets.token_urlsafe(32)
        record = self.sudo().create({
            'name': name,
            'expiration_date': expiration_date,
            'key_hash': hash_token(token),
            'key_hint': token[:8],
        })
        return record, token

    @api.model
    def _authenticate(self, token):
        """Return the matching, active, unexpired key or an empty recordset."""
        empty = self.browse()
        if not token or not token.startswith(KEY_PREFIX) or len(token) > 200:
            return empty
        now = fields.Datetime.now()
        key = self.sudo().search([
            ('key_hash', '=', hash_token(token)),
            ('expiration_date', '>', now),
        ], limit=1)
        if key and (not key.last_used or key.last_used < now - LAST_USED_GRANULARITY):
            key.last_used = now
        return key
