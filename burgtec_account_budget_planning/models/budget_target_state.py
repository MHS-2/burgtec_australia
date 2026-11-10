from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class BudgetTargetState(models.Model):
    _name = "budget.target.state"
    _description = "Budget Target State"
    _rec_name = "code"

    state_id = fields.Many2one(
        "res.country.state",
        string="State",
        domain="[('country_id.code', '=', 'AU')]",
    )

    code = fields.Char(related="state_id.code", store=True)
    sequence = fields.Integer(default=10)

    @api.constrains('state_id')
    def _check_state_unique(self):
        for record in self:
            if record.state_id:
                existing = self.search([
                    ('state_id', '=', record.state_id.id),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing:
                    raise ValidationError("Target State must be unique.")