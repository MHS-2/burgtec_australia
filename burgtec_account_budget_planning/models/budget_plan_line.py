from odoo import api, fields, models
from odoo.exceptions import ValidationError

class BudgetPlanLine(models.Model):
    _name = "budget.plan.line"
    _description = "Budget Plan Line"
    _order = "plan_id, target_type_id"

    plan_id = fields.Many2one(
        "budget.plan",
        ondelete="cascade",
    )
    year = fields.Integer(related="plan_id.year", store=True)
    company_id = fields.Many2one(related="plan_id.company_id", store=True)
    currency_id = fields.Many2one(related="plan_id.currency_id", store=True)

    target_type_id = fields.Many2one(
        "budget.target.type",
        string="Target Type"
    )
    target_state_id = fields.Many2one(
        "budget.target.state",
        domain=[("code", "in", ('NSW','ACT','QLD','VIC','ALL'))],
        string="State"
    )

    jan_amount = fields.Monetary(string="Jan")
    feb_amount = fields.Monetary(string="Feb")
    mar_amount = fields.Monetary(string="Mar")
    apr_amount = fields.Monetary(string="Apr")
    may_amount = fields.Monetary(string="May")
    jun_amount = fields.Monetary(string="Jun")
    jul_amount = fields.Monetary(string="Jul")
    aug_amount = fields.Monetary(string="Aug")
    sep_amount = fields.Monetary(string="Sep")
    oct_amount = fields.Monetary(string="Oct")
    nov_amount = fields.Monetary(string="Nov")
    dec_amount = fields.Monetary(string="Dec")

    line_total = fields.Monetary(
        string="Line Total",
        compute="_compute_line_total",
        store=True,
    )

    @api.constrains('target_type_id', 'target_state_id', 'plan_id')
    def _check_duplicate_target_for_same_state(self):
        for line in self:
            if not line.target_type_id or not line.target_state_id:
                continue

            duplicate = self.env["budget.plan.line"].search([
                ('plan_id', '=', line.plan_id.id),
                ('target_type_id', '=', line.target_type_id.id),
                ('target_state_id', '=', line.target_state_id.id),
                ('id', '!=', line.id),
            ], limit=1)

            if duplicate:
                raise ValidationError(
                    "A Target with the same Type and State already exists in this plan."
                )


    @api.depends(
        "jan_amount", "feb_amount", "mar_amount", "apr_amount",
        "may_amount", "jun_amount", "jul_amount", "aug_amount",
        "sep_amount", "oct_amount", "nov_amount", "dec_amount",
    )
    def _compute_line_total(self):
        for line in self:
            line.line_total = (
                line.jan_amount + line.feb_amount + line.mar_amount
                + line.apr_amount + line.may_amount + line.jun_amount
                + line.jul_amount + line.aug_amount + line.sep_amount
                + line.oct_amount + line.nov_amount + line.dec_amount
            )

