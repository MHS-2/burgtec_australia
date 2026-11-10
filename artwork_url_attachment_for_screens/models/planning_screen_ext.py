from odoo import api, fields, models


class PlanningScreen(models.Model):
    _inherit = 'planning.screen'


class PlanningScreenLineExt(models.Model):
    _inherit = 'planning.screen.line'

    artwork_image_url = fields.Char(
        string="Artwork Image URL", related='sale_quote_planning_screen_line_id.artwork_image_url', store=True)

    attachment_id = fields.Many2one(related='sale_quote_planning_screen_line_id.attachment_id', store=True)

    def action_open_add_attachment_artwork_wizard(self):
        return {
            'name': 'Add Artwork',
            'type': 'ir.actions.act_window',
            'res_model': 'attachment.artwork.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'dialog_size': 'medium',
                'default_planning_screen_line_id': self.id,
            }
        }

    def open_record_in_new_window(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.artwork_image_url,
            'target': 'new'
        }
