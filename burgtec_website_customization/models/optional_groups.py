from odoo import models,fields,api,_

class OptionalGroups(models.Model):
    _name='optional.groups'
    _description = "Optional Groups for products to be passed on website API."

    name= fields.Char(string="Group Name")
    website_name = fields.Char(string="Website Display Name")
    is_publish = fields.Boolean(string="Publish On Website")
    product_ids = fields.Many2many('product.product',domain=[('product_bom_type', '!=', 'components')])


class OptionalGroupsLine(models.Model):
    _name='optional.groups.line'
    _description="Will be used to assign optional groups on product templates"

    name = fields.Char(string="Name")
    product_template_id = fields.Many2one('product.template')
    product_product_id = fields.Many2one('product.product')
    optional_group_id = fields.Many2one('optional.groups')
    website_name = fields.Char(string="Website Display Name", compute="_compute_website_name", store=True)
    is_publish = fields.Boolean(string="Publish On Website", compute="_compute_is_publish", store=True)
    product_ids = fields.Many2many('product.product', compute="_compute_product_ids", store=True)

    @api.depends('optional_group_id','optional_group_id.website_name')
    def _compute_website_name(self):
        for record in self:
            optional_groups_obj = record.optional_group_id
            if optional_groups_obj:
                website_name = optional_groups_obj.website_name
                if website_name:
                    record.website_name = website_name
                else:
                    record.website_name = False
            else:
                record.website_name = False
    
    @api.depends('optional_group_id','optional_group_id.is_publish')
    def _compute_is_publish(self):
        for record in self:
            optional_groups_obj = record.optional_group_id
            if optional_groups_obj:
                is_publish = optional_groups_obj.is_publish
                if is_publish:
                    record.is_publish = is_publish
                else:
                    record.is_publish = False
            else:
                record.is_publish = False
    
    @api.depends('optional_group_id','optional_group_id.product_ids')
    def _compute_product_ids(self):
        for record in self:
            optional_groups_obj = record.optional_group_id
            if optional_groups_obj:
                products = optional_groups_obj.product_ids
                if products:
                    record.product_ids = products
                else:
                    record.product_ids = False
            else:
                record.product_ids = False

    @api.model_create_multi
    def create(self, vals_list):
        optional_lines = False
        count= 1
        res = super(OptionalGroupsLine, self).create(vals_list)
        if res.product_template_id:
            optional_lines = self.sudo().search([('product_template_id','=',res.product_template_id.id)])
        if res.product_product_id:
            optional_lines = self.sudo().search([('product_product_id','=',res.product_product_id.id)])
        if optional_lines:
            for line in optional_lines:
                line.name = f'Display {count}'
                count+=1
        return res

    

