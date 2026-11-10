import ast
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.sync_xero_connector.lib.xero.auth import PublicCredentials,PrivateCredentials, OAuth2Credentials
from odoo.addons.sync_xero_connector.lib.xero.constants import XeroScopes
from odoo.addons.sync_xero_connector.lib.xero import Xero
from odoo.addons.sync_xero_connector.lib.xero.exceptions import (
    XeroAccessDenied,
)
from requests_oauthlib import OAuth1, OAuth2, OAuth2Session
from datetime import datetime
import datetime
import time


# Xero New Granular Scopes

ACCOUNTING_INVOICES = "accounting.invoices"
ACCOUNTING_INVOICES_READ = "accounting.invoices.read"
ACCOUNTING_PAYMENTS = "accounting.payments"
ACCOUNTING_PAYMENTS_READ = "accounting.payments.read"
ACCOUTNING_BACNKTRANSACTIONS = "accounting.banktransactions"
ACCOUTNING_BACNKTRANSACTIONS_READ = "accounting.banktransactions.read"
ACCOUNTING_MANUALJOURNALS = "accounting.manualjournals"
ACCOUNTING_MANUALJOURNALS_READ = "accounting.manualjournals.read"


class XeroAccountExt(models.Model):
    _inherit = 'xero.account'

    # For Second Xero (New Zeland) 

    second_client_id = fields.Char(string='Client ID')
    second_client_secret = fields.Char(string='Client Secret')
    second_callback_uri = fields.Char('Call Back URI')
    second_raw_url = fields.Char('Generated Raw URL')
    second_raw_uri = fields.Char('Raw URI')
    second_state = fields.Char('State')
    second_token = fields.Char('Token')
    second_auth = fields.Char()
    seccond_xero_org_id = fields.Many2one('xero.organization', string='Import/Export Xero Organization')



    
    @api.model
    def automatic_import_contacts(self):
        context = dict(self.env.context) or {}
        context.update({'schedule_action': True})
        self.env.context = context
        for record in self.search([('active', '=', True)]):
            xero = record.xero_auth()
            if xero:
                try:
                    # Import Contact Group
                    # Import Contacts
                    record.import_contact_overwrite() if record.contact_overwrite else record.import_contact()
                    
                except Exception as e:
                    mismatch_vals = {'name': record.name,
                                 'source_model': 'ir.cron',
                                 'source_id': record.id,
                                 'description': e,
                                 'date': fields.datetime.now(),
                                 'option': 'import',
                                 'xero_account_id': record.id
                                 }
                    self.env['mismatch.log'].create(mismatch_vals)

        context.pop('schedule_action')
        self.env.context = context
    
    def import_contact_overwrite(self):
        self.ensure_one()
        xero = self.xero_auth()

        group_list = xero.contactgroups.all()
        self.env['res.partner.category'].import_contact_group(group_list, xero)
        page = 0
        while True:
            page += 1
            contact_list = []
            if self.last_create_contact_import_date and self.import_option == 'create':
                contact_list = xero.contacts.filter(since=self.last_create_contact_import_date, page=page,includeArchived=True)
            elif self.last_update_contact_import_date and self.import_option == 'update':
                contact_list = xero.contacts.filter(since=self.last_update_contact_import_date, page=page,includeArchived=True)
            elif self.import_option == 'both' and self.last_create_contact_import_date and self.last_update_contact_import_date:
                min_date = min(self.last_create_contact_import_date, self.last_update_contact_import_date)
                contact_list = xero.contacts.filter(since=min_date, page=page,includeArchived=True)
            else:
                contact_list = xero.contacts.filter(page=page,includeArchived=True)
            if contact_list:
                self.env['res.partner'].import_contact_overwrite(contact_list, xero, xero_account_id=self.id, company=self.company_id.id, import_option=self.import_option)
            else:
                break

        if self.import_option == 'create':
            self.last_create_contact_import_date = fields.Datetime.now()
        elif self.import_option == 'update':
            self.last_update_contact_import_date = fields.Datetime.now()
        elif self.import_option == 'both':
            self.last_create_contact_import_date = fields.Datetime.now()
            self.last_update_contact_import_date = fields.Datetime.now()
    
    def import_all_contacts_overwrite(self):
        self.ensure_one()
        xero = self.xero_auth()

        group_list = xero.contactgroups.all()
        self.env['res.partner.category'].import_contact_group(group_list, xero)
        page = 0
        while True:
            page += 1
            contact_list = []
            contact_list = xero.contacts.filter(page=page,includeArchived=True)
            if contact_list:
                self.env['res.partner'].import_contact_overwrite(contact_list, xero, xero_account_id=self.id, company=self.company_id.id, import_option=self.import_option)
            else:
                break
    
    def check_all_contacts(self):
        self.ensure_one()
        xero = self.xero_auth()

        group_list = xero.contactgroups.all()
        self.env['res.partner.category'].import_contact_group(group_list, xero)
        page = 0
        total = 0
        while True:
            page += 1
            contact_list = []
            contact_list = xero.contacts.filter(page=page,includeArchived=True)
            if contact_list:
                total += len(contact_list)
            else:
                break
    
    @api.model
    def automatic_import(self):
        context = dict(self.env.context) or {}
        context.update({'schedule_action': True})
        self.env.context = context
        for record in self.search([('active', '=', True)]):
            xero = record.xero_auth()
                # Import Currency
            if xero:
                try:
                    # record.import_currency()
                    # # Import Tax
                    # record.import_tax()

                    # # Import Account
                    record.import_account()


                    # # Import Contact Group
                    # # Import Contacts
                    # record.import_contact_overwrite() if record.contact_overwrite else record.import_contact()
                    # # Import Bank Account
                    # record.import_bank_account()
                    # # Import Product
                    # if not record.inv_without_product:
                    #     record.import_product()
                    # # Import PO
                    # record.import_purchase_order()
                    # # Import SO
                    # record.import_quotes()

                    # -------------------------------------------------
                    # Import Invoice
                    record.import_invoice()
                    # -------------------------------------------------

                    # Import Manual Journal
                    # record.import_manual_journal()
                    # # Import Credit Notes
                    # if record.import_export_creditnotes == 'import':
                    #     record.import_credit_notes()
                except Exception as e:
                    mismatch_vals = {'name': record.name,
                                 'source_model': 'ir.cron',
                                 'source_id': record.id,
                                 'description': e,
                                 'date': fields.datetime.now(),
                                 'option': 'import',
                                 'xero_account_id': record.id
                                 }
                    self.env['mismatch.log'].create(mismatch_vals)

        context.pop('schedule_action')
        self.env.context = context

    
    @api.model
    def automatic_export(self):
        context = dict(self.env.context) or {}
        context.update({'schedule_action': True})
        self.env.context = context
        for record in self.search([('active', '=', True)]):
            xero = record.xero_auth()
            # Export Taxes
            if xero:
                try:
                    # ---------------------------------------------------------------
                    record.export_tax()
                    # # Export Accounts
                    record.export_account()
                    # # Export Bank Accounts
                    # record.export_bank_account()
                    # # Export Contact Groups
                    # ---------------------------------------------------------------

                    # Export Contacts
                    record.export_contact_overwrite()if record.contact_overwrite else record.export_contact()
                    # Export Products
                    record.export_product()

                    # ---------------------------------------------------------------

                    # # Export PO
                    # record.export_purchase_order()
                    # # Export SO
                    # record.export_quotes()
                    # # Export invoices
                    # record.export_invoice()
                    # record.export_payment()
                    # # Export credit Notes
                    # if record.import_export_creditnotes == 'export':
                    #     record.export_credit_notes()
                    #     record.export_credit_notes_payment()
                    # # Export Inventory Adjustments
                    # record.export_inventory_adjustments()
                    # #Export Attachment
                    # record.export_attachments()

                    # ---------------------------------------------------------------

                except Exception as e:
                    mismatch_vals = {'name': record.name,
                                 'source_model': 'ir.cron',
                                 'source_id': record.id,
                                 'description': e,
                                 'date': fields.datetime.now(),
                                 'option': 'export',
                                 'xero_account_id': record.id
                                 }
                    self.env['mismatch.log'].create(mismatch_vals)
        context.pop('schedule_action')
        self.env.context = context
    
    def generate_url_auth2(self):
        self.ensure_one()
        my_scope = [XeroScopes.ACCOUNTING_SETTINGS, XeroScopes.OPENID, XeroScopes.PROFILE, XeroScopes.EMAIL, XeroScopes.OFFLINE_ACCESS, XeroScopes.ACCOUNTING_CONTACTS, XeroScopes.ACCOUNTING_ATTACHMENTS, XeroScopes.PAYROLL_EMPLOYEES, ACCOUNTING_INVOICES, ACCOUNTING_PAYMENTS, ACCOUTNING_BACNKTRANSACTIONS, ACCOUNTING_MANUALJOURNALS]
        credentials = OAuth2Credentials(self.client_id, self.client_secret, scope=my_scope, callback_uri=self.callback_uri)
        url = credentials.generate_url()
        self.raw_url = url
        self.state = credentials.state.get('auth_state')
    
    def authenticate(self):
        self.ensure_one()
        my_scope = [XeroScopes.ACCOUNTING_SETTINGS, XeroScopes.OPENID, XeroScopes.PROFILE, XeroScopes.EMAIL, XeroScopes.OFFLINE_ACCESS, XeroScopes.ACCOUNTING_CONTACTS, XeroScopes.ACCOUNTING_ATTACHMENTS, XeroScopes.PAYROLL_EMPLOYEES, ACCOUNTING_INVOICES, ACCOUNTING_PAYMENTS, ACCOUTNING_BACNKTRANSACTIONS, ACCOUNTING_MANUALJOURNALS]
        new_credentials = OAuth2Credentials(self.client_id, self.client_secret, scope=my_scope, callback_uri=self.callback_uri)
        if not self.raw_uri:
            raise UserError(_('Please Add Raw URI.'))
        try:
            new_credentials.verify(self.raw_uri)
        except XeroAccessDenied as e:
            raise UserError(_('XeroAccessDenied %s'% e))
        except Exception as e:
            raise UserError(e)

        self.token = new_credentials.token

        xero = Xero(new_credentials)
        self.auth = Xero(new_credentials)

        tenants = new_credentials.get_tenants()
        tenant_list = []
        for tenant in tenants:
            xero_org_id = self.xero_org_ids.filtered(lambda l: l.xero_tenant_id == tenant.get('tenantId'))
            if not xero_org_id:
                new_credentials.tenant_id = tenant.get('tenantId')
                org = xero.organisations.all()
                tenant_data = {'name': org[0].get('Name'),
                                'xero_id': tenant.get('id'),
                                'xero_tenant_id': tenant.get('tenantId'),
                                'xero_tenant_type': tenant.get('tenantType'),
                                'xero_account_id': self.id,
                                }
                tenant_list.append((0, 0, tenant_data))
        self.xero_org_ids = tenant_list

        return Xero(new_credentials, unit_price_4dps=4)
    
    def re_authenticate(self):
        self.ensure_one()
        my_scope = [XeroScopes.ACCOUNTING_SETTINGS, XeroScopes.OPENID, XeroScopes.PROFILE, XeroScopes.EMAIL, XeroScopes.OFFLINE_ACCESS, XeroScopes.ACCOUNTING_CONTACTS, XeroScopes.ACCOUNTING_ATTACHMENTS, XeroScopes.PAYROLL_EMPLOYEES, ACCOUNTING_INVOICES, ACCOUNTING_PAYMENTS, ACCOUTNING_BACNKTRANSACTIONS, ACCOUNTING_MANUALJOURNALS]
        new_credentials = OAuth2Credentials(self.client_id, self.client_secret, scope=my_scope, callback_uri=self.callback_uri, token=ast.literal_eval(self.token))

        if new_credentials.expired():
            try:
                new_credentials.refresh()
            except Exception as e:
                if self._context.get('schedule_action'):
                    description = (_('Your Token has been expired %s, you need to Reauthentication' % e))
                    mismatch_vals = {'name': self.name,
                                 'source_model': 'xero.account',
                                 'source_id': self.id,
                                 'description': description,
                                 'date': fields.datetime.now(),
                                 'xero_account_id': self.id
                                 }
                    self.env['mismatch.log'].create(mismatch_vals)
                    return False
                else:
                    raise UserError(_('Your Token has been expired %s, you need to Reauthentication' % e))

            self.state = new_credentials.state
            self.token = new_credentials.token

        new_credentials.tenant_id = self.xero_org_id.xero_tenant_id
        return Xero(new_credentials, unit_price_4dps=4)

    
    # Second XERO METHODS UNIQUE TO THEM.

    def generate_url(self):
        """Get the authorization url. This will also set `self.auth_state` to a
        random string if it has not already been set.
        """
        XERO_OAUTH2_AUTHORIZE_URL = "https://login.xero.com/identity/connect/authorize"

        session = OAuth2Session(
            self.second_client_id, scope=self.scope, redirect_uri=self.second_callback_uri
        )
        url, self.auth_state = session.authorization_url(
            XERO_OAUTH2_AUTHORIZE_URL, state=self.auth_state
        )
        return url

    def generate_url_auth2(self):
        self.ensure_one()
        my_scope = [XeroScopes.ACCOUNTING_SETTINGS, XeroScopes.OPENID, XeroScopes.PROFILE, XeroScopes.EMAIL, XeroScopes.OFFLINE_ACCESS, XeroScopes.ACCOUNTING_CONTACTS, XeroScopes.ACCOUNTING_ATTACHMENTS, XeroScopes.PAYROLL_EMPLOYEES, ACCOUNTING_INVOICES, ACCOUNTING_PAYMENTS, ACCOUTNING_BACNKTRANSACTIONS, ACCOUNTING_MANUALJOURNALS]
        credentials = OAuth2Credentials(self.second_client_id, self.second_client_secret, scope=my_scope, callback_uri=self.second_callback_uri)
        url = credentials.generate_url()
        self.second_raw_url = url
        self.second_state = credentials.state.get('auth_state')

