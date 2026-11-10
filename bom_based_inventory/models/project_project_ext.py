from odoo import fields, models


class ProjectProjectExt(models.Model):
    _inherit = 'project.project'

    def action_open_bom_report_for_project(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales BOM Report',
            'res_model': 'sale.report.bom',
            'view_mode': 'list,pivot,form',
            'domain': [('project_reference', '=', self.id)],
            'context': {
                'group_by': ['project_reference'],
            }
        }
