# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import ValidationError

MAX_VALIDITY_DAYS = 365


class WordpressApiKeyWizard(models.TransientModel):
    """Generates a key and shows it once. The key is not kept after closing."""
    _name = 'wordpress.api.key.wizard'
    _description = 'Generate WordPress API Key'
    # Transient rows are purged quickly because the plain key lives in one for a moment.
    _transient_max_hours = 0.1

    name = fields.Char(required=True, default='WordPress website')
    validity_days = fields.Integer('Valid for (days)', required=True, default=90)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft')
    key = fields.Char('API Key', readonly=True)

    def action_generate(self):
        self.ensure_one()
        if not 1 <= self.validity_days <= MAX_VALIDITY_DAYS:
            raise ValidationError('Validity must be between 1 and %s days.' % MAX_VALIDITY_DAYS)
        _record, token = self.env['wordpress.api.key']._generate(
            self.name, fields.Datetime.now() + timedelta(days=self.validity_days))
        self.write({'state': 'done', 'key': token})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_close(self):
        """Wipe the plain key, then close the dialog."""
        self.write({'key': False})
        return {'type': 'ir.actions.act_window_close'}
