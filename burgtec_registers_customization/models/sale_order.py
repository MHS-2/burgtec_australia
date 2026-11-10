# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends_context('burgtec_project_reference')
    def _compute_display_name(self):
        for record in self:
            if record.env.context.get('burgtec_project_reference'):
                if record.burgtec_quote_reference:
                    record.display_name = record.burgtec_quote_reference.split("-")[0].strip()
                else:
                    return super()._compute_display_name()

            else:
                return super()._compute_display_name()

    def set_old_lines(self):
        self.ensure_one()
        component_lines = self.env['sale.order.bom.component.line'].sudo().search([])
        _logger.info('Total Component Lines %s', len(component_lines))
        component_lines.write({
            'is_old_line': True
        })


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    has_indented_components = fields.Boolean('Has Indented Lines?', compute='_compute_has_indented_components',
                                             store=True, copy=False)

    @api.depends('order_id.bom_component_id.component_line_ids.is_icr_register')
    def _compute_has_indented_components(self):
        for sale_order_line in self:
            bom_component_id = sale_order_line.order_id.bom_component_id
            bom_component_line_ids = bom_component_id.component_line_ids
            if not bom_component_line_ids:
                sale_order_line.has_indented_components = False
            if bom_component_line_ids:
                child_component_ids = bom_component_line_ids.filtered(
                    lambda line: not line.is_parent and not line.display_type and line.order_line_id.id == sale_order_line.id)
                if not child_component_ids:
                    sale_order_line.has_indented_components = False
                sale_order_line.has_indented_components = any(
                    child_component_ids.mapped("is_icr_register")
                )

