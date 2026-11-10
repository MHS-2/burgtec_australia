# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    icr_register_id = fields.Many2one('icr.register',string='ICR Register')

    icr_register_state = fields.Selection(string="ICR Register State", related="icr_register_id.state", store=True)

    is_indent = fields.Boolean(default=False)

    icr_register_ids = fields.Many2many('icr.register')

    def get_product_component_lines(self):
        for record in self:
            vals = {}
            existing_component_lines_with_icr_record = record.env['sale.order.bom.component.line'].sudo().search(['&','&','&',('product_id','=',record.id),('component_id','!=',False),('icr_register_id','!=',False),('is_old_line','=',False)])
            if existing_component_lines_with_icr_record:
                existing_component_lines_with_icr_record.icr_register_id.write({
                    'state': 'in_progress',
                })
            component_lines = record.env['sale.order.bom.component.line'].sudo().search(['&','&','&',('product_id','=',record.id),('component_id','!=',False),('icr_register_id','=',False),('is_old_line','=',False)])
            if component_lines:
                for component in component_lines:
                    # NOW CREATE ICR REGISTER RECORD FOR EACH LINE.
                    vals = {'icr_date':fields.Datetime.now(),
                            'bom_component_id': component.component_id.id,
                            'bom_component_line_id': component.id,
                            'order_id': component.component_id.order_id.id,
                            'burgtec_project_reference': component.component_id.order_id.burgtec_quote_reference,
                            'order_line_id': component.order_line_id.id,
                            'product_variant_id': component.order_line_id.product_id.id,
                            'product_component_id': component.product_id.id if not component.is_parent else False ,
                            'user_id': self.env.user.id
                    }
                    res = record.env['icr.register'].with_context({"burgtec_project_reference": True}).create(vals)
                    if res:
                        component.write({
                            'is_icr_register':True,
                            'icr_register_id':res.id,
                        })
                        record.icr_register_ids = [(4, res.id)]
        
    def _uncheck_register_bom_lines(self):
        for record in self:
            component_lines = record.env['sale.order.bom.component.line'].sudo().search(['&','&','&',('product_id','=',record.id),('component_id','!=',False),('icr_register_id','!=',False),('is_old_line','=',False)])
            if component_lines:
                component_lines.write({
                    'is_icr_register':False,
                })
                component_lines.icr_register_id.write({
                    'state':'cancel',
                })

                

    def write(self, vals):
        res = super(ProductProduct,self).write(vals)
        if vals.get('is_indent') == True:
            self.get_product_component_lines()
        if vals.get('is_indent') == False:
            self._uncheck_register_bom_lines()
        return res

