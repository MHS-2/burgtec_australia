from odoo import models, fields, api,_
from odoo.exceptions import UserError

class SimpleQuoteDraft(models.Model):
    _name='simple.quote.draft'
    _description = "Stores Simple Quote Entry Wizard, as draft to be used later."

    user_id = fields.Many2one('res.users')
    data = fields.Json()
    lines_data = fields.Json()

    @api.constrains('user_id')
    def _check_user(self):
        for record in self:
            same_user_drafts = record.search_count([
                ('user_id','=',record.env.user.id)
            ])
            if same_user_drafts > 1:
                raise UserError(_('You already have a draft saved. You can only have one draft at a time.'))