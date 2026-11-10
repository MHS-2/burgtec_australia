from odoo import api, fields, models, _, Command
from odoo.api import ValuesType
import logging

logger = logging.getLogger(__name__)


class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    sale_quote_planning_screen_id = fields.Many2one(
        'sale.quote.planning.screen',
        string='Sale Quote Planning Screen',
        copy=False
    )

    def mark_empty_line_status_planing_screen_line_with_unscheduled(self):
        sale_orders_with_planning_screen = self.env['sale.order'].search([('planning_screen_id', '!=', False)])
        count = 0
        for so in sale_orders_with_planning_screen:
            lines_to_update = so.planning_screen_id.line_ids.filtered(lambda l: not l.line_item_status)
            if lines_to_update:
                lines_to_update.write({'line_item_status': 'unschedule'})
                count += len(lines_to_update)
        logger.info(f"Updated {count} planning screen lines to 'unschedule'")

    def action_show_sale_quote_planning_screen(self):
        self.ensure_one()
        return {
            'name': _('Sale Quote Planning Screen'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.quote.planning.screen',
            'res_id': self.sale_quote_planning_screen_id.id or False,
            'view_id': self.env.ref('sale_quote_planning_screen.sale_quote_planning_screen_view_form').id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'active_id': self.id}
        }

    def create_sale_planning_screen_lines(self):
        for rec in self:
            lines = []
            item = 0
            for sol in rec.order_line:
                if not sol.display_type:
                    item += 1
                    vals = {
                        'display_type': sol.display_type or False,
                        'product_id': sol.product_template_id.id if sol.product_id else False,
                        'quantity': sol.product_uom_qty if sol.product_uom_qty else 0,
                        'order_line_id': sol.id,
                        'code': sol.line_section_name,
                        'item': item,
                        'lead_time': sol.product_template_id.quotation_lead_time,
                        'line_group_name': sol.line_group_name,
                        'line_section_name': sol.line_section_name,
                        'line_group_id_value': int(sol.line_group_id_value),
                        'line_section_id_value': int(sol.line_section_id_value),

                    }
                    lines.append((0, 0, vals))
            res = self.env['sale.quote.planning.screen'].create({
                'order_id': rec.id,
                'stage_count': 0,
                'sale_quote_line_ids': lines,
            })
            rec.sale_quote_planning_screen_id = res.id


class SaleOrderLineExt(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(SaleOrderLineExt, self).create(vals_list)
        for sol in res:
            if not sol.display_type and sol.order_id.sale_quote_planning_screen_id:
                vals = {
                    'item': len(sol.order_id.sale_quote_planning_screen_id.sale_quote_line_ids) + 1,
                    'display_type': sol.display_type or False,
                    'product_id': sol.product_template_id.id if sol.product_id else False,
                    'quantity': sol.product_uom_qty if sol.product_template_id else 0,
                    'order_line_id': sol.id,
                    'line_group_name': sol.line_group_name,
                    'line_section_name': sol.line_section_name,
                    'line_group_id_value': int(sol.line_group_id_value),
                    'line_section_id_value': int(sol.line_section_id_value),
                    'line_item_status': 'unschedule',
                }
                sol.order_id.sale_quote_planning_screen_id.sale_quote_line_ids = [Command.create(vals)]
        return res
