from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class DuplicateQuotationLineWizardExt(models.TransientModel):
    """ This model represents duplicate.quotation.line.wizard."""
    _inherit = 'duplicate.quotation.line.wizard'

    def action_duplicate(self):
        if (self.order_id.is_frozen_due_to_project_creation):
            raise ValidationError(_(
                "The Targeted Sale order is frozen.You cannot duplication a line in it."
            ))
        return super().action_duplicate()
