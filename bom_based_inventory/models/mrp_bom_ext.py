from odoo import _, fields, models, api
from odoo.exceptions import ValidationError


class MrpBomExt(models.Model):
    _inherit = 'mrp.bom'

    bom_cost = fields.Float('BOM Cost', compute='_compute_bom_cost', store=True)

    @api.depends('bom_line_ids.product_id.standard_price', 'bom_line_ids.product_qty')
    def _compute_bom_cost(self):
        for rec in self:
            total_cost = 0.0
            for line in rec.bom_line_ids:
                if line.product_id:
                    total_cost += line.product_id.standard_price * line.product_qty
            rec.bom_cost = total_cost

    @api.model_create_multi
    def create(self, vals_list):
        res = super(MrpBomExt, self).create(vals_list)
        for bom in res:
            if bom.product_tmpl_id:
                bom.product_tmpl_id.button_bom_cost()
        return res

    def write(self, vals):
        result = super(MrpBomExt, self).write(vals)
        for bom in self:
            if bom.product_tmpl_id:
                bom.product_tmpl_id.button_bom_cost()
        return result

class MrpBomLineExt(models.Model):
    _inherit = 'mrp.bom.line'

    currency_id = fields.Many2one(
        'res.currency', compute='_compute_currency_id',
    )
    component_unit_cost = fields.Monetary(
        string='Component Unit Cost', currency_field='currency_id',
        compute='_compute_costs', store=True,
    )
    total_cost_per_line = fields.Monetary(
        string='Total Cost', currency_field='currency_id',
        compute='_compute_costs', store=True,
    )

    @api.depends('company_id')
    @api.depends_context('company')
    def _compute_currency_id(self):
        for line in self:
            line.currency_id = (line.company_id or self.env.company).currency_id


    @api.constrains('product_id', 'bom_id')
    def _check_duplicate_component_product(self):
        for rec in self.filtered(lambda l: l.product_id):
            duplicate = self.search([
                ('product_id', '=', rec.product_id.id),
                ('bom_id', '=', rec.bom_id.id),
                ('id', '!=', rec.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    f"Product '{rec.product_id.display_name}' is already added as a component "
                    f"in BOM '{rec.bom_id.display_name}'."
                )

    @api.depends('product_id', 'product_id.standard_price', 'product_qty', 'company_id')
    def _compute_costs(self):
        for line in self:
            product = line.product_id.with_company(line.company_id or self.env.company)
            line.component_unit_cost = product.standard_price
            line.total_cost_per_line = product.standard_price * line.product_qty