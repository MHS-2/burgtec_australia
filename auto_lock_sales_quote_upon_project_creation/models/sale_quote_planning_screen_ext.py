from odoo import fields, models, api, _, Command


class SalesQuotePlanningScreenExt(models.Model):
    _inherit = 'sale.quote.planning.screen'

    project_name = fields.Char(related="order_id.project_name", store=True)

    auto_lock_sales_quote_upon_project_creation = fields.Boolean(
        string='Is Freeze Sale Quotation Due to Project Creation',
        related='order_id.is_frozen_due_to_project_creation', store=True)

    line_item_status_ids = fields.One2many('line.item.status', 'sale_quote_planning_screen_id',
                                           compute="_compute_line_item_status_quantity", store=True)

    @api.depends('sale_quote_line_ids', 'sale_quote_line_ids.line_item_status')
    def _compute_line_item_status_quantity(self):
        values_dict = {
            "sales_sales_court": "Sales-Sales Court",
            "sales_customer_court": "Sales-Customer Court",
            "technical_initial_check": "Technical-Initial Check",
            "technical_final_check": "Technical-Final Check",
            "technical_purchasing": "Technical-Purchasing",
            "projects_awaiting_delivery": "Projects-Awaiting Delivery",
            "projects_delivered": "Projects-Delivered",
            "projects_installed": "Projects-Installed",
            "unschedule": "Unschedule",
        }
        for rec in self:
            status_quantity_dict = {}
            lines = rec.sale_quote_line_ids
            for line in lines:
                status = line.line_item_status
                status_quantity_dict[status] = status_quantity_dict.get(status, 0) + 1
            commands = [(5, 0, 0)]
            for status, qty in status_quantity_dict.items():
                if status:
                    commands.append(Command.create({
                        'status_name': values_dict[status],
                        'status_quantity': qty,
                    }))
            rec.line_item_status_ids = commands

