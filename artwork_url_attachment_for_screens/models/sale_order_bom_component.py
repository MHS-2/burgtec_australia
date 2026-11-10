from odoo import api, fields, models

class SaleOrderBomComponentLineExt(models.Model):
    _inherit = 'sale.order.bom.component.line'

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
                'default_bom_line_id': self.id,
            }
        }
    def open_record_in_new_window(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.artwork_image_url,
            'target': 'new'
        }
