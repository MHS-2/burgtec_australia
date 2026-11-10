from odoo import api, fields, models, Command, _
import logging

_logger = logging.getLogger(__name__)


class PlanningScreenExt(models.Model):
    _inherit = 'planning.screen'

    freeze_sale_order = fields.Boolean(string='Freeze Sale Order', related='order_id.freeze_sale_order', store=True)

    @api.model
    def fetch_do_stages(self, record_ids=None):
        records = self.browse(record_ids) if record_ids else self
        stage_data = {}

        status_fields = [f for f in self._fields if f.startswith('do_') and f.endswith('_status')]

        for record in records:
            for field in status_fields:
                value = getattr(record, field, False)
                if value:
                    stage_num = field.split('_')[1]
                    stage_field = f"do_stage_{stage_num}"
                    stage_data[stage_field] = {
                        'value': value,
                        'disabled': value in ['planned', 'confirmed'],
                        'frozen': record.freeze_sale_order,
                    }

        return stage_data



class PlanningScreenLineExt(models.Model):
    _inherit = 'planning.screen.line'

    sd_url = fields.Char('Approved SD Url')
    internal_sd_url = fields.Char('Internal SD Url')
    other_url = fields.Char('Other Url')
    has_indented_components = fields.Boolean(related='order_line_id.has_indented_components',string='Has Indented Components ?')

    def action_view_product_line(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'View Sale Order Product Line',
            'res_model': 'sale.order.line',
            'res_id': self.order_line_id.id,
            'view_id': self.env.ref(
                'hubspot_deal_stage_quote_project_lock.view_sale_order_line_from_planning_screen'
            ).id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
            }
        }


