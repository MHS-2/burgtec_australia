from odoo import models, fields, api

class ComponentExistingNscrSelection(models.TransientModel):
    _name = 'component.existing.nscr.selection'
    _description = 'Component Existing Nscr Selection'

    nscr_id = fields.Many2one('nscr.register','Existing NSCR')
    description = fields.Char(related='nscr_id.nscr_description',string='Description')
    product_component_id = fields.Many2one('product.product')
    bom_component_line_id = fields.Many2one('sale.order.bom.component.line')


    def action_assign_entry(self):
        if self.bom_component_line_id and self.nscr_id:
            self.bom_component_line_id.nscr_register_id = self.nscr_id.id


