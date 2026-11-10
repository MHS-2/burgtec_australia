# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_simple_quote = fields.Boolean()

    product_sale_type = fields.Selection([
                ('burgtec','Burgtec'),
                ('dpg','DPG'),
        ], compute="compute_product_sale_type",store=True, precompute=True)
    
    is_pricelist_group = fields.Boolean(compute="compute_is_pricelist_group")

    series_sequence = fields.Integer(related='series_sequence_id.sequence',store=True)

    nz_pricelist_ids = fields.Many2many(related='series_sequence_id.pricelist_ids')

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('is_simple_quote_copy'):
            return super(SaleOrder, self).create(vals_list)
        if not self.env.context.get('simple_quote'):
            return super(SaleOrder, self).create(vals_list)
        if self.env.context.get('simple_quote'):
            for vals in vals_list:
                vals['is_simple_quote'] = True
        res = super(SaleOrder, self).create(vals_list)
        # As Simple Quotes now being created directly we need to create their oppoetunities as well
        for record in res:
            lead_vals = {
                'partner_id': record.partner_id.id,
                'series_sequence_id': record.series_sequence_id.id,
                'project_name': record.project_name,
                'location': record.location,
                'source_simple_quote_id': record.id,
                'type':'opportunity',
            }
            lead_res = self.env['crm.lead'].sudo().create(lead_vals)
            lead_res.action_generate_deal_number()
            lead_res.import_deal_from_hubspot()
            record.opportunity_id = lead_res.id
            record.new_sale_order_number = lead_res.odoo_deal_number_6digit
            record.origin = 'Simple Quote',

            # Create Its BOM Component For quick and simple logic. 
            bom = self.env['sale.order.bom.component'].sudo().create({
                'order_id': record.id,
            })

            # attach it
            record.bom_component_id = bom.id
        return res

    def action_show_component(self):
        self.ensure_one()
        bom_component = self.bom_component_id
        return {
            'name': _('BOM Components'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.bom.component',
            'res_id': bom_component.id or False,
            'view_mode': 'form',
            'view_id': self.env.ref('bom_based_inventory.view_sale_order_bom_components_form').id,
            'target': 'current',
            'context': {
                'active_model': 'sale.order',
                'active_id': self.id,
                'default_order_id': self.id,
                'bom_id': bom_component.id or False,
            }
        }

    def copy(self, default=None):
        default = dict(default or {})
        # so that all complex quotes upon duplicate can als show under the simple quotes menu
        default['is_simple_quote'] = True
        series = self.opportunity_id.series_sequence_id
        if series:
            default['series_sequence_id'] = series.id
        res = super(SaleOrder, self.with_context(is_simple_quote_copy=True)).copy(default)
        return res

    def action_original_sales_view(self):
        self.ensure_one()
        return {
            'name': _('Sales Quote'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.id,
        }
    
    @api.depends('opportunity_id','series_sequence_id')
    def compute_product_sale_type(self):
        for record in self:
            if not record.opportunity_id:
                if not record.series_sequence_id:
                    record.product_sale_type = False
                    continue
                if record.series_sequence_id.sequence == 9:
                    record.product_sale_type = 'dpg'
                    continue
                if record.series_sequence_id.sequence != 9:
                    record.product_sale_type = 'burgtec'
                    continue
            series = record.opportunity_id.series_sequence_id.sequence
            if not series == 9:
                record.product_sale_type = 'burgtec'
            if series == 9:
                record.product_sale_type = 'dpg'
    
    @api.depends('partner_id', 'company_id','product_sale_type','series_sequence_id')
    def _compute_pricelist_id(self):
        for record in self:
            price_list = False
            series_sequence = record.series_sequence_id
            series_sequence_pricelists = series_sequence.pricelist_ids
            if series_sequence.sequence == 1:
                if series_sequence_pricelists:
                    record.pricelist_id = series_sequence_pricelists[-1]
                    continue
                else:
                    record.pricelist_id = False
                    continue
            if not record.product_sale_type:
                if not record.partner_id:
                    record.pricelist_id = False
                    continue
                record = record.with_company(record.company_id)
                record.pricelist_id = record.partner_id.property_product_pricelist
            if record.product_sale_type:
                price_list = self.env['product.pricelist'].sudo().search([
                    ('pricelist_type', '=', record.product_sale_type),
                    ('is_preferred','=',True),
                ])
                if price_list:
                    record.pricelist_id = price_list[0].id
                else:
                    if not record.partner_id:
                        record.pricelist_id = False
                        continue
                    record = record.with_company(record.company_id)
                    record.pricelist_id = record.partner_id.property_product_pricelist
    
    def compute_is_pricelist_group(self):
        has_group = self.env.user.has_group('product.group_product_pricelist')
        for record in self:
            record.is_pricelist_group = has_group
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        has_group = self.env.user.has_group('product.group_product_pricelist')
        res['is_pricelist_group'] = has_group
        return res
    
    def unlink_empty_lines(self):
        for record in self:
            quote_planning_screen = record.sale_quote_planning_screen_id
            ps_lines = False
            empty_ps_lines = False
            if quote_planning_screen:
                ps_lines = quote_planning_screen.sale_quote_line_ids
                empty_ps_lines = ps_lines.filtered(lambda l:not l.product_id)
                empty_ps_lines.unlink()
                


                


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Called by action button to show a wizard
    def action_show_wizard_to_add_code(self):
        # Don't include res_id key for wizards.
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': 'Perform Add Code Action',
            'view_id': self.env.ref('sale_order_customisation.sale_order_line_wizard_add_code_form_view').id,
            'view_mode': 'form',
            'res_model': 'sale.order.line.wizard',
            'context': {
                'dialog_size': 'extra-large',
            }
        }
