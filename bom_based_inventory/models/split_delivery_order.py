from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,AccessError

sale_state_dict = {
    'draft': 'Draft',
    'sent': 'Quotation Sent',
    'quotation_confirmed': 'Quotation Confirmed',
    'sale': 'Sales Order',
    'cancel': 'Cancelled',
}



class SplitDO(models.Model):
    _name = 'split.do'
    _description = 'Split Delivery Orders'

    order_id = fields.Many2one('sale.order', string='Sale Order', ondelete='cascade')

    state = fields.Selection(related='order_id.state',store=True)

    line_ids = fields.One2many('split.do.line', 'split_id', string="Lines")

    def web_save(self, vals, specification: dict[str, dict], next_id=None) -> list[dict]:
        
        if self:
            if self.order_id.state not in ('draft'):
                if not self.env.user.has_group("sales_team.group_sale_manager"):
                    raise AccessError(_(f"Only Sales Administrator can edit a Sale Quotation in '{sale_state_dict[self.order_id.state]}' State"))
        return super(SplitDO,self).web_save(vals, specification)

    @api.onchange('line_ids')
    def onchange_line_ids(self):
        for line in self.line_ids:
            line.available_quantity = line.quantity - (
                    line.do_stage_1 + line.do_stage_2 + line.do_stage_3 + line.do_stage_4 + line.do_stage_5
            )
            if line.available_quantity < 0:
                raise ValidationError("You cannot enter more quantities than the original quantity.")

    @api.model_create_multi
    def create(self, vals_list):
        res = super(SplitDO, self).create(vals_list)
        model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if model and active_id:
            sale_order = self.env[model].browse(active_id)
            sale_order.split_do_id = res.id
        return res

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        sale_order_id = self.env.context.get('active_id')
        if not sale_order_id:
            return res
        sale_order = self.env['sale.order'].browse(sale_order_id)

        lines = []
        for sol in sale_order.order_line:
            vals = {
                'display_type': sol.display_type or False,
                'name': sol.name if sol.display_type else False,
                'product_reference': sol.product_template_id.default_code if sol.product_template_id else False,
                'product_id': sol.product_template_id.id if sol.product_id else False,
                'quantity': sol.product_uom_qty if sol.product_template_id else 0,
                'order_line_id': sol.id,
                'origin_order_line': sol.old_order_line if sol.old_order_line else False,
                # 'line_group_name': sol.line_group_name,
                # 'line_section_name': sol.line_section_name,
                # 'line_group_id_value': sol.line_group_id_value,
                # 'line_section_id_value': sol.line_section_id_value,
            }
            lines.append((0, 0, vals))
        res.update({
            'order_id': sale_order.id,
            'line_ids': lines,
        })
        return res


class SplitDOLine(models.Model):
    _name = 'split.do.line'
    _description = 'Split DO Line'

    split_id = fields.Many2one('split.do', ondelete='cascade')
    product_reference = fields.Char('Product Reference')
    product_id = fields.Many2one('product.template', string="Product")
    # quantity = fields.Integer("Quantity")
    available_quantity = fields.Float("Unscheduled Quantity")
    do_stage_1 = fields.Integer("DO Stage")
    do_stage_2 = fields.Integer("DO Stage 2")
    do_stage_3 = fields.Integer("DO Stage 3")
    do_stage_4 = fields.Integer("DO Stage 4")
    do_stage_5 = fields.Integer("DO Stage 5")
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note"),
        ('line_group', "Group"),
    ], string="Display Type")

    name = fields.Char('Name',compute="_compute_line_name",store=True)
    order_line_id = fields.Many2one('sale.order.line', ondelete='cascade')
    origin_order_line = fields.Char(store=True) 
    sequence = fields.Integer(related='order_line_id.sequence')
    quantity = fields.Float(related="order_line_id.product_uom_qty")


    @api.depends("order_line_id.name")
    def _compute_line_name(self):
        for record in self:
            record.name = record.order_line_id.name


    @api.constrains('quantity', 'do_stage_1', 'do_stage_2', 'do_stage_3', 'do_stage_4', 'do_stage_5')
    def _check_do_stage_total(self):
        for line in self:
            total = sum([
                line.do_stage_1 or 0,
                line.do_stage_2 or 0,
                line.do_stage_3 or 0,
                line.do_stage_4 or 0,
                line.do_stage_5 or 0,
            ])
            quantity = line.quantity or 0
            if total != quantity:
                raise ValidationError(
                    f"Total of DO Stage quantities ({total}) must exactly equal the line quantity ({quantity}) "
                    f"for product '{line.product_id.name or 'Unknown'}'."
                )
