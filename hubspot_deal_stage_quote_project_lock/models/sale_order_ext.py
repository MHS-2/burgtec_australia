from odoo import api, fields, models, _
from odoo.exceptions import UserError
from markupsafe import Markup


class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    hubspot_deal_stage = fields.Char(related='opportunity_id.deal_stage_id.name', store=True,
                                     index=True, string='Hubspot Project Stage')
    freeze_sale_order = fields.Boolean(string='Freeze Sale Order', compute='_compute_freeze_sale_order', store=True,
                                       readonly=False
                                       , tracking=True)

    deal_stage_id = fields.Many2one(related='opportunity_id.deal_stage_id', string='Hubspot Stage Id',
                                            store=True, index=True)

    deal_stage_pipeline_name = fields.Char(related='opportunity_id.deal_stage_id.pipeline_name', store=True)
    deal_stage_project_freeze = fields.Boolean(related='opportunity_id.deal_stage_id.freeze_project', store=True)
    deal_close_date = fields.Datetime(related='opportunity_id.deal_close_date', store=True)
    weighted_amount = fields.Float(related='opportunity_id.weighted_amount', store=True)

    @api.depends('deal_stage_id','deal_stage_id.freeze_project')
    def _compute_freeze_sale_order(self):
        for record in self:
            if record.deal_stage_id.freeze_project:
                record.freeze_sale_order = True
            else:
                record.freeze_sale_order = False

    def _automatic_freeze_project_based_on_deal_stages(self):
        project_quotes = self.env['sale.order'].search(
            [('quote_type', '=', 'project_quote'),('freeze_sale_order', '=', False),('deal_stage_pipeline_name','=','Projects Pipeline')])
        for record in project_quotes:
            if record.deal_stage_id.freeze_project:
                record.write({'freeze_sale_order': True})

    def action_show_wizard_to_add_group(self):
        if self.quote_type == 'project_quote' and self.freeze_sale_order:
            return None
        return super().action_show_wizard_to_add_group()



class SaleOrderLineExt(models.Model):
    _inherit = 'sale.order.line'

    def action_open_copy_wizard(self):
        if self.order_id.quote_type == 'project_quote' and self.order_id.freeze_sale_order:
            return None
        return super().action_open_copy_wizard()

    def action_show_wizard_to_add_code(self):
        if self.order_id.quote_type == 'project_quote' and self.order_id.freeze_sale_order:
            return None
        return super().action_show_wizard_to_add_code()

    def action_show_wizard_to_add_product(self):
        if self.order_id.quote_type == 'project_quote' and self.order_id.freeze_sale_order:
            return None
        return super().action_show_wizard_to_add_product()

    def action_show_wizard_to_swap_groups(self):
        if self.order_id.quote_type == 'project_quote' and self.order_id.freeze_sale_order:
            return None
        return super().action_show_wizard_to_swap_groups()

    def action_show_wizard_to_swap_codes(self):
        if self.order_id.quote_type == 'project_quote' and self.order_id.freeze_sale_order:
            return None
        return super().action_show_wizard_to_swap_codes()
