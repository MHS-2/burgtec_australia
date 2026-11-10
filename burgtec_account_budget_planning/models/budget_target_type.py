from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class BudgetTargetType(models.Model):
    _name = "budget.target.type"
    _description = "Budget Target Type"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    description = fields.Text()

    @api.constrains('name')
    def _check_target_type_unique(self):
        for record in self:
            if record.name:
                name = record.name.strip().lower()

                existing = self.search([
                    ('id', '!=', record.id),
                    ('name', 'ilike', name)
                ])
                if any(rec.name.strip().lower() == name for rec in existing):
                    raise ValidationError(_("Target Type must be unique."))
