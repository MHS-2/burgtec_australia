from odoo import fields, models, _
from odoo.exceptions import ValidationError



class PurchaseOrderExt(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        res = super(PurchaseOrderExt,self).button_confirm()
        for po in self:
            if po.tag == 'parent':
                so = po._get_sale_orders()[:1]
                if not so:
                    continue
                so = so[0]
                if not so.location:
                    raise ValidationError(_('Please select a location on delivery stage.'))

                return self.env.ref(
                    'burgtec_delivery_report.action_burgtec_delivery_report'
                ).report_action(so)


