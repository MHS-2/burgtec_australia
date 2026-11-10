from odoo import fields, models, api


class AccountMoveExt(models.Model):
    _inherit = 'account.move'
    burgtec_invoice_reference = fields.Char('Burgtec Invoice Reference')

    x_sale_order_ids = fields.Many2many(
        comodel_name='sale.order',
        relation='sale_order_account_move_rel',
        column1='move_id',
        column2='sale_id',
        string="Linked Sale Orders",
        copy=False,
        help="Stored link to sale orders related to this invoice (used for smart buttons)."
    )

    sale_order_count = fields.Integer(
        compute="_compute_origin_so_count",
        string='Sale Order Count',
        store=False,
        readonly=True,
    )

    @api.depends('x_sale_order_ids', 'line_ids.sale_line_ids.order_id')
    def _compute_origin_so_count(self):
        for move in self:
            if move.x_sale_order_ids:
                move.sale_order_count = len(move.x_sale_order_ids)
            else:
                move.sale_order_count = len(move.line_ids.sale_line_ids.order_id)

    def action_view_source_sale_orders(self):
        """Prefer stored x_sale_order_ids, fallback to the standard relation."""
        self.ensure_one()
        source_orders = self.mapped('x_sale_order_ids') or self.line_ids.sale_line_ids.order_id
        result = self.env['ir.actions.act_window']._for_xml_id('sale.action_orders')
        if len(source_orders) > 1:
            result['domain'] = [('id', 'in', source_orders.ids)]
        elif len(source_orders) == 1:
            result['views'] = [(self.env.ref('sale.view_order_form', False).id, 'form')]
            result['res_id'] = source_orders.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

