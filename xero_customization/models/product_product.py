# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from bs4 import BeautifulSoup


_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_export_product = fields.Boolean(default=False, readonly=True)

    # def export_product(self, product_list, xero, last_export_date, xero_account_id, company=False, item_ids=[]):
    #     """
    #     Map: ItemID(Odoo) with ItemID(Xero)

    #     Create a product in Xero if product is not available.

    #     If product record is available in xero then it will update that particular record.
    #     """
    #     # property_pool = self.env['ir.property'].sudo()
    #     account_pool = self.env['account.account']
    #     mismatch_log = self.env['mismatch.log']
    #     same_record = []
    #     final_product_list = []
    #     product_code_list = []
    #     if self._context.get('product_ids'):
    #         item_ids = self._context.get('product_ids')
    #     else:
    #         if len(item_ids) <= 0:
    #             if last_export_date:
    #                 item_ids = self.search(['|', ('company_id', '=', company), ('company_id', '=', False), '|', ('write_date', '>=', last_export_date), ('create_date', '>=', last_export_date)])
    #             else:
    #                 item_ids = self.search(['|', ('company_id', '=', company), ('company_id', '=', False)])
    #     for product_id in item_ids:
    #         xero_company = product_id.product_xero_company_ids.filtered(lambda l: l.company_id.id == company)
    #         if not xero_company:
    #             product_id.product_xero_company_ids = [(0, 0, {'company_id': company})]
    #         for name in product_list:
    #             xero_company_id = product_id.product_xero_company_ids.filtered(lambda l: l.company_id.id == company)
    #             if product_id.default_code == name.get('Code'):
    #                 if xero_company_id:
    #                     xero_company_id[0].xero_item_id = name.get('ItemID')
    #             else:
    #                 product_code_list.append(name.get('Code'))

    #             if xero_company_id and xero_company_id[0].xero_item_id == name.get('ItemID'):
    #                 same_record.append(product_id.id)
    #         final_product_list.append(product_id.id)

    #     item_data = []
    #     data = []
    #     c = 0
    #     for record in self.browse(list(set(final_product_list).difference(set(same_record)))):
    #         description = False
    #         if record.description:
    #             soup = BeautifulSoup(record.description, 'lxml')
    #             description = soup.get_text()
    #         # res = 'product.template,' + str(record.product_tmpl_id.id)
    #         # purchase_account = property_pool.search([('company_id', '=', company), ('res_id', '=', res),
    #         #                                          ('name', '=', 'property_account_expense_id')], limit=1)
    #         # sale_account = property_pool.search([('company_id', '=', company), ('res_id', '=', res),
    #         #                                      ('name', '=', 'property_account_income_id')], limit=1)

    #         purchase_account = record.with_company(company).property_account_expense_id or record.categ_id.with_company(company).property_account_expense_categ_id
    #         sale_account = record.with_company(company).property_account_income_id or record.categ_id.with_company(company).property_account_income_categ_id
    #         stock_account = record.categ_id.with_company(company).property_stock_account_input_categ_id

    #         # categ_res = 'product.category,' + str(record.categ_id.id)
    #         # if not purchase_account:
    #         #     purchase_account = property_pool.search([('company_id', '=', company), '|' ,('res_id', '=', categ_res), ('res_id', '=', False),
    #         #                                              ('name', '=', 'property_account_expense_categ_id')], limit=1)
    #         # if not sale_account:
    #         #     sale_account = property_pool.search([('company_id', '=', company), '|', ('res_id', '=', categ_res), ('res_id', '=', False),
    #         #                                          ('name', '=', 'property_account_income_categ_id')], limit=1)

    #         # stock_account = property_pool.search([('company_id', '=', company), ('res_id', '=', categ_res),
    #         #                                       ('name', '=', 'property_stock_account_input_categ_id')], limit=1)

    #         purchase_account_code = purchase_account.code
    #         sale_account_code = sale_account.code
    #         stock_account_code = stock_account.code

    #         # purchase_account_code = account_pool.browse(int(purchase_account.value_reference.split(',')[1])).code if purchase_account else ''
    #         # sale_account_code = account_pool.browse(int(sale_account.value_reference.split(',')[1])).code if sale_account else ''
    #         # stock_account_code = account_pool.browse(int(stock_account.value_reference.split(',')[1])).code if stock_account and stock_account.value_reference else ''

    #         sale_tax_type = False
    #         if record.taxes_id:
    #             taxes = record.taxes_id.filtered(lambda l: l.company_id.id == company)
    #             sale_tax_type = taxes[0] if taxes else ''
    #         purchase_tax_type = False

    #         if record.supplier_taxes_id:
    #             supplier_taxes = record.supplier_taxes_id.filtered(lambda l: l.company_id.id == company)
    #             purchase_tax_type = supplier_taxes[0] if supplier_taxes else ''

    #         if record.lst_price > 0.0:
    #             sale_price = record.lst_price
    #         else:
    #             sale_price = record.list_price
    #         if record.default_code and record.default_code not in product_code_list:
    #             item_name = record.name and record.name[:49]
    #             code = record.default_code and record.default_code[:30]

    #             item = {
    #                 u'Code': code,
    #                 u'Name': item_name,
    #                 u'Description': description or u'',
    #                 u'PurchaseDescription': description or u'',
    #                 u'SalesDetails': {u'UnitPrice': sale_price,
    #                                   u'AccountCode': sale_account_code,
    #                                   u'TaxType': sale_tax_type.xero_tax_type if sale_tax_type and sale_tax_type.xero_tax_type else u''}
    #             }
    #             if record.categ_id.property_valuation == 'real_time':
    #                 item.update({
    #                         u'InventoryAssetAccountCode': stock_account_code,
    #                         u'PurchaseDetails': {
    #                                     u'UnitPrice': record.standard_price,
    #                                     u'COGSAccountCode': purchase_account_code,
    #                                     u'TaxType': purchase_tax_type.xero_tax_type if purchase_tax_type else u''
    #                                 },
    #                 })
    #             else:
    #                 item.update({
    #                         u'PurchaseDetails': {
    #                                     u'UnitPrice': record.standard_price,
    #                                     u'AccountCode': purchase_account_code,
    #                                     u'TaxType': purchase_tax_type.xero_tax_type if purchase_tax_type else u''
    #                                 },
    #                 })
    #             data.append(item)
    #             c += 1
    #             if c == 50:
    #                 item_data.append(data)
    #                 data = []
    #                 c = 0
    #         elif not record.default_code and record.name not in product_code_list:
    #             item_name = record.name and record.name[:49]
    #             name = record.name and record.name[:30]
    #             record.write({'default_code': name})

    #             item = {
    #                 u'Code': name,
    #                 u'Name': item_name,
    #                 u'Description': description or u'',
    #                 u'PurchaseDescription': description or u'',
    #                 u'SalesDetails': {u'UnitPrice': sale_price,
    #                                   u'AccountCode': sale_account_code,
    #                                   u'TaxType': sale_tax_type.xero_tax_type if sale_tax_type and sale_tax_type.xero_tax_type else u''}
    #             }

    #             if record.categ_id.property_valuation == 'real_time':
    #                 item.update({
    #                     u'InventoryAssetAccountCode': stock_account_code,
    #                     u'PurchaseDetails': {
    #                                 u'UnitPrice': record.standard_price,
    #                                 u'COGSAccountCode': purchase_account_code,
    #                                 u'TaxType': purchase_tax_type.xero_tax_type if purchase_tax_type and purchase_tax_type.xero_tax_type else u''
    #                             },
    #                 })
    #             else:
    #                 item.update({
    #                         u'PurchaseDetails': {
    #                                 u'UnitPrice': record.standard_price,
    #                                 u'AccountCode': purchase_account_code,
    #                                 u'TaxType': purchase_tax_type.xero_tax_type if purchase_tax_type and purchase_tax_type.xero_tax_type else u''
    #                             },
    #                     })
    #             data.append(item)
    #             c += 1
    #             if c == 50:
    #                 item_data.append(data)
    #                 data = []
    #                 c = 0
    #     if data:
    #         item_data.append(data)

    #     for data in item_data:
    #         item_rec = xero.items.put(data)
    #         for item in item_rec:
    #             if item.get('ValidationErrors'):
    #                 description = item.get('ValidationErrors')[0].get('Message')
    #                 mismatch_log.create({'name': item.get('Name'),
    #                                      'source_model': 'product.product',
    #                                      'description': description,
    #                                      'date': fields.Datetime.now(),
    #                                      'option': 'export',
    #                                      'xero_account_id': xero_account_id})
    #                 continue
    #             product_id = self.search(['|', ('default_code', '=', item.get('Code')), ('name', '=', item.get('Code'))], limit=1)
    #             # Customisation for exprot tag on products
    #             if product_id:
    #                 product_id.is_export_product = True
    #                 product_id.message_post(body=_('Product Exported Successfully'), message_type='comment', subtype_xmlid='mail.mt_comment')
    #             xero_company = product_id.product_xero_company_ids.filtered(lambda l: l.company_id.id == company)
    #             xero_company.xero_item_id = item.get('ItemID')
    #             self._cr.commit()
    #     item_data = []
    #     data = []
    #     c = 0
    #     for product in self.browse(same_record):
    #         description = False
    #         if product.description:
    #             soup = BeautifulSoup(product.description,'lxml')
    #             description = soup.get_text()
    #         code = product.default_code and product.default_code[:30]
    #         item_name = product.name and product.name[:49]

    #         # res = 'product.template,' + str(product.product_tmpl_id.id)
    #         # purchase_account = property_pool.search([('company_id', '=', company), ('res_id', '=', res),
    #         #                                          ('name', '=', 'property_account_expense_id')], limit=1)
    #         # sale_account = property_pool.search([('company_id', '=', company), ('res_id', '=', res),
    #         #                                      ('name', '=', 'property_account_income_id')], limit=1)

    #         # categ_res = 'product.category,' + str(product.categ_id.id)
    #         # if not purchase_account:
    #         #     purchase_account = property_pool.search([('company_id', '=', company), '|' ,('res_id', '=', categ_res), ('res_id', '=', False),
    #         #                                              ('name', '=', 'property_account_expense_categ_id')], limit=1)
    #         # if not sale_account:
    #         #     sale_account = property_pool.search([('company_id', '=', company), '|', ('res_id', '=', categ_res), ('res_id', '=', False),
    #         #                                          ('name', '=', 'property_account_income_categ_id')], limit=1)

    #         # stock_account = property_pool.search([('company_id', '=', company), ('res_id', '=', categ_res),
    #         #                                       ('name', '=', 'property_stock_account_input_categ_id')], limit=1)

    #         purchase_account = product.property_account_expense_id or product.categ_id.property_account_expense_categ_id
    #         sale_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
    #         stock_account = product.categ_id.property_stock_account_input_categ_id

    #         purchase_account_code = purchase_account.code
    #         sale_account_code = sale_account.code
    #         stock_account_code = stock_account.code

    #         # purchase_account_code = account_pool.browse(int(purchase_account.value_reference.split(',')[1])).code if purchase_account else ''
    #         # sale_account_code = account_pool.browse(int(sale_account.value_reference.split(',')[1])).code if sale_account else ''
    #         # stock_account_code = account_pool.browse(int(stock_account.value_reference.split(',')[1])).code if stock_account and stock_account.value_reference else ''

    #         sale_tax_type = False
    #         if product.taxes_id:
    #             taxes = product.taxes_id.filtered(lambda l: l.company_id.id == company)
    #             sale_tax_type = taxes[0] if taxes else False
    #         purchase_tax_type = False
    #         if product.supplier_taxes_id:
    #             supplier_taxes = product.supplier_taxes_id.filtered(lambda l: l.company_id.id == company)
    #             purchase_tax_type = supplier_taxes[0] if supplier_taxes else False

    #         if product.lst_price > 0.0:
    #             sale_price = product.lst_price
    #         else:
    #             sale_price = product.list_price
    #         xero_company = product.product_xero_company_ids.filtered(lambda l: l.company_id.id == company)

    #         items = {
    #             u'Code': code or name,
    #             u'Name': item_name,
    #             u'Description': description or u'',
    #             u'PurchaseDescription': description or u'',
    #             u'SalesDetails': {u'UnitPrice': sale_price,
    #                               u'AccountCode': sale_account_code,
    #                               u'TaxType': sale_tax_type.xero_tax_type if sale_tax_type and sale_tax_type.xero_tax_type else u''},
    #             u'ItemID': xero_company[0].xero_item_id if xero_company else ''
    #         }

    #         if product.categ_id.property_valuation == 'real_time':
    #             items.update({
    #                 u'InventoryAssetAccountCode': stock_account_code,
    #                 u'PurchaseDetails': {
    #                             u'UnitPrice': product.standard_price,
    #                             u'COGSAccountCode': purchase_account_code,
    #                             u'TaxType': purchase_tax_type.xero_tax_type if purchase_tax_type and purchase_tax_type.xero_tax_type else u''
    #                         },
    #             })
    #         else:
    #             items.update({
    #                 u'PurchaseDetails': {
    #                             u'UnitPrice': product.standard_price,
    #                             u'AccountCode': purchase_account_code,
    #                             u'TaxType': purchase_tax_type.xero_tax_type if purchase_tax_type and purchase_tax_type.xero_tax_type else u''
    #                         },
    #             })
    #         data.append(items)
    #         c += 1
    #         if c == 50:
    #             item_data.append(data)
    #             data = []
    #             c = 0
    #     if data:
    #         item_data.append(data)
    #     for data in item_data:
    #         item_rec = xero.items.save(data)
    #         for item in item_rec:
    #             if item.get('ValidationErrors'):
    #                 description = item.get('ValidationErrors')[0].get('Message')
    #                 mismatch_log.create({'name': item.get('Name'),
    #                                      'source_model': 'product.product',
    #                                      'description': description,
    #                                      'date': fields.Datetime.now(),
    #                                      'option': 'export',
    #                                      'xero_account_id': xero_account_id})
    #                 continue
    #         self._cr.commit()

