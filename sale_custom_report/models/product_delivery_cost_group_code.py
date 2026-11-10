from odoo import models, fields, api, _

class ProductDeliveryCostGroupCode(models.Model):
    _name= 'product.delivery.cost.group.code'
    _description = 'Product Delivery Code'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'delivery_code'

    delivery_code = fields.Char(tracking=True)
    cbm_flatpacked = fields.Float(string="CBM Flatpacked", digits='Volume')
    cbm_assembled = fields.Float(string="CBM Assembled", digits='Volume')
    company_id = fields.Many2one('res.company', store=True, copy=False,
                                string="Company",
                                default=lambda self: self.env.user.company_id.id)

    currency_id = fields.Many2one('res.currency', string="Currency",
                                 related='company_id.currency_id',)
    

    description = fields.Text()

    # Zone 1 Fields
    delivery_code_cost = fields.Monetary(tracking=True)
    installation_cost = fields.Monetary(tracking=True)
    zone1_website_minimum = fields.Float(tracking=True)
    zone1_website_sale_price = fields.Monetary(tracking=True)

    # Zone 2 Fields
    zone2_delivery_cost = fields.Monetary(tracking=True)
    zone2_installation_cost = fields.Monetary(tracking=True)
    zone2_website_minimum = fields.Float(tracking=True)
    zone2_website_sale_price = fields.Monetary(tracking=True)


    # Zone 3 Fields
    zone3_delivery_cost = fields.Monetary(tracking=True)
    zone3_installation_cost = fields.Monetary(tracking=True)
    zone3_website_minimum = fields.Float(tracking=True)
    zone3_website_sale_price = fields.Monetary(tracking=True)

