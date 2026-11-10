from odoo import fields, models, api


class SaleOrderBOMComponentLineExt(models.Model):
    _inherit = 'sale.order.bom.component.line'

    is_early_procurement_supplier = fields.Boolean(
        related='supplier_id.is_early_procurement_supplier',
        string='Is Early Procurement Supplier',
        store=True,
        copy=False,
    )



