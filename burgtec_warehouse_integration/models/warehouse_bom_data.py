from odoo import fields, models


class WarehouseBomData(models.Model):
    _name = "warehouse.bom.data"
    _description = "Warehouse BoM Data"
    _order = "warehouse_bom_id"

    product_id = fields.Many2one("product.product", required=True, index=True, ondelete="cascade")
    warehouse_bom_id = fields.Integer(string="Warehouse BoM ID", required=True, index=True)
    name = fields.Char(required=True)
    code = fields.Char(string="Reference")
    is_kit = fields.Boolean(string="Kit")
    sequence = fields.Integer()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("product_remote_uniq", "unique(product_id, remote_id)", "Warehouse BoM already linked to this product."),
    ]