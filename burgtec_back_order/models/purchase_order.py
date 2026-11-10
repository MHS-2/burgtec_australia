# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_purchase_lines_fetched_for_bo = fields.Boolean()

    @api.depends_context('burgtec_po_reference')
    def _compute_display_name(self):
        for record in self:
            if record.env.context.get('burgtec_po_reference'):
                if record.burgtec_purchase_reference:
                    record.display_name = record.burgtec_purchase_reference
                else:
                    return super()._compute_display_name()

            else:
                return super()._compute_display_name()
    
    def button_confirm(self):
        res = super().button_confirm()
        parent_po = False
        delivery_quote = False
        planning_screen = False
        if self.tag =='child':
            parent_po = self.parent_po_id
            if parent_po:
                delivery_quote = self.env['sale.order'].sudo().search([('name','=',parent_po.origin)])
                project_quote = self.env['sale.order'].sudo().browse(int(delivery_quote.source_sale_order_id))
                planning_screen = project_quote.planning_screen_id
                if planning_screen.delivery_stage_id.id == delivery_quote.id:
                    planning_screen.delivery_stage_id = False
                    planning_screen.backorder_planning_line_ids = [(5, 0, 0)]
                    planning_screen.delivery_stage_id = delivery_quote.id 
        return res
    

