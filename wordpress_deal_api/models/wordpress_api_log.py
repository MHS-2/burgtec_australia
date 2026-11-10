# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class WordpressApiLog(models.Model):
    _name = 'wordpress.api.log'
    _description = 'WordPress API Call Log'
    _order = 'id desc'

    key_id = fields.Many2one('wordpress.api.key', string='API Key',
                             readonly=True, ondelete='set null', index=True)
    # Snapshot, so the log still names the key after it is deleted.
    key_name = fields.Char(readonly=True)
    endpoint = fields.Char(readonly=True, index=True)
    method = fields.Char(readonly=True)
    status = fields.Integer('HTTP Status', readonly=True)
    # Plain integer on purpose: the log must survive if a deal is later deleted.
    deal_id = fields.Integer('Deal ID', readonly=True, index=True)
    external_ref = fields.Char('External Reference', readonly=True, index=True)
    message_id = fields.Integer('Created Message ID', readonly=True)
    ip_address = fields.Char(readonly=True)
    detail = fields.Char(readonly=True)

    @api.autovacuum
    def _gc_old_logs(self):
        """Keep the audit trail for 180 days."""
        limit = fields.Datetime.now() - relativedelta(days=180)
        self.search([('create_date', '<', limit)]).unlink()
