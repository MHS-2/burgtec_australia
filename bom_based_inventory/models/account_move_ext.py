from odoo import fields, models, api


class AccountMoveExt(models.Model):
    _inherit = 'account.move'
    burgtec_bill_reference = fields.Char('Burgtec Reference')
    burgtec_bill_reference_computed = fields.Char('Burgtec Reference Computed',
                                                  compute='_compute_burgtec_bill_reference_computed', store=True)
    is_old_data = fields.Boolean('Is Old Data ?', default=False)

    @api.depends('ref', 'burgtec_bill_reference')
    def _compute_burgtec_bill_reference_computed(self):
        for rec in self:
            if rec.ref and rec.burgtec_bill_reference:
                rec.burgtec_bill_reference_computed = f"{rec.burgtec_bill_reference}-{rec.ref}"
            elif rec.burgtec_bill_reference and not rec.ref:
                rec.burgtec_bill_reference_computed = f"{rec.burgtec_bill_reference}"
            else:
                rec.burgtec_bill_reference_computed = False

    def action_mark_old_data(self):
        for order in self:
            order.write({
                'is_old_data': True
            })
