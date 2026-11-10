from odoo import api, fields, models

class SaleQuotePlanningScreenExt(models.Model):
    _inherit = 'sale.quote.planning.screen'


class SaleQuotePlanningScreenLineExt(models.Model):
    _inherit = "sale.quote.planning.screen.line"

    artwork_image_url = fields.Char(
        string="Artwork Image URL"
    )

    attachment_id = fields.Many2one('ir.attachment', string="Attachment"
    )

    def action_open_add_attachment_artwork_wizard(self):
        return {
            'name': 'Add Artwork',
            'type': 'ir.actions.act_window',
            'res_model': 'attachment.artwork.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'dialog_size': 'medium',
                'default_sale_quote_planning_screen_line_id': self.id,
            }
        }

    def open_record_in_new_window(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.artwork_image_url,
            'target': 'new'
        }