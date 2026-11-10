from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError, AccessError


class SaleOrderBOMComponentExt(models.Model):
    _inherit = 'sale.order.bom.component'


    freeze_sale_order = fields.Boolean(string='Freeze Sale Order', related='order_id.freeze_sale_order', store=True)

    def action_quoted_cost(self):
        if self.order_id.quote_type == 'project_quote' and self.order_id.freeze_sale_order:
            return None
        return super(SaleOrderBOMComponentExt, self).action_quoted_cost()

    def action_fetch_pre_project_cost(self):
        if self.order_id.quote_type == 'project_quote' and self.order_id.freeze_sale_order:
            return None
        return super(SaleOrderBOMComponentExt, self).action_fetch_pre_project_cost()

    def sync_component_cost(self):
        if self.order_id.quote_type == 'project_quote' and self.order_id.freeze_sale_order:
            return None
        return super(SaleOrderBOMComponentExt, self).sync_component_cost()


class SaleOrderBOMComponentLineExt(models.Model):
    _inherit = 'sale.order.bom.component.line'


    def action_open_add_components_wizard(self):
        if self.component_id.order_id.quote_type == 'project_quote' and self.component_id.order_id.freeze_sale_order:
            return None
        return super(SaleOrderBOMComponentLineExt, self).action_open_add_components_wizard()

    def unlink(self):
        for record in self:
            if record.component_id.order_id.quote_type == 'project_quote' and  record.component_id.order_id.freeze_sale_order:
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
        if self.component_id.order_id.quote_type == 'project_quote' and  self.component_id.order_id.freeze_sale_order:
            return None
        return super(SaleOrderBOMComponentLineExt, self).action_open_update_parent_line()
