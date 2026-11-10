from odoo import fields, models, _
from odoo.osv import expression


class CrmLeadExt(models.Model):
    _inherit = 'crm.lead'

    source_simple_quote_id = fields.Many2one('sale.order')

    def action_view_simple_sale_quote(self):
        self.ensure_one()
        return {
            'name': _('Simple Sale Quote'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.source_simple_quote_id.id,
            'context': {"simple_quote":1},
            'view_id': self.env.ref('burgtec_simple_quote.simple_quote_view_sale_order_form_new').id,

        }
    
    def action_view_sale_quotation(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale_custom_report.action_quotations_with_sale_quote_type")
        action['context'] = self._prepare_opportunity_quotation_context()
        action['context']['search_default_draft'] = 1
        action['context']['simple_quote'] = 0
        action['domain'] = expression.AND(
            [[('opportunity_id', '=', self.id)], self._get_action_view_sale_quotes_domain()])
        quotations = self.order_ids.filtered_domain(self._get_action_view_sale_quotes_domain())
        if len(quotations) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = quotations.id
        return action

    def action_view_project_quotation(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale_custom_report.action_quotations_with_project_quote_type")
        action['context'] = self._prepare_opportunity_quotation_context()
        action['context']['simple_quote'] = 0
        action['domain'] = expression.AND(
            [[('opportunity_id', '=', self.id)], self._get_action_view_project_quotation_domain()])
        quotations = self.order_ids.filtered_domain(self._get_action_view_project_quotation_domain())
        if len(quotations) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = quotations.id
        return action

    def action_view_delivery_stages(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale_custom_report.action_quotations_with_delivery_stage_quote_type")
        action['context'] = self._prepare_opportunity_quotation_context()
        action['context']['simple_quote'] = 0
        action['domain'] = expression.AND(
            [[('opportunity_id', '=', self.id)], self._get_action_view_delivery_stage_domain()])
        quotations = self.order_ids.filtered_domain(self._get_action_view_delivery_stage_domain())
        if len(quotations) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = quotations.id
        return action