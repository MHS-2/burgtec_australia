# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from pytz import timezone, UTC

_logger = logging.getLogger(__name__)


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def set_mail_sent_date(self, res_ids):
        purchase_order = self.env['purchase.order'].sudo()
        purchase_order_obj = purchase_order.browse(res_ids)
        user_tz = False
        local_dt = False
        today = fields.Datetime.now()
        user_tz = timezone(self.env.user.tz or 'UTC')
        local_dt = UTC.localize(today).astimezone(user_tz)
        if purchase_order_obj:
            purchase_order_obj.write({
                'po_sent_date': local_dt
            })
    
    def _action_send_mail(self, auto_commit=False):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed.

        :return tuple: (
            result_mails_su: in mass mode, sent emails (as sudo),
            result_messages: in comment mode, posted messages
        )
        """
        result_mails_su, result_messages = self.env['mail.mail'].sudo(), self.env['mail.message']

        for wizard in self:
            if wizard.res_domain:
                search_domain = wizard._evaluate_res_domain()
                res_ids = self.env[wizard.model].search(search_domain).ids
            else:
                res_ids = wizard._evaluate_res_ids()
            # in comment mode: raise here as anyway message_post will raise.
            if not res_ids and wizard.composition_mode == 'comment':
                raise ValueError(
                    _('Mail composer in comment mode should run on at least one record. No records found (model %(model_name)s).',
                      model_name=wizard.model)
                )

            if wizard.composition_mode == 'mass_mail':
                result_mails_su += wizard._action_send_mail_mass_mail(res_ids, auto_commit=auto_commit)
            else:
                result_messages += wizard._action_send_mail_comment(res_ids)
            
            if wizard._context.get('active_model') == 'purchase.order':
                wizard.set_mail_sent_date(res_ids)

        return result_mails_su, result_messages
    

