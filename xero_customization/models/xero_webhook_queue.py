# -*- coding: utf-8 -*-
import logging
import json
import ast
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class XeroWebhookQueue(models.Model):
    _name = 'xero.webhook.queue'
    _description = 'XeroWebhookQueue'

    payload = fields.Text()
    state = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ], default='pending')
    datetime = fields.Datetime()
    xero_event_line_ids = fields.One2many('xero.event.line','xero_webhook_queue_id',compute="compute_xero_event_lines",store=True)

    @api.depends('payload')
    def compute_xero_event_lines(self):
        for record in self:
            resource_processed = []
            vals = {}
            vals_list = []
            if not record.payload:
                record.xero_event_line_ids = False
            data = ast.literal_eval(record.payload)
            record.xero_event_line_ids = [(5, 0, 0)]
            for event in data.get('events', []):
                if event.get('resourceId') not in resource_processed:
                    vals = {
                        'resource_url': event.get('resourceUrl'),
                        'resource_id': event.get('resourceId'),
                        'tenant_id': event.get('tenantId'),
                        'tenant_type': event.get('tenantType'),
                        'event_category': event.get('eventCategory'),
                        'event_type': event.get('eventType'),
                        'event_date_char': event.get('eventDateUtc'),
                    }
                    resource_processed.append(event.get('resourceId'))
                    vals_list.append((0,0,vals))
                    vals = {}
            record.xero_event_line_ids = vals_list
    
    def process_events(self):
        contact = False
        event_mapped = []
        queued_records = self.search([('state','=','pending')])
        res_partner = self.env['res.partner'].sudo()
        res_partner_category = self.env['res.partner.category'].sudo()
        account_move = self.env['account.move'].sudo()
        xero_account = self.env['xero.account'].sudo().search([])
        xero = xero_account.xero_auth()
        for record in queued_records:
            events = record.xero_event_line_ids
            if events:
                for line in events:
                    # Contacts Operations.
                    if line.event_category == 'CONTACT':
                        group_list = xero.contactgroups.all()
                        res_partner_category.import_contact_group(group_list, xero)
                        contact = xero.contacts.filter(ContactID=line.resource_id)
                        if xero_account.contact_overwrite:
                            res_partner.import_contact_overwrite(contact, xero, xero_account_id=xero_account.id, company=xero_account.company_id.id, import_option=xero_account.import_option)
                        else:
                            res_partner.import_contact(contact, xero, xero_account_id=xero_account.id, company=xero_account.company_id.id, import_option=xero_account.import_option)
                    
                    # Invoice Operations.
                    if line.event_category == 'INVOICE':
                        invoice = xero.invoices.filter(InvoiceID=line.resource_id)
                        account_move.import_invoice(xero_account.id, invoice , xero, company=xero_account.company_id.id, without_product=xero_account.inv_without_product, import_option=xero_account.import_option, customer_inv_journal_id=xero_account.customer_inv_journal_id, vendor_bill_journal_id=xero_account.vendor_bill_journal_id)
                record.write({
                    'state':'done'
                })




                            

                 

            
            

class XeroEventLine(models.Model):
    _name = 'xero.event.line'
    _description = 'Xero Event Lines'

    xero_webhook_queue_id = fields.Many2one('xero.webhook.queue', ondelete='cascade')
    resource_url = fields.Char()
    resource_id = fields.Char()
    tenant_id = fields.Char()
    tenant_type = fields.Char()
    event_category = fields.Char()
    event_type = fields.Char()
    event_date_char = fields.Char()

