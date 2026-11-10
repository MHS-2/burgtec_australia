from odoo import models, fields,api, _

class BomComponentState(models.Model):
    _name= "bom.component.state"
    _description = "Replacing Global Dict"

    component_state = fields.Json(string='Component state', default=lambda self: {})
    order_id = fields.Many2one('sale.order')
    bom_component_id = fields.Many2one(related='order_id.bom_component_id',store=True)
