import datetime
import logging
import time
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
from odoo.tools import (
    date_utils,
    float_compare,
    float_is_zero,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    is_html_empty,
    sql
)
from odoo.tools.mail import (
    email_re,
    email_split,
    )
from markupsafe import Markup

_logger = logging.getLogger(__name__)

class AccountMoveExt(models.Model):
    _inherit = 'account.move'

    is_xero_contact = fields.Boolean(related="partner_id.is_xero_contact", store=True)

    is_export_xero_contact = fields.Boolean(related="partner_id.is_export_contact", store=True)

    is_export_move = fields.Boolean(default=False,readonly=True)

    is_chart_account_issue = fields.Boolean(default=False)

    def export_invoice(self, invoice_list, xero, last_export_date, xero_account_id, company=False, disable_export=False):
        xero_account = self.env['xero.account'].search([('company_id', '=', company)], limit=1)
        if self._context.get('invoice_ids'):
            invoice_ids = self._context.get('invoice_ids')
        else:
            if last_export_date:
                invoice_ids = self.search([('company_id', '=', company),
                                           ('able_to_xero_export', '=', True),
                                           ('move_type', 'in', ['out_invoice', 'in_invoice']),
                                           '|', ('state', '!=', 'cancel'),
                                           ('xero_invoice_number', '!=', False),
                                           '|', ('write_date', '>=', last_export_date),
                                           ('create_date', '>=', last_export_date)])
            else:
                invoice_ids = self.search([('company_id', '=', company),
                                           ('able_to_xero_export', '=', True),
                                           ('move_type', 'in', ['out_invoice', 'in_invoice']),
                                           '|', ('state', '!=', 'cancel'),
                                           ('xero_invoice_number', '!=', False)])
        update_invoice_data = []
        update_invoice_data_list = []
        create_invoice_data = []
        create_invoice_data_list = []
        count = 0
        c = 0
        request = 0
        mismatch_log = self.env['mismatch.log']
        for invoice_id in invoice_ids:
            if invoice_id.move_type == 'out_invoice':
                type = u'ACCREC'
            elif invoice_id.move_type == 'in_invoice':
                type = u'ACCPAY'
            if not invoice_id.partner_id:
                description = 'Customer must be set for export (Odoo to Xero)'
                mismatch_log.create({'name': invoice_id.name,
                                     'source_model': 'account.move',
                                     'source_id': invoice_id.id,
                                     'description': description,
                                     'date': datetime.datetime.now(),
                                     'option': 'export',
                                     'xero_account_id': xero_account_id
                                     })
                continue

            if invoice_id.xero_invoice_id:
                for xero_inv in invoice_list:
                    if xero_inv.get('InvoiceID') == invoice_id.xero_invoice_id and xero_inv.get('Status') in ['DRAFT','SUBMITTED'] :
                        invoice_currency_rate = 0.0
                        status = u'DRAFT'
                        if invoice_id.state == 'draft':
                            status = u'DRAFT'
                        elif invoice_id.state == 'cancel':
                            status = u'DELETED'
                        elif invoice_id.state == 'posted':
                            status = u'AUTHORISED'
                            if invoice_id.currency_id.id != invoice_id.company_id.currency_id.id:
                                if invoice_id.move_type == 'out_invoice':
                                    if not invoice_id.line_ids[0].amount_currency == 0.0 and not invoice_id.line_ids[0].debit == 0.0:
                                        invoice_currency_rate = abs(invoice_id.line_ids[0].amount_currency / invoice_id.line_ids[0].debit)
                                else:
                                    if not invoice_id.line_ids[0].amount_currency == 0.0 and not invoice_id.line_ids[0].credit == 0.0:
                                        invoice_currency_rate = abs(invoice_id.line_ids[0].amount_currency / invoice_id.line_ids[0].credit)

                        line_amount_type = invoice_id.line_amount_type

                        partner_details = {}
                        if invoice_id.partner_id.parent_id:
                            contact = invoice_id.partner_id.parent_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                            if not contact.xero_contact_id:
                                xero_account.export_contact_overwrite() if xero_account.contact_overwrite else xero_account.export_contact()
                                contact = invoice_id.partner_id.parent_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                            partner_details = {u'ContactID': contact.xero_contact_id}
                        else:
                            contact = invoice_id.partner_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                            if not contact.xero_contact_id:
                                xero_account.export_contact_overwrite() if xero_account.contact_overwrite else xero_account.export_contact()
                                contact = invoice_id.partner_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                            partner_details = {u'ContactID': contact.xero_contact_id}
                        invoice_data = {u'Type': type,
                                        u'InvoiceID': invoice_id.xero_invoice_id,
                                        u'Status': status,
                                        u'LineAmountTypes': line_amount_type,
                                        u'Contact': partner_details,
                                        u'Date': invoice_id.invoice_date or fields.Date.today(),
                                        u'DueDate': invoice_id.invoice_date_due or fields.Date.today(),
                                        u'CurrencyCode': invoice_id.currency_id.name,
                                        }
                        if invoice_id.move_type == 'out_invoice':
                            invoice_data.update({u'Reference': invoice_id.burgtec_invoice_reference if invoice_id.burgtec_invoice_reference else str(invoice_id.id) or u''})

                        elif invoice_id.move_type == 'in_invoice':
                            invoice_data.update({u'InvoiceNumber': invoice_id.burgtec_bill_reference_computed if invoice_id.burgtec_bill_reference_computed else str(invoice_id.id) or u''})
                        if invoice_currency_rate:
                            invoice_data.update({u'CurrencyRate': invoice_currency_rate})
                        line_items = []
                        for inv_line in invoice_id.invoice_line_ids.filtered(lambda p: p.product_id or (p.name and p.account_id)):
                            if inv_line.product_id:
                                product = inv_line.product_id.product_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                                if product and not product[0].xero_item_id:
                                    xero_account.export_product()
                            if inv_line.tax_ids:
                                tax_type = inv_line.tax_ids[0]
                            else:
                                if invoice_id.move_type == 'out_invoice':
                                    tax_type = self.env['account.tax'].search([('type_tax_use', '=', 'sale'), ('amount', '=', 0), ('company_id', '=', company)], limit=1)
                                    if not tax_type:
                                        company_id = self.env['res.company'].browse(company)
                                        raise UserError(_('Please create account tax of type \'SALE\' and amount = 0.0 for Company: %s')% (company_id.name))
                                else:
                                    tax_type = self.env['account.tax'].search([('type_tax_use', '=', 'purchase'), ('amount', '=', 0), ('company_id', '=', company)], limit=1)
                                    if not tax_type:
                                        company_id = self.env['res.company'].browse(company)
                                        raise UserError(_('Please create account tax of type \'PURCHASE\' and amount = 0.0 for Company: %s')%(company_id.name))
                            if not tax_type.xero_tax_type:
                                tax_rates = xero.taxrates.all()
                                self.env['account.tax'].export_tax(tax_rates, xero, xero_account_id, company=company, disable_export=disable_export)
                            if inv_line.xero_invoice_line_id:
                                vals = {u'LineItemID': inv_line.xero_invoice_line_id,
                                        u'AccountCode': inv_line.account_id.code,
                                        u'Description': inv_line.name or inv_line.product_id.name,
                                        u'UnitAmount': -(inv_line.price_unit) if inv_line.quantity < 0 else inv_line.price_unit,
                                        u'TaxType': u'' if inv_line.move_id.line_amount_type == 'NoTax' else  tax_type and tax_type.xero_tax_type or u'',
                                        u'ValidationErrors': [],
                                        u'Quantity': abs(inv_line.quantity) if inv_line.quantity < 0 else inv_line.quantity,
                                        }
                            else:
                                vals = {u'AccountCode': inv_line.account_id.code,
                                        u'Description': inv_line.name or inv_line.product_id.name,
                                        u'UnitAmount': -(inv_line.price_unit) if inv_line.quantity < 0 else inv_line.price_unit,
                                        u'TaxType': u'' if inv_line.move_id.line_amount_type == 'NoTax' else  tax_type and tax_type.xero_tax_type or u'',
                                        u'ValidationErrors': [],
                                        u'Quantity': abs(inv_line.quantity) if inv_line.quantity < 0 else inv_line.quantity,
                                        }
                            if invoice_id.move_type == 'out_invoice':
                                vals.update({u'DiscountRate': inv_line.discount or 0.0})

                            if inv_line.product_id:
                                vals.update({u'ItemCode': inv_line.product_id.default_code or 'XeroTest'})
                            line_items.append(vals)
                        if line_items:
                            invoice_data.update({u'LineItems': line_items})
                        # invoice in draft state individual request
                        if invoice_id.state == 'draft':
                            request += 1
                            if request > 30:
                                time.sleep(1)
                            inv_rec = xero.invoices.save(invoice_data)
                            if inv_rec[0].get('ValidationErrors'):
                                description = inv_rec[0].get('ValidationErrors')[0].get('Message')
                                mismatch_log.create({'name': inv_rec[0].get('InvoiceNumber') or inv_rec[0].get('Reference'),
                                                     'source_model': 'account.move',
                                                     'source_id': invoice_id.id,
                                                     'description': description,
                                                     'date': fields.Datetime.now(),
                                                     'option': 'export',
                                                     'xero_account_id': xero_account_id})
                                continue
                            if inv_rec[0].get('LineItems'):
                                for lines in inv_rec[0].get('LineItems'):
                                    inv_line = invoice_id.invoice_line_ids.filtered(lambda l: not l.xero_invoice_line_id
                                        and (l.product_id.default_code or 'XeroTest') == lines.get('ItemCode')
                                        and l.price_unit == lines.get('UnitAmount')
                                        and l.quantity == lines.get('Quantity'))
                                    if inv_line:
                                        inv_line[0].xero_invoice_line_id = lines.get('LineItemID')
                                        inv_line[0].move_id = invoice_id.id

                            self._cr.commit()
                        else:
                            update_invoice_data.append(invoice_data)
                            count += 1
                            if count == 50:
                                update_invoice_data_list.append(update_invoice_data)
                                update_invoice_data = []
                                count = 0

            elif not invoice_id.xero_invoice_id and invoice_id.state != 'cancel':
                if invoice_id.state == 'posted':
                    # set state of invoice 'paid' not possible at a time.
                    status = u'AUTHORISED'
                else:
                    status = u'DRAFT'

                invoice_currency_rate = 0.0
                if invoice_id.state == 'posted' and invoice_id.currency_id.id != invoice_id.company_id.currency_id.id:
                    if invoice_id.move_type == 'out_invoice':
                        if not invoice_id.line_ids[0].amount_currency == 0.0 and not invoice_id.line_ids[0].debit == 0.0:
                            invoice_currency_rate = abs(invoice_id.line_ids[0].amount_currency / invoice_id.line_ids[0].debit)
                    else:
                        if not invoice_id.line_ids[0].amount_currency == 0.0 and not invoice_id.line_ids[0].credit == 0.0:
                            invoice_currency_rate = abs(invoice_id.line_ids[0].amount_currency / invoice_id.line_ids[0].credit)

                line_amount_type = invoice_id.line_amount_type

                partner_details = {}
                if invoice_id.partner_id.parent_id:
                    contact = invoice_id.partner_id.parent_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                    if not contact.xero_contact_id:
                        xero_account.export_contact_overwrite() if xero_account.contact_overwrite else xero_account.export_contact()
                        contact = invoice_id.partner_id.parent_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                    partner_details = {u'ContactID': contact.xero_contact_id}
                else:
                    contact = invoice_id.partner_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                    if not contact.xero_contact_id:
                        xero_account.export_contact_overwrite() if xero_account.contact_overwrite else xero_account.export_contact()
                        contact = invoice_id.partner_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                    partner_details = {u'ContactID': contact.xero_contact_id}
                final_invoice_data = {u'Type': type,
                                      u'Contact': partner_details,
                                      u'Date': invoice_id.invoice_date or fields.Date.today(),
                                      u'DueDate': invoice_id.invoice_date_due or fields.Date.today(),
                                      u'Status': status,
                                      u'LineAmountTypes': line_amount_type,
                                      u'CurrencyCode': invoice_id.currency_id.name,
                                      }
                if invoice_id.move_type == 'out_invoice':
                    final_invoice_data.update({u'Reference': invoice_id.burgtec_invoice_reference if invoice_id.burgtec_invoice_reference else str(invoice_id.id) or u''})
                elif invoice_id.move_type == 'in_invoice':
                    final_invoice_data.update({u'InvoiceNumber': invoice_id.burgtec_bill_reference_computed if invoice_id.burgtec_bill_reference_computed else str(invoice_id.id) or u''})

                if invoice_currency_rate:
                    final_invoice_data.update({u'CurrencyRate': invoice_currency_rate})
                if invoice_id.invoice_line_ids:
                    line_items = []
                    for invoice_line in invoice_id.invoice_line_ids.filtered(lambda p: p.product_id or (p.name and p.account_id)):
                        if invoice_line.product_id:
                            product = invoice_line.product_id.product_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                            if product and not product[0].xero_item_id:
                                xero_account.export_product()
                        if invoice_line.tax_ids:
                            tax_type = invoice_line.tax_ids[0]
                        else:
                            if invoice_id.move_type == 'out_invoice':
                                tax_type = self.env['account.tax'].search([('type_tax_use', '=', 'sale'), ('amount', '=', 0), ('company_id', '=', company)], limit=1)
                                if not tax_type:
                                    company_id = self.env['res.company'].browse(company)
                                    raise UserError(_('Please create account tax of type \'SALE\' and amount = 0.0 for Company: %s')% (company_id.name))
                            else:
                                tax_type = self.env['account.tax'].search([('type_tax_use', '=', 'purchase'), ('amount', '=', 0), ('company_id', '=', company)], limit=1)
                                if not tax_type:
                                    company_id = self.env['res.company'].browse(company)
                                    raise UserError(_('Please create account tax of type \'PURCHASE\' and amount = 0.0 for Company: %s')%(company_id.name))
                        if not tax_type.xero_tax_type:
                            tax_rates = xero.taxrates.all()
                            self.env['account.tax'].export_tax(tax_rates, xero, xero_account_id, company=company, disable_export=disable_export)
                        vals = {u'AccountCode': invoice_line.account_id.code,
                                u'Description': invoice_line.name or invoice_line.product_id.name,
                                u'UnitAmount': -(invoice_line.price_unit) if invoice_line.quantity < 0 else invoice_line.price_unit,
                                u'TaxType': u'' if invoice_line.move_id.line_amount_type == 'NoTax' else  tax_type and tax_type.xero_tax_type or u'',
                                u'ValidationErrors': [],
                                u'Quantity': abs(invoice_line.quantity) if invoice_line.quantity < 0 else invoice_line.quantity,
                            }
                        if invoice_id.move_type == 'out_invoice':
                            vals.update({u'DiscountRate': invoice_line.discount or 0.0})

                        if invoice_line.product_id:
                            vals.update({u'ItemCode': invoice_line.product_id.default_code or 'XeroTest'})
                        line_items.append(vals)
                    if line_items:
                        final_invoice_data.update({u'LineItems': line_items})

                    # invoice request batch process
                create_invoice_data.append(final_invoice_data)
                c += 1
                if c == 50:
                    create_invoice_data_list.append(create_invoice_data)
                    create_invoice_data = []
                    c = 0

        if create_invoice_data:
            create_invoice_data_list.append(create_invoice_data)

        for data in create_invoice_data_list:
            inv_rec = xero.invoices.put(data)
            for inv in inv_rec:
                if inv.get('ValidationErrors'):
                    description = inv.get('ValidationErrors')[0].get('Message')
                    mismatch_log.create({'name': inv.get('InvoiceNumber') or inv.get('Reference'),
                                         'source_model': 'account.move',
                                         'description': description,
                                         'date': fields.Datetime.now(),
                                         'option': 'export',
                                         'xero_account_id': xero_account_id})
                    continue
                if inv.get('Type') == 'ACCREC':
                    try:
                        invoice_id = int(inv.get('Reference'))
                        invoice_id = self.browse(invoice_id)
                    except Exception as e:
                        invoice_id = self.search([('burgtec_invoice_reference', '=', inv.get('Reference')), ('company_id', '=', company), ('move_type', '=', 'out_invoice')],limit=1)
                    # invoice_id = self.search([('name', '=', inv.get('Reference')), ('company_id', '=', company), ('move_type', '=', 'out_invoice')],limit=1)
                else:
                    try:
                        invoice_id = int(inv.get('InvoiceNumber'))
                        invoice_id = self.browse(invoice_id)
                    except Exception as e:
                        invoice_id = self.search([('burgtec_bill_reference_computed', '=', inv.get('InvoiceNumber')), ('company_id', '=', company), ('move_type', '=', 'in_invoice')],limit=1)
                    # invoice_id = self.search([('name', '=', inv.get('InvoiceNumber')), ('company_id', '=', company), ('move_type', '=', 'in_invoice')],limit=1)
                if inv.get('LineItems'):
                    for lines in inv.get('LineItems'):
                        inv_line = invoice_id.invoice_line_ids.filtered(lambda l: not l.xero_invoice_line_id
                            and (l.product_id.default_code or 'XeroTest') == lines.get('ItemCode')
                            and l.price_unit == lines.get('UnitAmount')
                            and l.quantity == lines.get('Quantity'))
                        if inv_line:
                            inv_line[0].xero_invoice_line_id = lines.get('LineItemID')
                            inv_line[0].move_id = invoice_id[0].id

                invoice_id.write({'xero_invoice_id': inv.get('InvoiceID'), 'xero_invoice_number': inv.get('InvoiceNumber'), 'is_export_move':True})
                invoice_id.message_post(body=_('Exported Successfully'), message_type='comment', subtype_xmlid='mail.mt_comment')
                self._cr.commit()

        if update_invoice_data:
            update_invoice_data_list.append(update_invoice_data)

        for data in update_invoice_data_list:
            inv_rec = xero.invoices.save(data)
            for inv in inv_rec:
                if inv.get('ValidationErrors'):
                    description = inv.get('ValidationErrors')[0].get('Message')
                    mismatch_log.create({'name': inv.get('InvoiceNumber') or inv.get('Reference'),
                                         'source_model': 'account.move',
                                         'description': description,
                                         'date': fields.Datetime.now(),
                                         'option': 'export',
                                         'xero_account_id': xero_account_id})
                    continue
                if inv.get('Type') == 'ACCREC':
                    try:
                        invoice_id = int(inv.get('Reference'))
                        invoice_id = self.browse(invoice_id)
                    except Exception as e:
                        invoice_id = self.search([('burgtec_invoice_reference', '=', inv.get('Reference')), ('company_id', '=', company), ('move_type', '=', 'out_invoice')],limit=1)
                        # invoice_id = self.search([('name', '=', inv.get('Reference')), ('move_type', '=', 'out_invoice'), ('company_id', '=', company)],limit=1)
                    # invoice_id = self.search([('name', '=', inv.get('Reference')), ('move_type', '=', 'out_invoice'), ('company_id', '=', company)],limit=1)
                else:
                    try:
                        invoice_id = int(inv.get('InvoiceNumber'))
                        invoice_id = self.browse(invoice_id)
                    except Exception as e:
                        # invoice_id = self.search([('name', '=', inv.get('InvoiceNumber')), ('move_type', '=', 'in_invoice'), ('company_id', '=', company)],limit=1)
                        invoice_id = self.search([('burgtec_bill_reference_computed', '=', inv.get('InvoiceNumber')), ('company_id', '=', company), ('move_type', '=', 'in_invoice')],limit=1)
                    # invoice_id = self.search([('name', '=', inv.get('InvoiceNumber')), ('move_type', '=', 'in_invoice'), ('company_id', '=', company)],limit=1)
                if inv.get('LineItems'):
                    for lines in inv.get('LineItems'):
                        inv_line = invoice_id.invoice_line_ids.filtered(lambda l: not l.xero_invoice_line_id
                            and (l.product_id.default_code or 'XeroTest') == lines.get('ItemCode')
                            and l.price_unit == lines.get('UnitAmount')
                            and l.quantity == lines.get('Quantity'))
                        if inv_line:
                            inv_line[0].xero_invoice_line_id = lines.get('LineItemID')
                            inv_line[0].move_id = invoice_id.id
                self._cr.commit()

    
    def pay_invoice(self, xero_account_id, xero, partner, xero_invoice, odoo_invoice, type, company=False):
        partner_pool = self.env['res.partner']
        currency_pool = self.env['res.currency']
        account_pool = self.env['account.account']
        xero_pool = self.env['xero.account']
        company_pool = self.env['res.company']
        payment_pool = self.env['account.payment']
        account_move_pool = self.env['account.move']
        move = False
        if partner and xero_invoice and odoo_invoice:
            invoice = odoo_invoice
            partner_id = partner_pool._find_accounting_partner(partner).id
            if xero_invoice.get('Payments'):
                for payment in xero_invoice.get('Payments'):
                    payment_line = payment_pool.search([('xero_payment_id', '=', payment.get('PaymentID'))])
                    currency_id = currency_pool.search([('name', '=', xero_invoice.get('CurrencyCode'))], limit=1)
                    if not currency_id:
                        currency_list = xero.currencies.all()
                        currency_pool.import_currency(currency_list, xero)
                        currency_id = currency_pool.search([('name', '=', xero_invoice.get('CurrencyCode'))], limit=1)

                    if payment.get('PaymentID'):
                        _logger.info("PaymentID %s", payment.get('PaymentID'))
                        xero_payment_id = xero.payments.get(payment.get('PaymentID'))
                        _logger.info("XERO Payment ID %s", xero_payment_id)
                        payment_account = xero_payment_id[0].get('Account')
                        _logger.info("Payment Account %s", payment_account)
                        account = account_pool.search([('code', '=', payment_account.get('Code')), ('acc_id', '=', payment_account.get('AccountID'))],limit=1)
                        _logger.info("Payment Account Code %s and Payment Account ID %s", payment_account.get('Code'), payment_account.get('AccountID'))
                        payment_invoice = xero_payment_id[0].get('Invoice')
                        if not account:
                            _logger.info('------- ACCOUNT NOT FOUND -----')
                            account_list = xero.accounts.all()
                            _logger.info("Account List Count %s",len(account_list))
                            account_pool.import_account(account_list, xero, xero_account_id, company=company, import_option='create')
                            account = account_pool.search([('code', '=', payment_account.get('Code')), ('acc_id', '=', payment_account.get('AccountID'))],limit=1)
                            # If not account still not found then it was not created due to archived or similar accounts.
                            if not account:
                                move = account_move_pool.search([('xero_invoice_id','=',payment_invoice.get('InvoiceID'))],limit=1)
                                if move:
                                    message_body = Markup(f"""
                                        <div style="background-color: #ffcdd2; border: 2px solid #c62828; border-radius: 8px; padding: 15px; margin: 10px 0;">
                                            <h4 style="color: #c62828; margin: 0 0 12px 0; font-size: 15px;">
                                                ⚠️ (Invoice Not Paid!) Chart of Account — XERO Sync Problem
                                            </h4>
                                            <table style="width: 100%; border-collapse: collapse; background-color: #fff3f3; border-radius: 5px; overflow: hidden;">
                                                <tr style="border-bottom: 1px solid #ef9a9a;">
                                                    <td style="padding: 7px 12px; font-weight: bold; color: #555; width: 40%;">Account Code</td>
                                                    <td style="padding: 7px 12px; color: #333;">{payment_account.get('Code')}</td>
                                                </tr>
                                                <tr style="border-bottom: 1px solid #ef9a9a;">
                                                    <td style="padding: 7px 12px; font-weight: bold; color: #555;">Account Name</td>
                                                    <td style="padding: 7px 12px; color: #333;">{payment_account.get('Name')}</td>
                                                </tr>
                                            </table>
                                            <p style="margin: 10px 0 0 0; font-size: 12px; color: #c62828; background-color: #ffebee; padding: 8px 10px; border-radius: 4px; border-left: 3px solid #c62828;">
                                                ℹ️ This account was <strong>not created in Odoo</strong> — it may be archived in Xero, or a chart of account with the same code already exists in Odoo.
                                            </p>
                                        </div>
                                    """)
                                    move.is_chart_account_issue = True
                                    move.message_post(
                                        body=message_body,
                                        subject='Chart Account Issue',
                                        message_type='notification',
                                        subtype_xmlid='mail.mt_note',)
                                    _logger.info('------- Chart Issue and Message Posted On %s -----',move.name)
                                    continue

                            
                        xero_account = xero_pool.browse(xero_account_id)
                        payment_journal = False
                        for journal in xero_account.journal_ids:
                            if journal.inbound_payment_method_line_ids.payment_account_id.id == account.id or journal.outbound_payment_method_line_ids.payment_account_id.id == account.id:
                                payment_journal = journal
                                break
                        if not payment_journal:
                            company_id = company_pool.browse(company)
                            raise UserError(_("Please Create or Add 'Payment Journal' for account \'%s %s\' of company \'%s\'.")% (account.code, account.name, company_id.name))

                    if not payment_line:
                        date = payment.get('Date')
                        account_payment_vals = {
                                            # 'invoice_ids': [(6, 0, odoo_invoice.ids)],
                                            'amount': payment.get('Amount'),
                                            'currency_id': currency_id and currency_id.id or False,
                                            'partner_id': partner_id,
                                            'company_id': company,
                                            'journal_id': payment_journal and payment_journal.id or False,
                                            'date': date or fields.Date.today(),
                                            'partner_type': odoo_invoice.move_type in ('out_invoice', 'out_refund') and 'customer' or 'supplier',
                                            'xero_payment_id': payment.get('PaymentID') or False,
                                            'memo': odoo_invoice[0].name
                                            }
                        if type in ['out_invoice', 'in_refund']:
                            account_payment_vals.update({'reconciled_invoice_ids': [(6, 0, odoo_invoice.ids)],
                                                        'reconciled_invoices_count': len(odoo_invoice.ids),
                                                        'payment_type':invoice.move_type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound',
                                                        'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id})
                        elif type in ['in_invoice', 'out_refund']:
                            account_payment_vals.update({'reconciled_bill_ids': [(6, 0, odoo_invoice.ids)],
                                                        'reconciled_bills_count': len(odoo_invoice.ids),
                                                        'payment_type':invoice.move_type in ('in_invoice', 'out_refund') and 'outbound' or 'inbound',
                                                        'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id})
                        account_payment = invoice.env['account.payment'].create([account_payment_vals])
                        if xero_invoice.get('CurrencyRate'):
                            account_payment.with_context({'CurrencyRate': payment.get('CurrencyRate')}).action_post()
                        else:
                            account_payment.action_post()
                        account_payment.action_validate()
                        domain = [('account_type', 'in', ('asset_receivable', 'liability_payable')),('reconciled', '=', False)]
                        # payment_lines = account_payment.line_ids.filtered_domain(domain)
                        payment_lines = account_payment.move_id.line_ids.filtered_domain(domain)
                        for line in invoice.line_ids.filtered(lambda l: l.account_type in ('asset_receivable', 'liability_payable')):
                            payment_lines |= line
                        payment_lines.filtered_domain([('reconciled', '=', False)]).reconcile()
                        self._cr.commit()
