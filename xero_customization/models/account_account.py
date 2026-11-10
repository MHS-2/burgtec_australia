# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAccount(models.Model):
    _inherit = 'account.account'

    def import_account(self, account_list, xero, xero_account_id, company=False, import_option=None):
        """
            Map: AccountID(Odoo) with AccountID(Xero)

            Create a account in Odoo if account is not available with
            AccountID and company.

            Note: If any record is already available with same code in Odoo which we
            going to import from xero then it will skip that particular record.

            Constraint(Odoo): The code of the account must be unique per company

            If account record is available then it will update that particular record.
        """
        mismatch_log = self.env['mismatch.log']
        account_mapping = {'bank': 'asset_cash',
                           'current': 'asset_current',
                           'currliab': 'liability_current',
                           'depreciatn': 'expense_depreciation',
                           'directcosts': 'expense',
                           'equity': 'equity',
                           'expense': 'expense',
                           'fixed': 'asset_fixed',
                           'inventory': 'asset_current',
                           'liability': 'liability_current',
                           'noncurrent': 'asset_non_current',
                           'otherincome': 'income_other',
                           'overheads': 'expense',
                           'prepayment': 'asset_prepayments',
                           'revenue': 'expense_direct_cost',
                           'sales': 'asset_receivable',
                           'termliab': 'liability_non_current',
                           'paygliability': 'liability_current',
                           'wagesexpense': 'expense',
                           'superannuationexpense': 'expense',
                           'superannuationliability': 'liability_non_current',
                            }

        for account in account_list:
            if account.get('Status') == 'ACTIVE' and account.get('Type'):
                account_type = str(account['Type'].lower())
                if account_mapping.get(account_type):
                    user_type = account_mapping[account_type]
                    account_rec = self.search([('acc_id', '=', account.get('AccountID')),
                                               ('company_ids', 'in', company)], limit=1)
                    if account.get('Type') == 'BANK' and not account.get('Code'):
                        raise UserError(_('Please enter unique code for account \'%s\' on Xero side.')% (account.get('Name')))
                    available_acc_ids = self.search([('code', '=', account.get('Code')),
                                                     ('company_ids', 'in', company)], limit=1)

                    if available_acc_ids and not available_acc_ids.acc_id and available_acc_ids.name == account.get('Name'):
                        available_acc_ids.acc_id = account.get('AccountID')
                    tax_id = self.env['account.tax'].search([('xero_tax_type', '=', account.get('TaxType')),
                                                             ('company_id', '=', company)])
                                                             
                    # _logger.info("Account Rec %s and Available Account Ids %s",account_rec, available_acc_ids)
                    # _logger.info("Current CHART ACCOUNT VAL -->, Name %s , Code %s , Acc_Id %s", account.get('Name'), account.get('Code'), account.get('AccountID'))
                    if account_rec and import_option in ['update', 'both']:
                        _logger.info("----- UPDATING -----")
                        try:
                            account_rec.write({
                                     'name': account.get('Name'),
                                     'company_ids': [(4, company)],
                                     'tax_ids': [(6, 0, [tax_id[0].id])] if tax_id else [],
                                     'use_as_inventory_in_xero': True if account_type == 'inventory' else False,
                                     'xero_description': account.get('Description'),
                                     # 'account_type_xero': account_type,
                                     # 'account_type': user_type or False,
                                })
                        except Exception as e:
                            _logger.info("MIS MATCH (FIRST IF) !!! CHART ACCOUNT !, Name %s , Code %s , Acc_Id %s", account.get('Name'), account.get('Code'), account.get('AccountID'))
                            mismatch_log.create({'name': account.get('Name'),
                                                 'source_model': 'account.account',
                                                 'description': e,
                                                 'date': fields.Datetime.now(),
                                                 'option': 'import',
                                                 'xero_account_id': xero_account_id,
                                                 })
                            continue
                    elif not account_rec and not available_acc_ids and import_option in ['create', 'both']:
                        _logger.info("----- CREATING -----")
                        _logger.info("Account Rec %s and Available Account Ids %s",account_rec.name, available_acc_ids)
                        try:
                            _logger.info("CREATING CHART ACCOUNT !, Name %s , Code %s , Acc_Id %s", account.get('Name'), account.get('Code'), account.get('AccountID'))
                            self.create({'name': account.get('Name'),
                                         'code': account.get('Code'),
                                         'acc_id': account.get('AccountID'),
                                         'company_ids': [(4, company)],
                                         'tax_ids': [(6, 0, [tax_id[0].id])] if tax_id else [],
                                         'account_type': user_type or False,
                                         'use_as_inventory_in_xero': True if account_type == 'inventory' else False,
                                         'xero_description': account.get('Description'),
                                         'account_type_xero': account_type})
                            self._cr.commit()
                        except Exception as e:
                            _logger.info("MIS MATCH (SECOND IF) !!! CHART ACCOUNT !, Name %s , Code %s , Acc_Id %s", account.get('Name'), account.get('Code'), account.get('AccountID'))
                            mismatch_log.create({'name': account.get('Name'),
                                                 'source_model': 'account.account',
                                                 'description': e,
                                                 'date': fields.Datetime.now(),
                                                 'option': 'import',
                                                 'xero_account_id': xero_account_id,
                                                 })
                            continue

