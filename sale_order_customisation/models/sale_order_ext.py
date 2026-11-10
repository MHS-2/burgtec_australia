from odoo import models, fields, api, _, Command

class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    defected_line_ids = fields.Many2many('sale.order.line')

    def defected_lines(self):
        for record in self:
            if record.defected_line_ids:
                return ['|',('line_group_id_value', 'in', record.defected_line_ids.ids),('id','in',record.defected_line_ids.ids)]
            else:
                return []
        
    defected_order_line_ids = fields.One2many(
        comodel_name='sale.order.line',
        inverse_name='order_id',
        string="Defected Order Lines",
        domain=lambda self: self.defected_lines(),
        auto_join=True)


    def _compute_display_name(self):
        for record in self:
            if record.env.context.get('group_swap'):
                record.display_name = f'{record.name} - {record.burgtec_quote_reference}'
            else:
                return super(SaleOrderExt,self)._compute_display_name()
    

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        record_list=[]
        if not args:
            args = []
        if name:
            # Search by the full name or part of the name
            name_parts = name.split()
            domain = ['|','|',('name', operator, name), ('burgtec_quote_reference',operator, name), ('name', operator, ' '.join(name_parts))]
            quotes = self.sudo().search(domain + args, limit=limit)
            for record in quotes:
                record_list.append((record.id,record.display_name))
            return record_list
        return super(SaleOrderExt, self).name_search(name, args, operator, limit)
    
    # Called by action button to show a wizard
    def action_show_wizard_to_add_group(self):
        # Don't include res_id key for wizards.
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': 'Perform Add Group Action',
            'view_id': self.env.ref('sale_order_customisation.sale_order_line_wizard_add_group_form_view').id,
            'view_mode': 'form',
            'res_model': 'sale.order.line.wizard',
            'context': {
                'dialog_size': 'extra-large',
            }
        }
    
    def action_add_defect_group(self):
        order_lines = self.order_line.sorted(lambda o: o.sequence)
        sequence = False
        vals = {}
        if not order_lines:
            vals.update(
                {
                    'order_id': self.id,
                    'name': 'Defect Group',
                    'display_type': 'line_section',
                    'is_defect_group_line':True,
                }
            )
        if order_lines:
            sequence = order_lines[-1].sequence
            sequence+=1
            vals.update(
                {
                    'order_id': self.id,
                    'name': 'Defect Group',
                    'display_type': 'line_section',
                    'sequence': sequence,
                    'is_defect_group_line':True,
                }
            )

        default_group_res = self.env['sale.order.line'].sudo().create(vals)

        self.order_line = [Command.link(default_group_res.id)]
        self.defected_line_ids = [Command.link(default_group_res.id)]

    
    

                


    
