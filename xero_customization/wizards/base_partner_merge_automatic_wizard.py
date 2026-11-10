# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    xero_contact_id = fields.Many2one('contact.xero.company')


    def _merge(self, partner_ids, dst_partner=None, extra_checks=True):
        """ private implementation of merge partner
            :param partner_ids : ids of partner to merge
            :param dst_partner : record of destination res.partner
            :param extra_checks: pass False to bypass extra sanity check (e.g. email address)
        """
        # super-admin can be used to bypass extra checks
        if self.env.is_admin():
            extra_checks = False

        Partner = self.env['res.partner']
        partner_ids = Partner.browse(partner_ids).exists()
        if len(partner_ids) < 2:
            return

        if len(partner_ids) > 6:
            raise UserError(_("For safety reasons, you cannot merge more than 6 contacts together. You can re-open the wizard several times if needed."))

        # check if the list of partners to merge contains child/parent relation
        child_ids = self.env['res.partner']
        for partner_id in partner_ids:
            child_ids |= Partner.search([('id', 'child_of', [partner_id.id])]) - partner_id
        if partner_ids & child_ids:
            raise UserError(_("You cannot merge a contact with one of his parent."))

        # check if the list of partners to merge are linked to more than one user
        if len(partner_ids.with_context(active_test=False).user_ids) > 1:
            raise UserError(_("You cannot merge contacts linked to more than one user even if only one is active."))

        if extra_checks and len(set(partner.email for partner in partner_ids)) > 1:
            raise UserError(_("All contacts must have the same email. Only the Administrator can merge contacts with different emails."))

        # remove dst_partner from partners to merge
        if dst_partner and dst_partner in partner_ids:
            src_partners = partner_ids - dst_partner
        else:
            ordered_partners = self._get_ordered_partner(partner_ids.ids)
            dst_partner = ordered_partners[-1]
            src_partners = ordered_partners[:-1]
        _logger.info("dst_partner: %s", dst_partner.id)

        # Make the company of all related users consistent with destination partner company
        if dst_partner.company_id:
            partner_ids.mapped('user_ids').sudo().write({
                'company_ids': [Command.link(dst_partner.company_id.id)],
                'company_id': dst_partner.company_id.id
            })

        # Merge bank accounts before merging partners
        self._merge_bank_accounts(src_partners, dst_partner)

        # call sub methods to do the merge
        self._update_foreign_keys(src_partners, dst_partner)
        self._update_reference_fields(src_partners, dst_partner)
        self._update_values(src_partners, dst_partner)

        self.env.add_to_compute(dst_partner._fields['partner_share'], dst_partner)

        self.set_xero_contact_id(dst_partner)

        self._log_merge_operation(src_partners, dst_partner)

        # delete source partner, since they are merged
        src_partners.unlink()

    
    def set_xero_contact_id(self, dst_partner):
        if not self.xero_contact_id:
            contact_xero_company = dst_partner.contact_xero_company_ids
            if len(contact_xero_company) > 1:
                dst_partner.contact_xero_company_ids.unlink()
        if self.xero_contact_id:
            selected_xero_contact_id = self.xero_contact_id.xero_contact_id
            selected_xero_contact_company = self.xero_contact_id.company_id
            contact_xero_company = dst_partner.contact_xero_company_ids
            contact_xero_company_object = self.env['contact.xero.company'].sudo()
            if contact_xero_company:
                dst_partner.contact_xero_company_ids.unlink()
            contact_xero_company_object.create({
                'company_id':selected_xero_contact_company.id,
                'partner_id':dst_partner.id,
                'xero_contact_id': selected_xero_contact_id,
            })
        


