from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError, AccessError


class SaleOrderBOMComponentExt(models.Model):
    _inherit = 'sale.order.bom.component'

    quote_type = fields.Selection(related="order_id.quote_type", store=True)
    is_old_data = fields.Boolean(related="order_id.is_old_data", store=True)

    def action_quoted_cost(self):
        if self.order_id.quote_type == 'delivery_stage':
            return None
        return super().action_quoted_cost()

    def action_fetch_pre_project_cost(self):
        if self.order_id.quote_type == 'delivery_stage':
            return None
        return super().action_fetch_pre_project_cost()


class SaleOrderBOMComponentLineExt(models.Model):
    _inherit = 'sale.order.bom.component.line'

    is_product_fully_approved = fields.Boolean(
        string='Is Product Fully Approved ?',
        default=False,
        copy=False,
        help="Sale order Line becomes readonly when Product  is fully approved on Planning screen")

    def action_open_add_components_wizard(self):
        if self.component_id.order_id.quote_type == 'delivery_stage':
            return None
        if self.is_product_fully_approved:
            return None
        return super().action_open_add_components_wizard()

    def unlink(self):
        for record in self:
            if record.is_product_fully_approved:
                raise UserError(
                    'You cannot delete the BOM component line of the Product, if the Product is in fully approved state in Planning Screen'
                )
            if not record._context.get('force_delete') and record.is_parent:
                raise UserError(
                    'You can’t delete the Parent Product line directly. Deleting the associated sale order line will automatically remove the BOM line.'
                )
            if not record._context.get('force_delete') and record.display_type:
                raise UserError(
                    'You can’t delete the Display name line of Parent product. Deleting the associated sale order line will automatically remove this line.'
                )

        return super(SaleOrderBOMComponentLineExt, self).unlink()

    def action_open_update_parent_line(self):
        if self.component_id.order_id.quote_type == 'delivery_stage':
            return None
        if self.is_product_fully_approved:
            return None
        return super().action_open_update_parent_line()
