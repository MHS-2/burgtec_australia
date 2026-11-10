from odoo import models, fields, api

class ProjectProjectExt(models.Model):
    _inherit = 'project.project'

    project_reference = fields.Char()
    delivery_installation_cost = fields.Monetary()


    # OVERRIDING DEFAULT CREATE METHOD
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['project_reference'] = self.env['ir.sequence'].next_by_code('project.reference')

        res = super(ProjectProjectExt, self).create(vals_list)
        return res
