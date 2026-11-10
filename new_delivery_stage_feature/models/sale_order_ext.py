from email.policy import default

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrderExt(models.Model):
    _inherit = "sale.order"

    planning_screen_id = fields.Many2one(
        'planning.screen',
        string='Planning Screen',
        copy=False
    )

    quote_type = fields.Selection([
        ('sales_quote', 'Sales Quote'),
        ('project_quote', 'Project Quote'),
        ('delivery_stage', 'Delivery Stage'),
    ])
    delivery_stage_reference_number = fields.Char(default=lambda self: _('New'), readonly=True, copy=False,
                                                  help="Reference Number of the new delivery stage")

    is_sales_quote = fields.Boolean(copy=False)

    is_parent_sale_order = fields.Boolean(copy=False)

    is_project_quote = fields.Boolean(copy=False)

    is_child_sale_order = fields.Boolean(copy=False)

    source_sale_order_name = fields.Char(copy=False)

    source_sale_order_id = fields.Char(copy=False)

    # Using this to store parent quotes child data!

    child_sale_order_ids = fields.Many2many('sale.order', 'parent_sale_order', 'child_sale_order', copy=False)

    reference_count = fields.Integer(copy=False, default=0)
    reference_count1 = fields.Integer(copy=False, default=1)

    child_quote_count = fields.Integer(copy=False, compute="_compute_total_child_quote", store=True)

    # def copy(self, default=None):
    #     if any(self.mapped('is_child_sale_order')):
    #         raise UserError(_('You cannot duplicate Sale Order(s) which are New Delivery Stage Project Quotes.'))
    #     return super().copy(default)
    def action_show_planning_screen(self):
        self.ensure_one()
        return {
            'name': _('Planning Screen'),
            'type': 'ir.actions.act_window',
            'res_model': 'planning.screen',
            'res_id': self.planning_screen_id.id or False,
            'view_id': self.env.ref('new_delivery_stage_feature.planning_screen_form_view').id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'active_id': self.id}
        }

    def action_confirm(self):
        if self.is_parent_sale_order:
            raise UserError(
                _("'Parent Sale Quote' cannot be Confirmed, you can only use this to create a 'New Delivery Stage'!."))

        if self.quote_type == 'sales_quote':
            raise UserError(_("'Sale Quote' cannot be Confirmed!!"))

        res = super(SaleOrderExt, self).action_confirm()
        return res

    @api.depends('child_sale_order_ids')
    def _compute_total_child_quote(self):
        for record in self:
            record.child_quote_count = len(record.child_sale_order_ids)

    def create_new_delivery_stage(self):
        for record in self:
            if record.quote_type == 'project_quote':
                raise UserError(_('You are not allowed to create Delivery Stage of Project Quotes!'))

            if not record.bom_component_id:
                raise UserError(_('Kindly set and save Bom Components before creating New Delivery Stage.'))
            # Now set few things in this quotation to make it different from all others.
            # parent quote
            child_quote = False
            updated_count = record.reference_count + 1

            sale_write_vals = {
                'is_sales_quote': True,
                'is_parent_sale_order': True,
                'quote_type': 'sales_quote',
                'reference_count': updated_count,
                'delivery_stage_reference_number': f"D{updated_count}",
                'state': 'quotation_confirmed',
            }
            res = record.write(sale_write_vals)
            child_sale_order_vals = {
                'name': f"{record.name} - {record.delivery_stage_reference_number}",
                'quote_type': 'project_quote',
                'is_project_quote': True,
                'source_sale_order_name': self.name,
                'source_sale_order_id': self.id,
                'is_child_sale_order': True,
            }
            if res:
                child_quote = record.with_context(copied_from_new_delivery_stage=True).copy()
                child_quote.update(
                    child_sale_order_vals
                )
                record.update(
                    {
                        'child_sale_order_ids': [(4, child_quote.id)],
                    }
                )
                return child_quote.id

    def action_show_child_sale_orders(self):
        self.ensure_one()
        children = self.child_sale_order_ids
        if len(children) == 1:
            return {
                'name': _('Child Quotation'),
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_model': 'sale.order',
                'res_id': children.id,
                'type': 'ir.actions.act_window',
                'context': {'create': False},
            }
        else:
            return {
                'name': _('Child Quotations'),
                'domain': [('id', 'in', children.ids)],
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],  # 👈 Add this
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'context': {'create': False},
            }

    def action_show_parent_sale_order(self):
        return {
            'name': _('Parent Sale Quotation'),
            'res_id': int(self.source_sale_order_id),
            'view_mode': 'form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'context': {'create': True},
        }

    def action_show_delivery_quote(self, value):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': value,
            'views': [[False, 'form']],
            'target': 'current',
        }


class SaleOrderLineExt(models.Model):
    _inherit = "sale.order.line"

    total_available_quantity = fields.Float(string="Total Unscheduled Quantity", compute="_compute_total_available_qty",
                                            help="Gets the qty of thi line from its Parent Sale Order Lne.")

    def _compute_total_available_qty(self):
        for rec in self:
            if rec.order_id.is_child_sale_order:
                if not rec.display_type:
                    # Need Quanitites 
                    # Origin Sale Order Line Quantity.
                    original_qty = rec.env['sale.order.line'].browse(int(rec.old_order_line)).product_uom_qty
                    other_delivery_stage_lines_quantities = 0
                    # If Previous Delivery Stages!

                    if rec.old_order_line:
                        other_delivery_stage_lines_quantities = sum(rec.env['sale.order.line'].search(
                            [
                                ('old_order_line', '=', rec.old_order_line),
                                ('state', '=', 'sale'),
                                # ('order_id','!=',rec.split_id.order_id.id)
                            ]).mapped('product_uom_qty'))

                    remaining_difference = 0

                    if original_qty and other_delivery_stage_lines_quantities:
                        remaining_difference = abs(original_qty - other_delivery_stage_lines_quantities)
                    elif original_qty and not other_delivery_stage_lines_quantities:
                        remaining_difference = abs(original_qty - other_delivery_stage_lines_quantities)
                    else:
                        remaining_difference = 0
                    rec.total_available_quantity = remaining_difference
                else:
                    rec.total_available_quantity = 0
            else:
                rec.total_available_quantity = 0


