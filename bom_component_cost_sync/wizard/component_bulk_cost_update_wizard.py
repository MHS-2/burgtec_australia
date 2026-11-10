from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError


class BomComponentBulkCostUpdateWizard(models.TransientModel):
    _name = 'bom.component.bulk.cost.update.wizard'
    _description = 'Bom Component Bulk Update Wizard'

    new_manual_live_unit_cost = fields.Float('New Live Unit Cost')
    component_id = fields.Many2one('sale.order.bom.component', string='Component', readonly=True)
    wizard_line_ids = fields.One2many(
        'bom.component.bulk.cost.update.wizard.line',
        'wizard_id',
        string='Components to Add'
    )
    bom_component_lines_ids = fields.Many2many(
        'sale.order.bom.component.line',
        'bom_comp_bulk_cost_rel',
        'wizard_id',
        'component_line_id',
        string='BOM Component Lines',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        component_id = self.env.context.get('default_component_id')
        if component_id:
            res['component_id'] = component_id
        line_ids = self.env.context.get('default_bom_component_lines_ids', [])
        res['bom_component_lines_ids'] = [(6, 0, line_ids)]
        wizard_lines = []
        for line in self.env['sale.order.bom.component.line'].browse(line_ids):
            wizard_lines.append((0, 0, {
                'parent_product_name': line.parent_product_id.name,
                'product_id': line.product_id.id,
                'manual_live_unit_cost': line.manual_live_unit_cost,
                'sale_order_bom_component_line_id': line.id,
            }))

        res['wizard_line_ids'] = wizard_lines
        return res

    def action_apply_new_cost(self):
        for rec in self:
            all_initially_selected_bom_component_lines = rec.bom_component_lines_ids
            new_manual_live_unit_cost = rec.new_manual_live_unit_cost
            wizard_line_ids = rec.wizard_line_ids
            if not wizard_line_ids:
                raise UserError(_('You must have at least one component line to apply the cost'))
            if new_manual_live_unit_cost and new_manual_live_unit_cost > 0:
                for line in wizard_line_ids:
                    component_line = line.sale_order_bom_component_line_id
                    component_line.manual_live_unit_cost = new_manual_live_unit_cost
                    component_line.live_unit_cost = new_manual_live_unit_cost * component_line.product_qty
                    all_initially_selected_bom_component_lines.write({'is_component_line_selected': False})
                component_order_line_ids = wizard_line_ids.mapped('sale_order_bom_component_line_id.order_line_id')
                self.component_id.onchange_component_line_ids(component_order_line_ids)






class BOMComponentBulkCostUpdateWizardLine(models.TransientModel):
    _name = 'bom.component.bulk.cost.update.wizard.line'
    _description = 'BOM Component Bulk Cost Update Wizard Line'

    wizard_id = fields.Many2one('bom.component.bulk.cost.update.wizard', string='Wizard', required=True,
                                ondelete='cascade')

    parent_product_name = fields.Char('Parent Product Name')
    product_id = fields.Many2one(
        'product.product',
        string='Component',
        domain="[('product_tmpl_id.product_bom_type', '=', 'components')]"
    )
    manual_live_unit_cost = fields.Float('Live Unit Cost', store=True)
    sale_order_bom_component_line_id = fields.Many2one(
        'sale.order.bom.component.line')

