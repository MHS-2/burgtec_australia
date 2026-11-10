import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class SaleOrderBOMComponentExt(models.Model):
    _inherit = 'sale.order.bom.component'

    skip_nscr_entry = fields.Boolean('Skip NSCR')


class SaleOrderBomComponentLine(models.Model):
    _inherit = 'sale.order.bom.component.line'

    is_icr_register = fields.Boolean(string="ICR", compute="_compute_is_icr_register", store=True, readonly=False)
    icr_register_id = fields.Many2one('icr.register')
    nscr_register_id = fields.Many2one('nscr.register')

    is_old_line = fields.Boolean(help="Marking Component Lines as old before Registers features")

    def _set_icr_register(self):
        for record in self:
            vals = {}
            # New Logic To Cancel ICR Register Entry.
            if record.icr_register_id and record.is_icr_register == False:
                record.icr_register_id.state = 'cancel'
            if record.icr_register_id and record.is_icr_register == True:
                record.icr_register_id.state = 'in_progress'
            if not record.icr_register_id and record.is_icr_register == True:
                vals = {'icr_date': fields.Datetime.now(),
                        'bom_component_id': record.component_id.id,
                        'bom_component_line_id': record.id,
                        'order_id': record.component_id.order_id.id,
                        'burgtec_project_reference': record.component_id.order_id.burgtec_quote_reference,
                        'order_line_id': record.order_line_id.id,
                        'product_variant_id': record.order_line_id.product_id.id,
                        'product_component_id': record.product_id.id if not record.is_parent else False,
                        'user_id': self.env.user.id
                        }
                res = record.env['icr.register'].with_context({"burgtec_project_reference": True}).create(vals)
                if res:
                    record.icr_register_id = res.id
                    # Assigning ICR to product or component as well
                    if not res.product_component_id and res.product_variant_id:
                        res.product_variant_id.icr_register_id = res.id
                        res.product_variant_id.is_indent = True
                    if res.product_component_id:
                        res.product_component_id.icr_register_id = res.id
                        res.product_component_id.is_indent = True

    def action_open_nscr_creation_choice_wizard(self):
        """Opens the NSCR creation choice wizard first"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'nscr.creation.choice',
            'view_id': self.env.ref(
                'burgtec_registers_customization.view_nscr_creation_choice_wizard_form').id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'dialog_size': 'extra-large',
                'default_bom_component_line_id': self.id,
            }
        }

    def write(self, vals):
        res = super(SaleOrderBomComponentLine, self).write(vals)
        if vals.get('is_icr_register') == True:
            self._set_icr_register()
        if vals.get('is_icr_register') == False:
            self._set_icr_register()
        return res


    @api.depends('product_id', 'product_id.is_indent')
    def _compute_is_icr_register(self):
        for record in self:
            if record.product_id:
                # Check if ICR Register record exists
                if not record.icr_register_id and record.product_id.is_indent and not record.is_old_line:
                    vals = {'icr_date': fields.Datetime.now(),
                            'bom_component_id': record.component_id.id,
                            'bom_component_line_id': record.id,
                            'order_id': record.component_id.order_id.id,
                            'burgtec_project_reference': record.component_id.order_id.burgtec_quote_reference,
                            'order_line_id': record.order_line_id.id,
                            'product_variant_id': record.order_line_id.product_id.id,
                            'product_component_id': record.product_id.id if not record.is_parent else False,
                            'user_id': self.env.user.id
                            }
                    res = record.env['icr.register'].with_context({"burgtec_project_reference": True}).create(vals)
                    if res:
                        record.icr_register_id = res.id
                        record.product_id.icr_register_ids = [(4, res.id)]
                        record.is_icr_register = record.product_id.is_indent

                if record.icr_register_id and not record.product_id.is_indent:
                    record.icr_register_id.state = 'cancel'
                    record.is_icr_register = record.product_id.is_indent

                if record.icr_register_id and record.product_id.is_indent:
                    record.icr_register_id.state = 'in_progress'
                    record.is_icr_register = record.product_id.is_indent
            else:
                record.is_icr_register = False
