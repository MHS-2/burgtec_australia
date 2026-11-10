from odoo import models, fields, api, _



class NscrRegister(models.Model):
    _name = 'nscr.register'
    _description = 'NSCR Register'

    name = fields.Char('Name',  default=lambda self: _('New'), copy=False, readonly=True)
    order_id = fields.Many2one('sale.order')
    order_line_id = fields.Many2one('sale.order.line')
    bom_component_id = fields.Many2one('sale.order.bom.component')
    bom_component_line_id = fields.Many2one('sale.order.bom.component.line')
    nscr_date = fields.Datetime(string='NSCR Date')
    product_variant_id = fields.Many2one('product.product')
    product_component_id = fields.Many2one('product.product')
    user_id = fields.Many2one('res.users', string="Requested By")
    nscr_description = fields.Char(string="Description")
    nscr_attachments_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string='Attachments'
    )


    @api.model_create_multi
    def create(self, vals_list):
        """ Create a sequence for the nscr.register model """
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = (self.env['ir.sequence'].
                next_by_code('nscr.register'))
        res = super().create(vals_list)
        if res.bom_component_line_id:
            res.bom_component_line_id.nscr_register_id = res.id
        return res
