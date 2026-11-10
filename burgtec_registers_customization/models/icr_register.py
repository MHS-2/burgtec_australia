import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class IcrRegister(models.Model):
    _name = 'icr.register'
    _description = 'ICR Register'
    _order = 'create_date desc, id desc'

    _inherit = ['mail.thread']

    name = fields.Char('Name',  default=lambda self: _('New'), copy=False, readonly=True, tracking=True)
    order_id = fields.Many2one('sale.order')
    burgtec_project_reference = fields.Char()
    order_line_id = fields.Many2one('sale.order.line')
    bom_component_id = fields.Many2one('sale.order.bom.component')
    bom_component_line_id = fields.Many2one('sale.order.bom.component.line', ondelete='cascade')
    icr_date = fields.Datetime(string='ICR Date')
    product_variant_id = fields.Many2one('product.product')
    product_component_id = fields.Many2one('product.product')
    user_id = fields.Many2one('res.users', string="Requested By")
    state = fields.Selection([('draft','Draft'),('in_progress','In Progress'),('complete','Completed'),('cancel','Cancelled')], default='draft', tracking=True)


    @api.model_create_multi
    def create(self, vals_list):
        """ Create a sequence for the student model """
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = (self.env['ir.sequence'].
                next_by_code('icr.register'))
        return super().create(vals_list)

    
    def set_state_to_inprogress(self):
        for record in self:
            record.write({'state': 'in_progress'})
    
    def set_state_to_complete(self):
        for record in self:
            record.write({'state': 'complete'})
    

    # Called by action button to dialog with template
    def action_open_sale_order(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_quotations_with_onboarding")
        action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
        action['res_id'] = self.order_id.id
        return action


    # Called by action button to dialog with template
    def action_open_product(self):
        self.ensure_one()
        product_id = False
        if not self.product_component_id:
            product_id = self.product_variant_id
        if self.product_component_id:
            product_id = self.product_component_id
        
        action = self.env["ir.actions.actions"]._for_xml_id("product.product_normal_action_sell")
        action['views'] = [(self.env.ref('product.product_normal_form_view').id, 'form')]
        action['res_id'] = product_id.id
        return action
    

