# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.tools import float_is_zero
from itertools import groupby
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    posted_linked_invoice_count = fields.Integer(compute="_compute_posted_linked_invoice_count", string='Posted Linked Bill Count', copy=False, default=0, store=True)
    remaining_purchase_amount = fields.Monetary(compute="compute_remaining_purchase_amount", currency_field="currency_id", string="Outstanding Balance")

    invoice_status = fields.Selection(selection_add=[
            ('partially invoiced', 'Partially Billed'),
        ], ondelete={'partially invoiced': 'cascade',}, string='Billing Status', compute='_get_invoiced', store=True, readonly=True, copy=False, default='no')



    @api.depends('invoice_ids','invoice_ids.state')
    def _compute_posted_linked_invoice_count(self):
        for order in self:
            invoice = order.invoice_ids.filtered(lambda i:i.state in 'posted' and not i.reversal_move_ids and not i.reversed_entry_id)
            order.posted_linked_invoice_count = len(invoice)
    
    def compute_remaining_purchase_amount(self):
        for record in self:
            posted_bills = record.invoice_ids.filtered(lambda i:i.state in 'posted' and not i.reversal_move_ids and not i.reversed_entry_id)
            if not posted_bills:
                amount_billed = 0
            if posted_bills:
                amount_billed = sum(posted_bills.mapped('amount_untaxed'))
            po_amount = record.amount_total
            remaining_po_amount = po_amount - amount_billed
            record.remaining_purchase_amount = remaining_po_amount


    @api.model
    def _nothing_to_invoice_error(self):
        """Function to showing user error while there is no products are
        received for the purchase order"""
        return UserError(_(
            "There is nothing to bill!\n\n"
            "Reason(s) of this behavior could be:\n"
            "- You should recieve your products before billing them: "
            "Click on the \"truck\" icon "
            "(top-right of your screen) and follow instructions.\n"
            "- You should modify the control policy of your product: Open the "
            "product, go to the "
            "\"Purchase\" tab and modify control policy from \"On received "
            "quantities\" to \"On ordered"
            "quantities\"."
        ))
    
    def _prepare_invoice(self):
        """Prepare the dict of values to create the new invoice for a purchase order.
        """
        self.ensure_one()
        move_type = self._context.get('default_move_type', 'in_invoice')

        partner_invoice = self.env['res.partner'].browse(self.partner_id.address_get(['invoice'])['invoice'])
        partner_bank_id = self.partner_id.commercial_partner_id.bank_ids.filtered_domain(['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)])[:1]

        child_purchase_ref = self.burgtec_purchase_reference
        desire_ref_for_bill = child_purchase_ref.split('-', 1)[1]
        formatted_number = str(self.invoice_count+1).zfill(2)
        burgtec_bill_reference = f"BILL-{desire_ref_for_bill}-{formatted_number}"

        invoice_vals = {
            'burgtec_bill_reference': burgtec_bill_reference,
            'ref': self.partner_ref or '',
            'move_type': move_type,
            'narration': self.notes,
            'currency_id': self.currency_id.id,
            'partner_id': partner_invoice.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(partner_invoice)).id,
            'payment_reference': self.partner_ref or '',
            'partner_bank_id': partner_bank_id.id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }
        return invoice_vals
    
    def _deduct_payment(self, grouped=False, final=False, date=None):
        """
        Create the Bill associated to the PO.
        :returns: list of created invoices
        """
        invoice_vals_list = []
        invoice_item_sequence = 0  # Incremental sequencing to keep the lines
        # order on the invoice.
        for order in self:
            order = order.with_company(order.company_id)
            invoice_vals = order._prepare_invoice()
            invoiceable_lines = order._get_invoiceable_lines(final)
            if not any(not line.display_type for line in invoiceable_lines):
                continue
            invoice_line_vals = []
            down_payment_section_added = False
            for line in invoiceable_lines:
                if not down_payment_section_added and line.is_downpayment:
                    invoice_line_vals.append(
                        (0, 0, order._prepare_down_payment_section_line(
                            sequence=invoice_item_sequence,
                        )),
                    )
                    down_payment_section_added = True
                    invoice_item_sequence += 1
                invoice_line_vals.append(
                    (0, 0, line._prepare_invoice_line(
                        sequence=invoice_item_sequence,
                    )),
                )
                invoice_item_sequence += 1
            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)
        if not invoice_vals_list:
            raise self._nothing_to_invoice_error()
        if not grouped:
            new_invoice_vals_list = []
            invoice_grouping_keys = self._get_invoice_grouping_keys()
            invoice_vals_list = sorted(
                invoice_vals_list,
                key=lambda x: [
                    x.get(grouping_key) for grouping_key in
                    invoice_grouping_keys
                ]
            )
            for grouping_keys, invoices in groupby(invoice_vals_list,
                                                   key=lambda x: [
                                                       x.get(grouping_key) for
                                                       grouping_key in
                                                       invoice_grouping_keys]):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals[
                            'invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(
                        payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list
        if len(invoice_vals_list) < len(self):
            PurchaseOrderLine = self.env['purchase.order.line']
            for invoice in invoice_vals_list:
                sequence = 1
                for line in invoice['invoice_line_ids']:
                    line[2][
                        'sequence'] = PurchaseOrderLine._get_invoice_line_sequence(
                        new=sequence,
                        old=line[2]['sequence'])
                    sequence += 1
        moves = self.env['account.move'].sudo().with_context(
            default_move_type='out_invoice').create(invoice_vals_list)
        return moves
    
    @api.model
    def _prepare_down_payment_section_line(self, **optional_values):
        """
        Prepare the dict of values to create a new down payment section for a
        purchase order line. :param optional_values: any parameter that
        should be added to the returned down payment section
        """
        context = {'lang': self.partner_id.lang}
        down_payments_section_line = {
            'display_type': 'line_section',
            'name': _('Down Payments'),
            'product_id': False,
            'product_uom_id': False,
            'quantity': 0,
            'discount': 0,
            'price_unit': 0,
            'account_id': False
        }
        del context
        if optional_values:
            down_payments_section_line.update(optional_values)
        return down_payments_section_line

    def _get_invoice_grouping_keys(self):
        """Return invoice grouping keys"""
        return ['company_id', 'partner_id', 'currency_id']

    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        down_payment_line_ids = []
        invoiceable_line_ids = []
        pending_section = None
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for line in self.order_line:
            line.display_type = ''
            if line.display_type == 'line_section':
                pending_section = line
                continue
            if line.display_type != 'line_note' and float_is_zero(
                    line.qty_to_invoice, precision_digits=precision):
                continue
            if (line.qty_to_invoice > 0 or (
                    line.qty_to_invoice < 0 and final) or line.display_type ==
                    'line_note'):
                if line.is_downpayment:
                    down_payment_line_ids.append(line.id)
                    continue
                if pending_section:
                    invoiceable_line_ids.append(pending_section.id)
                    pending_section = None
                invoiceable_line_ids.append(line.id)
        return self.env['purchase.order.line'].browse(
            invoiceable_line_ids + down_payment_line_ids)
    
    def action_view_posted_linked_invoice(self, invoices=False):
        """This function returns an action that display existing vendor bills of
        given purchase order ids. When only one found, show the vendor bill
        immediately.
        """
        if not invoices:
            self.invalidate_model(['invoice_ids'])
            invoices = self.invoice_ids.filtered(lambda i:i.state in 'posted' and not i.reversal_move_ids and not i.reversed_entry_id)

        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        # choose the view_mode accordingly
        if len(invoices) > 1:
            result['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            res = self.env.ref('account.view_move_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = invoices.id
        else:
            result = {'type': 'ir.actions.act_window_close'}

        return result
    

    @api.depends('state', 'order_line.qty_to_invoice')
    def _get_invoiced(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for order in self:
            if order.state not in ('purchase', 'done'):
                order.invoice_status = 'no'
                continue

            if any(
                not float_is_zero(line.qty_to_invoice, precision_digits=precision)
                for line in order.order_line.filtered(lambda l: not l.display_type)
            ):

                if order.posted_linked_invoice_count == 0:
                    order.invoice_status = 'to invoice'
                    continue

                if order.posted_linked_invoice_count > 0:
                    order.invoice_status = 'partially invoiced'
                    continue

            elif (
                all(
                    float_is_zero(line.qty_to_invoice, precision_digits=precision)
                    for line in order.order_line.filtered(lambda l: not l.display_type)
                )
                and order.invoice_ids
            ):
                order.invoice_status = 'invoiced'
            else:
                order.invoice_status = 'no'
