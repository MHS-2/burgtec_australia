from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime
import datetime
import time


class PurchaseOrderExt(models.Model):
    _inherit = "purchase.order"

    is_xero_contact = fields.Boolean(related="partner_id.is_xero_contact", store=True)
    
    is_export_xero_contact = fields.Boolean(related="partner_id.is_export_contact", store=True)

    def export_purchase_order(self, po_list, xero, last_export_date, xero_account_id, company=False, disable_export=False):
        mismatch_log = self.env['mismatch.log']
        xero_account = self.env['xero.account'].search([('company_id', '=', company)], limit=1)
        if self._context.get('order_ids'):
            order_ids = self._context.get('order_ids')
        else:
            if last_export_date:
                order_ids = self.search([('company_id', '=', company),
                                           ('state', '!=', 'cancel'),
                                           '|', ('write_date', '>=', last_export_date),
                                           ('create_date', '>=', last_export_date)])
            else:
                order_ids = self.search([('company_id', '=', company),
                                           ('state', '!=', 'cancel')])
        update_order_data = []
        update_order_data_list = []
        create_order_data = []
        create_order_data_list = []
        count = 0
        c = 0
        request = 0
        for order_id in order_ids:
            if not order_id.partner_id:
                description = 'Customer must be set for export (Odoo to Xero)'
                mismatch_log.create({'name': order_id.name,
                                     'source_model': 'purchase.order',
                                     'source_id': order_id.id,
                                     'description': description,
                                     'date': datetime.datetime.now(),
                                     'option': 'export',
                                     'xero_account_id': xero_account_id
                                     })
                continue
            if not order_id.xero_po_id:
                if order_id.state == 'draft':
                    status = u'Draft'
                if order_id.state in ['purchase', 'done']:
                    status = u'AUTHORISED'
                if order_id.invoice_status == 'invoiced':
                    status = u'BILLED'

                if order_id.state == 'sent':
                    status = {u'SentToContact': True}
                line_amount_type = order_id.line_amount_type
                partner_details = {}
                if order_id.partner_id.parent_id:
                    contact = order_id.partner_id.parent_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                    if not contact.xero_contact_id:
                        xero_account.export_contact_overwrite() if xero_account.contact_overwrite else xero_account.export_contact()
                        contact = order_id.partner_id.parent_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                    partner_details = {u'ContactID': contact.xero_contact_id}
                else:
                    contact = order_id.partner_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                    if not contact.xero_contact_id:
                        xero_account.export_contact_overwrite() if xero_account.contact_overwrite else xero_account.export_contact()
                        contact = order_id.partner_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                    partner_details = {u'ContactID': contact.xero_contact_id}
                final_order_data = {
                                    u'Contact': partner_details,
                                    u'Date': order_id.date_approve or fields.Date.today(),
                                    u'DeliveryDate': order_id.date_planned or fields.Date.today(),
                                    u'Status': status,
                                    u'TotalTax': order_id.amount_tax if order_id.amount_tax else 0.0,
                                    u'LineAmountTypes': line_amount_type,
                                    u'CurrencyCode': order_id.currency_id.name,
                                    }
                if order_id:
                    final_order_data.update({u'Reference': order_id.burgtec_purchase_reference or u''})

                if order_id.order_line:
                    line_items = []
                    for line in order_id.order_line.filtered(lambda l: l.product_id):
                        if line.product_id:
                            product = line.product_id.product_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                            if product and not product[0].xero_item_id:
                                xero_account.export_product()

                        if line.taxes_id:
                            tax_type = line.taxes_id[0]
                        else:
                            if order_id:
                                tax_type = self.env['account.tax'].search([('type_tax_use', '=', 'purchase'), ('amount', '=', 0), ('company_id', '=', company)], limit=1)
                                if not tax_type:
                                    company_id = self.env['res.company'].browse(company)
                                    raise UserError(_('Please create account tax of type \'PURCHASE\' and amount = 0.0 for Company: %s')% (company_id.name))
                        if not tax_type.xero_tax_type:
                            tax_rates = xero.taxrates.all()
                            self.env['account.tax'].export_tax(tax_rates, xero, xero_account_id, company=company, disable_export=disable_export)
                        vals = {
                                u'Description': line.name or line.product_id.name,
                                u'UnitAmount': line.price_unit,
                                u'TaxType': u'' if line.order_id.line_amount_type == 'NoTax' else tax_type and tax_type.xero_tax_type or u'',
                                u'DiscountRate': line.discount,
                                u'ValidationErrors': [],
                                u'Quantity': line.product_qty,
                            }
                        vals.update({u'ItemCode': line.product_id.default_code})
                        line_items.append(vals)
                    if line_items:
                        final_order_data.update({u'LineItems': line_items})
                if order_id.state in ['purchase','done'] and order_id.invoice_status == 'invoiced':
                    xero_account.export_invoice()
                if order_id.state == 'draft':
                    request += 1
                    if request > 30:
                        time.sleep(1)
                    order_rec = xero.purchaseorders.put(final_order_data)
                    if order_rec and order_rec[0].get('ValidationErrors'):
                        description = order_rec[0].get('ValidationErrors')[0].get('Message')
                        mismatch_log.create({'name': order_rec[0].get('PurchaseOrderNumber') or order_rec[0].get('Reference'),
                                             'source_model': 'purchase.order',
                                             'source_id': order_id.id,
                                             'description': description,
                                             'date': fields.Datetime.now(),
                                             'option': 'export',
                                             'xero_account_id': xero_account_id})
                        continue

                    if order_rec and order_rec[0].get('LineItems'):
                        for lines in order_rec[0].get('LineItems'):
                            order_line = order_id.order_line.filtered(lambda l: not l.xero_order_line_id
                                and l.product_id.default_code == lines.get('ItemCode')
                                and l.price_unit == lines.get('UnitAmount')
                                and l.product_qty == lines.get('Quantity'))
                            if order_line:
                                order_line[0].write({'xero_order_line_id': lines.get('LineItemID'), 'order_id': order_id.id})

                    order_id.write({'xero_po_id': order_rec and order_rec[0].get('PurchaseOrderID'), 'xero_po_number': order_rec and order_rec[0].get('Reference')})
                    self._cr.commit()

                else:
                    create_order_data.append(final_order_data)
                    c += 1
                    if c == 50:
                        create_order_data_list.append(create_order_data)
                        create_order_data = []
                        c = 0

            elif order_id.xero_po_id:
                for xero_ord in po_list:
                    if xero_ord.get('PurchaseOrderID') == order_id.xero_po_id:
                        order_currency_rate = 0.0
                        status = u'DRAFT'
                        if order_id.state == 'draft' and xero_ord.get('Status') == 'DRAFT':
                            status = u'DRAFT'
                        if order_id.state in ['purchase', 'done'] and xero_ord.get('Status') not in ['DELETED','BILLED']:
                            status = u'AUTHORISED'
                        if order_id.state == 'cancel':
                            status = u'DELETED'
                        if order_id.invoice_status == 'invoiced' and xero_ord.get('Status') not in ['DELETED', 'BILLED']:
                            status = u'BILLED'
                        if status == u'DRAFT' and xero_ord.get('Status') in ['BILLED']:
                            status = u'BILLED'
                        partner_details = {}
                        if order_id.partner_id.parent_id:
                            contact = order_id.partner_id.parent_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                            if not contact.xero_contact_id:
                                xero_account.export_contact_overwrite() if xero_account.contact_overwrite else xero_account.export_contact()
                                contact = order_id.partner_id.parent_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                            partner_details = {u'ContactID': contact.xero_contact_id}
                        else:
                            contact = order_id.partner_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                            if not contact.xero_contact_id:
                                xero_account.export_contact_overwrite() if xero_account.contact_overwrite else xero_account.export_contact()
                                contact = order_id.partner_id.contact_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                            partner_details = {u'ContactID': contact.xero_contact_id}
                        line_amount_type = order_id.line_amount_type

                        order_data = {
                                        u'PurchaseOrderID': order_id.xero_po_id,
                                        u'Status': status,
                                        u'LineAmountTypes': line_amount_type,
                                        u'Contact': partner_details,
                                        u'Reference': order_id.burgtec_purchase_reference if order_id.burgtec_purchase_reference else u'',
                                        u'Date': order_id.date_approve or fields.Date.today(),
                                        u'DeliveryDate': order_id.date_planned or fields.Date.today(),
                                        u'CurrencyCode': order_id.currency_id.name,
                                        u'TotalTax': order_id.amount_tax if order_id.amount_tax else 0.0,
                                    }

                        line_items = []
                        for ord_line in order_id.order_line.filtered(lambda l: l.product_id):
                            if ord_line.taxes_id:
                                tax_type = ord_line.taxes_id[0]
                            else:
                                if order_id:
                                    tax_type = self.env['account.tax'].search([('type_tax_use', '=', 'purchase'), ('amount', '=', 0), ('company_id', '=', company)], limit=1)
                                    if not tax_type:
                                        company_id = self.env['res.company'].browse(company)
                                        raise UserError(_('Please create account tax of type \'PURCHASE\' and amount = 0.0 for Company: %s')% (company_id.name))

                            if not tax_type.xero_tax_type:
                                tax_rates = xero.taxrates.all()
                                self.env['account.tax'].export_tax(tax_rates, xero, xero_account_id, company=company, disable_export=disable_export)
                            if ord_line.product_id:
                                product = ord_line.product_id.product_xero_company_ids.filtered(lambda l: l.company_id.id == company)
                                if product and not product[0].xero_item_id:
                                    xero_account.export_product()

                            vals = {
                                u'Description': ord_line.name or ord_line.product_id.name,
                                u'UnitAmount': ord_line.price_unit,
                                u'TaxType': u'' if ord_line.order_id.line_amount_type == 'NoTax' else tax_type and tax_type.xero_tax_type or u'',
                                u'Quantity': ord_line.product_qty,
                                u'ItemCode': ord_line.product_id.default_code,
                                u'DiscountRate': ord_line.discount,
                            }
                            if ord_line.xero_order_line_id:
                                vals.update({
                                    u'LineItemID': ord_line.xero_order_line_id,
                                })

                            line_items.append(vals)
                        if line_items:
                            order_data.update({u'LineItems': line_items})
                        if order_id.state in ['purchase','done'] and order_id.invoice_status == 'invoiced':
                            xero_account.export_invoice()
                        if order_id.state == 'draft':
                            request += 1
                            if request > 30:
                                time.sleep(1)
                            order_rec = xero.purchaseorders.save(order_data)
                            if order_rec and order_rec[0].get('ValidationErrors'):
                                description = order_rec[0].get('ValidationErrors')[0].get('Message')
                                mismatch_log.create({'name': order_rec[0].get('PurchaseOrderNumber') or order_rec[0].get('Reference'),
                                                     'source_model': 'purchase.order',
                                                     'source_id': order_id.id,
                                                     'description': description,
                                                     'date': fields.Datetime.now(),
                                                     'option': 'export',
                                                     'xero_account_id': xero_account_id})
                                continue
                            if order_rec in order_rec[0].get('LineItems'):
                                for lines in order_rec[0].get('LineItems'):
                                    order_line = order_id.order_line.filtered(lambda l: not l.xero_order_line_id
                                        and l.product_id.default_code == lines.get('ItemCode')
                                        and l.price_unit == lines.get('UnitAmount')
                                        and l.product_qty == lines.get('Quantity'))
                                    if order_line:
                                        order_line[0].write({'xero_order_line_id': lines.get('LineItemID'), 'order_id': order_id.id})

                            self._cr.commit()
                        else:
                            update_order_data.append(order_data)
                            count += 1
                            if count == 50:
                                update_order_data_list.append(update_order_data)
                                update_order_data = []
                                count = 0

        if create_order_data:
            create_order_data_list.append(create_order_data)
        for data in create_order_data_list:
            order_rec = xero.purchaseorders.put(data)
            for odr in order_rec:
                if odr.get('ValidationErrors'):
                    description = odr.get('ValidationErrors')[0].get('Message')
                    mismatch_log.create({'name': odr.get('PurchaseOrderNumber') or odr.get('Reference'),
                                         'source_model': 'purchase.order',
                                         'description': description,
                                         'date': fields.Datetime.now(),
                                         'option': 'export',
                                         'xero_account_id': xero_account_id})
                    continue
                order_id = self.search([('burgtec_purchase_reference', '=', odr.get('Reference')), ('company_id', '=', company)],limit=1)
                for lines in odr.get('LineItems'):
                    order_line = order_id.order_line.filtered(lambda l: not l.xero_order_line_id
                        and l.product_id.default_code == lines.get('ItemCode')
                        and l.price_unit == lines.get('UnitAmount')
                        and l.product_qty == lines.get('Quantity'))
                    if order_line:
                        order_line[0].write({'xero_order_line_id': lines.get('LineItemID'), 'order_id': order_id.id})

                order_id.write({'xero_po_id': odr.get('PurchaseOrderID'), 'xero_po_number': odr.get('Reference')})
                self._cr.commit()

        if update_order_data:
            update_order_data_list.append(update_order_data)
        for data in update_order_data_list:
            order_rec = xero.purchaseorders.save(data)
            for odr in order_rec:
                if odr.get('ValidationErrors'):
                    description = odr.get('ValidationErrors')[0].get('Message')
                    mismatch_log.create({'name': odr.get('PurchaseOrderNumber') or odr.get('Reference'),
                                         'source_model': 'purchase.order',
                                         'description': description,
                                         'date': fields.Datetime.now(),
                                         'option': 'export',
                                         'xero_account_id': xero_account_id})
                    continue
                order_id = self.search([('name', '=', odr.get('Reference')), ('company_id', '=', company)],limit=1)
                for lines in odr.get('LineItems'):
                    order_line = order_id.order_line.filtered(lambda l: not l.xero_order_line_id
                        and l.product_id.default_code == lines.get('ItemCode')
                        and l.price_unit == lines.get('UnitAmount')
                        and l.product_qty == lines.get('Quantity'))
                    if order_line:
                        order_line[0].write({'xero_order_line_id': lines.get('LineItemID'), 'order_id': order_id.id})
                        self._cr.commit()
                self._cr.commit()
