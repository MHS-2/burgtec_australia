from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError, AccessError


class SaleOrderBOMComponentExt(models.Model):
    _inherit = 'sale.order.bom.component'

    auto_lock_sales_quote_upon_project_creation = fields.Boolean(
        string='Is Freeze Sale Quotation Due to Project Creation',
        related='order_id.is_frozen_due_to_project_creation', store=True,
        copy=False)

    def action_quoted_cost(self):
        if self.order_id.is_frozen_due_to_project_creation:
            return None
        return super(SaleOrderBOMComponentExt, self).action_quoted_cost()

    def action_fetch_pre_project_cost(self):
        if self.order_id.is_frozen_due_to_project_creation:
            return None
        return super(SaleOrderBOMComponentExt, self).action_fetch_pre_project_cost()

    def sync_component_cost(self):
        if self.order_id.is_frozen_due_to_project_creation:
            return None
        return super(SaleOrderBOMComponentExt, self).sync_component_cost()


class SaleOrderBOMComponentLineExt(models.Model):
    _inherit = 'sale.order.bom.component.line'

    def action_open_add_components_wizard(self):
        if self.component_id.order_id.is_frozen_due_to_project_creation:
            return None
        return super(SaleOrderBOMComponentLineExt, self).action_open_add_components_wizard()

    def unlink(self):
        for record in self:
            if record.component_id.order_id.is_frozen_due_to_project_creation:
                raise UserError(
                    'You cannot delete the BOM component line of the Product, if the Sale Quotation is Freeze Due to Project Creation.'
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
        if self.component_id.order_id.is_frozen_due_to_project_creation:
            return None
        return super(SaleOrderBOMComponentLineExt, self).action_open_update_parent_line()
