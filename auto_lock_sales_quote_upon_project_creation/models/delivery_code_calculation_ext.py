from odoo import fields, models, api, _


class DeliveryCodeCalculationExt(models.Model):
    _inherit = 'delivery.code.calculation'

    auto_lock_sales_quote_upon_project_creation = fields.Boolean(
        string='Is Freeze Sale Quotation Due to Project Creation',
        related='order_id.is_frozen_due_to_project_creation', store=True,
        copy=False)
