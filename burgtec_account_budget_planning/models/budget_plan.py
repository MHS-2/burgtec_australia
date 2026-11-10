from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BudgetPlan(models.Model):
    _name = "budget.plan"
    _description = "Budget Plan"
    _order = "year desc, name"

    name = fields.Char(compute='_compute_name', store=True)
    sequence = fields.Integer()
    company_id = fields.Many2one()

    year = fields.Integer(
        required=True,
        default=lambda self: fields.Date.today().year,
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed"), ("closed", "Closed")],
        default="draft"
    )
    line_ids = fields.One2many(
        "budget.plan.line",
        "plan_id",
        string="Budget Lines",
    )
    notes = fields.Text()

    total_jan = fields.Monetary(compute="_compute_month_totals", store=True)
    total_feb = fields.Monetary(compute="_compute_month_totals", store=True)
    total_mar = fields.Monetary(compute="_compute_month_totals", store=True)
    total_apr = fields.Monetary(compute="_compute_month_totals", store=True)
    total_may = fields.Monetary(compute="_compute_month_totals", store=True)
    total_jun = fields.Monetary(compute="_compute_month_totals", store=True)
    total_jul = fields.Monetary(compute="_compute_month_totals", store=True)
    total_aug = fields.Monetary(compute="_compute_month_totals", store=True)
    total_sep = fields.Monetary(compute="_compute_month_totals", store=True)
    total_oct = fields.Monetary(compute="_compute_month_totals", store=True)
    total_nov = fields.Monetary(compute="_compute_month_totals", store=True)
    total_dec = fields.Monetary(compute="_compute_month_totals", store=True)
    grand_total = fields.Monetary(compute="_compute_month_totals", store=True)

    @api.constrains('company_id', 'year')
    def _check_duplicate_budget_for_same_company_and_year(self):
        for plan in self:
            duplicate_plan = self.env["budget.plan"].search(
                [('company_id', '=', plan.company_id.id), ('year', '=', plan.year), ('id', '!=', plan.id)], limit=1)
            if duplicate_plan:
                raise ValidationError('A budget plan with same company and year already exists')

    @api.depends('year')
    def _compute_name(self):
        for plan in self:
            plan.name = "Budget Plan %s" % plan.year

    @api.depends(
        "line_ids.jan_amount",
        "line_ids.feb_amount",
        "line_ids.mar_amount",
        "line_ids.apr_amount",
        "line_ids.may_amount",
        "line_ids.jun_amount",
        "line_ids.jul_amount",
        "line_ids.aug_amount",
        "line_ids.sep_amount",
        "line_ids.oct_amount",
        "line_ids.nov_amount",
        "line_ids.dec_amount",
    )
    def _compute_month_totals(self):
        months = [
            "jan", "feb", "mar", "apr", "may", "jun",
            "jul", "aug", "sep", "oct", "nov", "dec",
        ]
        for plan in self:
            grand = 0.0
            for month in months:
                amount = sum(plan.line_ids.mapped("%s_amount" % month))
                plan["total_%s" % month] = amount
                grand += amount
            plan.grand_total = grand

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})
