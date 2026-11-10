from email.policy import default
from odoo.tools import float_compare, float_is_zero, format_date, groupby
from odoo import models, api, fields, _, Command
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo import models
import io
import base64
import xlsxwriter

import logging

_logger = logging.getLogger(__name__)


class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    order_line = fields.One2many(
        comodel_name='sale.order.line',
        inverse_name='order_id',
        string="Order Lines",
        domain=[('is_downpayment', '=', False)],
        copy=True, auto_join=True)

    down_payment_order_line_ids = fields.One2many(
        comodel_name='sale.order.line',
        inverse_name='order_id',
        string="Down Payment Order Lines",
        domain=[('is_downpayment', '=', True)],
        auto_join=True)

    user_is_planning_admin = fields.Boolean(
        compute="_compute_user_is_planning_admin",
        store=False
    )

    @api.depends()
    def _compute_user_is_planning_admin(self):
        for rec in self:
            rec.user_is_planning_admin = self.env.user.has_group(
                'quotation_type_customization.group_planning_screen_admin')

    x_invoice_ids = fields.Many2many(
        comodel_name='account.move',
        relation='sale_order_account_move_rel',
        column1='sale_id',
        column2='move_id',
        string="Linked Invoices",
        copy=False,
        help="Stored link to invoices created for this sale (used for smart buttons)."
    )

    quote_type = fields.Selection([
        ('sales_quote', 'Sales Quote'),
        ('project_quote', 'Project'),
        ('delivery_stage', 'Delivery Stage'),
    ], default='sales_quote')
    new_sale_order_number = fields.Char(string="New Sale Order Number", readonly=True)
    series_sequence_id = fields.Many2one('sale.order.series', string="Series Sequence")
    series_from_hubspot_ref = fields.Char()
    site_address = fields.Char(string="Site Address")


    burgtec_po_status = fields.Selection([
        ('draft_to_approve', 'Draft - To be Approved'),
        ('draft_to_sent', 'Draft - To be Sent'),
        ('sent', 'Sent - Awaiting Supplier Confirmation'),
        ('await_receipt', 'Awaiting Receipt'),
        ('received_partial', 'Received - Partial'),
        ('received_full', 'Received - Full'),
        ('delivery_only', 'Delivery Only'),
        ('delivered_partial', 'Delivered - Partial'),
        ('delivered_full', 'Delivered - Full')
    ], string="Burgtec PO Status", compute="_compute_burgtec_po_status")

    latest_eta_date = fields.Datetime(compute="_compute_latest_eta_date", store=True)
    burgtec_quote_reference = fields.Char(string="Burgtec Reference", compute="_compute_sale_ref", store=True)

    def unlink(self):
        for rec in self:
            if rec.quote_type == 'delivery_stage' and not self.env.user.has_group(
                    'quotation_type_customization.group_super_admin'):
                raise UserError(_('Only Super Admin can delete Delivery Stage quotations.'))

        for rec in self:
            if rec.quote_type == 'delivery_stage':
                rec.write({'state': 'cancel'})
                stage_number = False
                if not rec.system_revision:
                    stage_number = rec.burgtec_quote_reference.split('-')[-1].lstrip('0')
                if rec.system_revision:
                    stage_number = rec.new_sale_order_number.split('-')[-1].lstrip('0')

                if rec.purchase_order_id:
                    parent_po = rec.purchase_order_id

                    # child purchase orders/
                    if parent_po.child_purchase_order_ids:
                        for child_po in parent_po.child_purchase_order_ids:
                            child_pickings = self.env['stock.picking'].search([
                                ('origin', '=', child_po.name)
                            ])
                            for picking in child_pickings:
                                if picking.move_ids:
                                    picking.move_ids.write({'state': 'cancel'})
                                picking.write({'state': 'cancel'})

                        # Cancel and delete child POs
                        parent_po.child_purchase_order_ids.write({'state': 'cancel'})
                        parent_po.child_purchase_order_ids.unlink()

                    # Cancel and delete parent PO pickings using origin field
                    parent_pickings = self.env['stock.picking'].search([
                        ('origin', '=', parent_po.name)
                    ])
                    for picking in parent_pickings:
                        if picking.move_ids:
                            picking.move_ids.write({'state': 'cancel'})
                        picking.write({'state': 'cancel'})

                    # Cancel and delete parent PO
                    parent_po.write({'state': 'cancel'})
                    parent_po.unlink()

                # Project Quote and Planning Screen
                if rec.source_sale_order_id and rec.is_child_sale_order:
                    source_sale_order_id = int(rec.source_sale_order_id)
                    project_quote = self.env['sale.order'].browse(source_sale_order_id)

                    if project_quote and project_quote.planning_screen_id:
                        status_field_name = f'do_{stage_number}_status'
                        project_quote.planning_screen_id.write({
                            status_field_name: 'draft'
                        })
                        project_quote.child_quote_count -= 1

        return super().unlink()

    def change_sale_ref_and_series(self):
        current_user = self.env.user
        if not current_user.has_group('quotation_type_customization.group_planning_screen_admin'):
            raise UserError(_('Only the Planning Screen Admin Can modify the Quotation and Series Sequence!'))
        for rec in self:
            if rec.is_old_data:
                if not rec.hubspot_reference:
                    raise ValidationError("HubSpot Reference is missing. Cannot update quotation reference or series.")

                hubspot_first_6 = rec.hubspot_reference[:6]
                existing_quotes = self.env['sale.order'].search([
                    ('burgtec_quote_reference', '!=', False),
                    ('quote_type', '=', 'sales_quote'),
                    ('is_old_data', '=', True),
                    ('id', '!=', rec.id)
                ])
                # Check if first 6 digits match
                for quote in existing_quotes:
                    if quote.burgtec_quote_reference and len(quote.burgtec_quote_reference) >= 6:
                        burgtec_first_6 = quote.burgtec_quote_reference[:6]
                        if burgtec_first_6 == hubspot_first_6:
                            raise ValidationError(
                                f"A Quotation with similar Reference already exists: '{quote.name}'. "
                                f"Please use a different HubSpot Reference."
                            )

                # Set reference based on whether manual_rev is present
                if rec.manual_rev:
                    rec.burgtec_quote_reference = f"{rec.hubspot_reference}-{rec.manual_rev}"
                else:
                    rec.burgtec_quote_reference = rec.hubspot_reference

                # Extract the first character
                first_initial = rec.hubspot_reference[0]

                # Validate it’s a digit between 1–9
                if first_initial.isdigit() and first_initial in '123456789':
                    series = self.env['sale.order.series'].search([
                        ('sequence', '=', int(first_initial))
                    ], limit=1)

                    if series:
                        rec.series_sequence_id = series.id
                    else:
                        raise ValidationError(f"No series found for sequence '{first_initial}'.")
                else:
                    raise ValidationError("HubSpot Reference must start with a digit from 1 to 9.")

    def action_set_the_sequence_as_hubspot_initial(self):
        for all_quote in self:
            if (
                    all_quote.is_old_data
                    and all_quote.hubspot_reference
            ):
                first_initial = all_quote.hubspot_reference[0]

                # Store only the first 6 characters of the hubspot_reference
                all_quote.series_from_hubspot_ref = all_quote.hubspot_reference[:6]

                # Check if the first initial is a digit between 1–9
                if first_initial.isdigit() and first_initial in '123456789':
                    series = self.env['sale.order.series'].search([
                        ('sequence', '=', int(first_initial))
                    ], limit=1)

                    if series:
                        all_quote.series_sequence_id = series.id

    def copy(self, default=None):
        current_user = self.env.user
        self.ensure_one()
        default = dict(default or {})
        if not self.burgtec_quote_reference:
            raise ValidationError(_("Kindly Generate the Sale Order Reference Number."))
        if self.quote_type == 'project_quote':
            if not current_user.has_group('quotation_type_customization.group_planning_screen_admin'):
                raise UserError(_('Only a Planning Screen Admin can duplicate a Project Quote.'))
            default['quote_type'] = 'delivery_stage'
        if self.quote_type == 'delivery_stage':
            raise ValidationError('You can not duplicate the Delivery Stage')
        if self.child_sale_order_ids:
            raise ValidationError(_('You can not Duplicate a Sale Quote if the Project is Already Created.'))
        if not self.child_sale_order_ids:
            odoo_reference_on_sales_quote = self.name.split("-")[0].strip()
            project_quotes = self.env['sale.order'].search([
                ('quote_type', '=', 'project_quote'),
                ('name', 'ilike', odoo_reference_on_sales_quote)
            ])
            if project_quotes:
                raise ValidationError(
                    _("You cannot duplicate a Sale Quote if a Project has already been created for any of its Revisions."))
        return super(SaleOrderExt, self).copy(default)

    def action_confirm(self):
        """Override action_confirm to set purchase line prices to zero and assign purchase order"""
        if not self.bom_component_id:
            raise UserError(_("Kindly set and save the Components before confirming!"))
        res = super(SaleOrderExt, self).action_confirm()
        return res

    def write(self, vals):
        res = super(SaleOrderExt, self).write(vals)
        for order in self:
            if vals.get("quote_type") == "project_quote":
                odoo_reference_on_project_quote = order.name.split("-")[0]
                # Check if another project quote with same reference already exists
                related_project_quotes = self.env['sale.order'].search([
                    ('quote_type', '=', 'project_quote'),
                    ('name', 'ilike', odoo_reference_on_project_quote),
                    ('id', '!=', order.id)
                ], limit=1)
                if related_project_quotes:
                    raise ValidationError(
                        _("You can only generate one Project from a Sale Quote.")
                    )
            elif vals.get('order_line'):
                lines_list = vals['order_line']
                execute = False
                keys = []
                ids = False
                sequences = False
                if len(lines_list) == 1:
                    ids = [item[1] for item in lines_list if item[0] == 1]
                if len(lines_list) > 1:
                    ids = [item[1] for item in lines_list if item[0] == 1]
                if isinstance(lines_list, list):
                    if all(isinstance(item, tuple) for item in lines_list):
                        if not (lines_list[0][
                                    0] == 4):  # Should execute when adding products only. Not when adding Groups and codes.
                            execute = True
                            sequences = [item[2] for item in lines_list if item[0] == 0]
                    if all(isinstance(item, list) for item in lines_list):
                        if lines_list[0][0] == 1:
                            keys = lines_list[0][2].keys()
                            if 'name' in keys or 'custom_product_name' in keys or 'image_128' in keys:
                                return
                        if not (lines_list[0][0] == 4 or lines_list[0][
                            0] == 0):  # Should execute when adding products only. Not when adding Groups and codes.
                            execute = True
                bom_obj = self.bom_component_id
                if execute and bom_obj:
                    if ids:
                        bom_obj.update_component_lines(ids)
                    if sequences:
                        bom_obj.update_component_lines(lines_vals=sequences)
        return res


    def action_generate_sale_order_number(self):
        for record in self:
            if not record.series_sequence_id:
                raise UserError("Please select a Sequence Number before generating the sale order number.")
            series_record = record.series_sequence_id
            series_starting_value = series_record.starting_value
            series_ending_value = series_record.ending_value
            if series_starting_value > series_ending_value:
                raise UserError("Sale Order Series has Ended.")
            # Get all existing first 6 digits in a set for faster lookup
            existing_quotes = self.env['sale.order'].search([
                ('burgtec_quote_reference', '!=', False),
                ('quote_type', '=', 'sales_quote'),
                ('is_old_data', '=', True),
                ('id', '!=', record.id)
            ])
            # Build set of existing first 6 digits using filtered and mapped
            existing_first_6_set = set(
                existing_quotes.filtered(
                    lambda q: q.burgtec_quote_reference and len(q.burgtec_quote_reference) >= 6
                ).mapped(lambda q: q.burgtec_quote_reference[:6])
            )
            # Keep checking until we find an available number
            while series_starting_value <= series_ending_value:
                current_reference = str(series_starting_value)
                current_first_6 = current_reference[:6]
                if current_first_6 not in existing_first_6_set:
                    # This number is available, assign it
                    record.new_sale_order_number = series_starting_value
                    record.burgtec_quote_reference = current_reference
                    series_record.starting_value = series_starting_value + 1
                    break
                else:
                    # This number is taken, try next one
                    series_starting_value += 1
            else:
                raise UserError("Sale Order Series has Ended. No available numbers found in the range.")

    @api.depends('new_sale_order_number', 'manual_rev', 'is_old_data')
    def _compute_sale_ref(self):
        for record in self:
            if record.quote_type != 'project_quote':
                if record.is_old_data:
                    # Use hubspot_reference logic
                    if record.hubspot_reference and not record.manual_rev:
                        record.burgtec_quote_reference = record.hubspot_reference
                    elif record.manual_rev and not record.hubspot_reference:
                        record.burgtec_quote_reference = record.manual_rev
                    elif record.hubspot_reference and record.manual_rev:
                        record.burgtec_quote_reference = f"{record.hubspot_reference}-{record.manual_rev}"
                    else:
                        record.burgtec_quote_reference = False
                else:
                    # Use new_sale_order_number logic
                    if record.new_sale_order_number and not record.manual_rev:
                        record.burgtec_quote_reference = record.new_sale_order_number
                    elif record.manual_rev and not record.new_sale_order_number:
                        record.burgtec_quote_reference = record.manual_rev
                    elif record.new_sale_order_number and record.manual_rev:
                        record.burgtec_quote_reference = f"{record.new_sale_order_number}-{record.manual_rev}"
                    else:
                        record.burgtec_quote_reference = False

    def action_mark_as_quoation_sent(self):
        for record in self:
            if not record.burgtec_quote_reference:
                raise UserError(_('Kindly Generate the Sale Order Reference Number.'))
            if not record.bom_component_id:
                raise UserError(_('Kindly set and save Bom Components before Quotation Sent.'))
        return super(SaleOrderExt, self).action_mark_as_quoation_sent()

    def create_new_delivery_stage(self):
        for record in self:
            if record.quote_type == 'project_quote':
                raise UserError(_('You are not allowed to create Project from Project!'))

            if record.state == 'draft':
                raise UserError(_('Project Can Only Be Created In Quotation Sent State.'))

            if self.quote_type == 'sales_quote':
                odoo_reference_on_sales_quote = self.name.split("-")[0].strip()
                project_quotes = self.env['sale.order'].search([
                    ('quote_type', '=', 'project_quote'),
                    ('name', 'ilike', odoo_reference_on_sales_quote)
                ])
                # projects_quotations = self.child_sale_order_ids.filtered(lambda so: so.quote_type == 'project_quote')
                if project_quotes:
                    raise ValidationError(
                        _("You Can Only Generate One Project From Sale Quote"))

            # Now set few things in this quotation to make it different from all others.
            # parent quote
            child_quote = False
            updated_count = record.reference_count + 1
            # stage_ref = f"{self.burgtec_quote_reference}-001"
            stage_ref = f"{self.burgtec_quote_reference[:6]}"
            sale_write_vals = {
                'is_sales_quote': True,
                'is_parent_sale_order': True,
                'quote_type': 'sales_quote',
                'reference_count': updated_count,
                'delivery_stage_reference_number': f"D{updated_count}",
                'state': 'sent',
                # 'new_sale_order_number': stage_ref,

            }
            res = record.write(sale_write_vals)
            child_sale_order_vals = {
                'burgtec_quote_reference': stage_ref,
                'name': f"{record.name}",
                'quote_type': 'project_quote',
                'is_project_quote': True,
                'source_sale_order_name': self.name,
                'source_sale_order_id': self.id,
                'is_child_sale_order': True,
                'state': 'quotation_confirmed',
                'is_old_data': False,
                'system_revision': record.system_revision,
            }
            if res:
                child_quote = record.with_context(copied_from_new_delivery_stage=True).copy()
                child_quote.write(
                    child_sale_order_vals
                )
                record.update(
                    {
                        'child_sale_order_ids': [(4, child_quote.id)],
                    }
                )
                return child_quote.id

    def _prepare_invoice(self):
        values = super()._prepare_invoice()
        existing_invoices = self.env['account.move'].search([
            ('invoice_origin', '=', self.name),
            ('move_type', '=', 'out_invoice')
        ])
        burgtec_quote_reference = self.burgtec_quote_reference[:6]

        # hubspot_reference = self.hubspot_reference
        invoice_count = len(existing_invoices) + 1
        values['burgtec_invoice_reference'] = f"INV-{burgtec_quote_reference}-{invoice_count:02d}"
        return values

    @api.depends('order_line.invoice_lines', 'down_payment_order_line_ids.invoice_lines')
    def _get_invoiced(self):
        # The invoice_ids are obtained thanks to the invoice lines of the SO
        # lines, and we also search for possible refunds created directly from
        # existing invoices. This is necessary since such a refund is not
        # directly linked to the SO.
        for order in self:
            invoices = order.order_line.invoice_lines.move_id.filtered(
                lambda r: r.move_type in ('out_invoice', 'out_refund'))
            dp_invoices = order.down_payment_order_line_ids.invoice_lines.move_id.filtered(
                lambda r: r.move_type in ('out_invoice', 'out_refund'))

            # Combine both invoice sets using the | (union) operator
            order.invoice_ids = invoices | dp_invoices
            order.invoice_count = len(order.invoice_ids)

    @api.depends('order_line.amount_invoiced', 'down_payment_order_line_ids.amount_invoiced')
    def _compute_amount_invoiced(self):
        for order in self:
            order.amount_invoiced = sum(order.down_payment_order_line_ids.mapped('amount_invoiced'))

    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        down_payment_line_ids = []
        invoiceable_line_ids = []
        pending_section = None
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        # down_payment_line = self.down_payment_order_line_ids
        order_lines = self.env['sale.order.line'].sudo().search([('order_id', '=', self.id)])

        # if down_payment_line:
        #     for dp in down_payment_line:
        #         if dp.id not in down_payment_line_ids:
        #             down_payment_line_ids.append(dp.id)

        for line in order_lines:
            if line.display_type == 'line_section':
                # Only invoice the section if one of its lines is invoiceable
                pending_section = line
                continue
            if line.display_type != 'line_note' and float_is_zero(line.qty_to_invoice, precision_digits=precision):
                continue
            if line.qty_to_invoice > 0 or (line.qty_to_invoice < 0 and final) or line.display_type == 'line_note':
                if line.is_downpayment:
                    # Keep down payment lines separately, to put them together
                    # at the end of the invoice, in a specific dedicated section.
                    down_payment_line_ids.append(line.id)
                    continue
                if pending_section:
                    invoiceable_line_ids.append(pending_section.id)
                    pending_section = None
                invoiceable_line_ids.append(line.id)

        return self.env['sale.order.line'].browse(invoiceable_line_ids + down_payment_line_ids)

    @api.depends('state', 'order_line.invoice_status', 'quote_type')
    def _compute_invoice_status(self):
        """
        Compute the invoice status of a SO. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
        invoice. This is also the default value if the conditions of no other status is met.
        - to invoice: if any SO line is 'to invoice', the whole SO is 'to invoice'
        - invoiced: if all SO lines are invoiced, the SO is invoiced.
        - upselling: if all SO lines are invoiced or upselling, the status is upselling.
        """
        # Separate project quotes from regular orders
        project_quote_orders = self.filtered(lambda so: so.quote_type == 'project_quote')
        regular_orders = self - project_quote_orders

        # Handle project quotes separately
        if project_quote_orders:
            lines_domain = [('is_downpayment', '=', False), ('display_type', '=', False)]
            line_invoice_status_all = [
                (order.id, invoice_status)
                for order, invoice_status in self.env['sale.order.line']._read_group(
                    lines_domain + [('order_id', 'in', project_quote_orders.ids)],
                    ['order_id', 'invoice_status']
                )
            ]

            for order in project_quote_orders:
                line_invoice_status = [d[1] for d in line_invoice_status_all if d[0] == order.id]

                if any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                    if any(invoice_status == 'no' for invoice_status in line_invoice_status):
                        invoiceable_domain = lines_domain + [('invoice_status', '=', 'to invoice')]
                        invoiceable_lines = order.order_line.filtered_domain(invoiceable_domain)
                        special_lines = invoiceable_lines.filtered(
                            lambda sol: not sol._can_be_invoiced_alone()
                        )
                        if invoiceable_lines == special_lines:
                            order.invoice_status = 'to invoice'  # Still 'to invoice' for project quotes
                        else:
                            order.invoice_status = 'to invoice'
                    else:
                        order.invoice_status = 'to invoice'
                elif line_invoice_status and all(
                        invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                    order.invoice_status = 'invoiced'
                elif line_invoice_status and all(
                        invoice_status in ('invoiced', 'upselling') for invoice_status in line_invoice_status):
                    order.invoice_status = 'upselling'
                else:
                    order.invoice_status = 'to invoice'  # Default to 'to invoice' for project quotes

        # Original logic for regular orders
        confirmed_orders = regular_orders.filtered(lambda so: so.state == 'sale')
        (regular_orders - confirmed_orders).invoice_status = 'no'
        if not confirmed_orders:
            return

        lines_domain = [('is_downpayment', '=', False), ('display_type', '=', False)]
        line_invoice_status_all = [
            (order.id, invoice_status)
            for order, invoice_status in self.env['sale.order.line']._read_group(
                lines_domain + [('order_id', 'in', confirmed_orders.ids)],
                ['order_id', 'invoice_status']
            )
        ]

        for order in confirmed_orders:
            line_invoice_status = [d[1] for d in line_invoice_status_all if d[0] == order.id]
            if order.state != 'sale':
                order.invoice_status = 'no'
            elif any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                if any(invoice_status == 'no' for invoice_status in line_invoice_status):
                    # If only discount/delivery/promotion lines can be invoiced, the SO should not
                    # be invoiceable.
                    invoiceable_domain = lines_domain + [('invoice_status', '=', 'to invoice')]
                    invoiceable_lines = order.order_line.filtered_domain(invoiceable_domain)
                    special_lines = invoiceable_lines.filtered(
                        lambda sol: not sol._can_be_invoiced_alone()
                    )
                    if invoiceable_lines == special_lines:
                        order.invoice_status = 'no'
                    else:
                        order.invoice_status = 'to invoice'
                else:
                    order.invoice_status = 'to invoice'
            elif line_invoice_status and all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                order.invoice_status = 'invoiced'
            elif line_invoice_status and all(
                    invoice_status in ('invoiced', 'upselling') for invoice_status in line_invoice_status):
                order.invoice_status = 'upselling'
            else:
                order.invoice_status = 'no'

    def _force_compute_invoice_status_for_order_and_order_line(self):
        # Compute all order lines at once (more efficient)
        if self.mapped('order_line'):
            self.mapped('order_line')._compute_invoice_status()

        # Then compute all orders
        self._compute_invoice_status()

    def _force_compute_qty_to_invoice(self):
        # Compute all order lines at once (more efficient)
        if self.mapped('order_line'):
            self.mapped('order_line')._compute_qty_to_invoice()

    def calculate_delivery_stage_costs(self):
        for record in self:
            if record.planning_screen_id:
                record.planning_screen_id._compute_delivery_stage_cost_lines()

    # @api.depends('purchase_order_id.child_purchase_order_ids', 'purchase_order_id.child_purchase_order_ids.burgtec_po_status')
    def _compute_burgtec_po_status(self):
        for record in self:
            purchase_order_obj = record.purchase_order_id
            child_po_obj = record.purchase_order_id.child_purchase_order_ids
            result = False
            ele_list = []
            if not purchase_order_obj:
                record.burgtec_po_status = False
            if purchase_order_obj:
                if not child_po_obj:
                    record.burgtec_po_status = False
                if child_po_obj:
                    def all_same_all(items):
                        # Returns True for an empty list
                        return all(x == items[0] for x in items) if items else True

                    ele_list = child_po_obj.mapped('burgtec_po_status')
                    result = all_same_all(ele_list)
                    if not result:
                        record.burgtec_po_status = False
                    if result:
                        record.burgtec_po_status = ele_list[-1]

    @api.depends('purchase_order_id.child_purchase_order_ids.date_planned')
    def _compute_latest_eta_date(self):
        child_po_to_exclude = ('Burgtec Delivery', 'Burgtec Installation')
        for record in self:
            child_pos = record.purchase_order_id.child_purchase_order_ids
            relevant_pos = child_pos.filtered(lambda po: po.partner_id.name not in child_po_to_exclude)
            if relevant_pos and all(relevant_pos.mapped('date_planned')):
                record.latest_eta_date = max(relevant_pos.mapped('date_planned'))
            else:
                record.latest_eta_date = False



    def action_project_wise_delivery_report(self):
        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Project_wise_delivery_stage_breakdown")

        # ==========================
        # Formats
        # ==========================

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 18,
            'bg_color': '#1F4E78',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
        })

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })

        cell_format = workbook.add_format({
            'font_size': 13,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })

        currency_format = workbook.add_format({
            'font_size': 13,
            'border': 1,
            'num_format': '$#,##0.00',
            'align': 'center',
            'valign': 'vcenter',
        })

        # ==========================
        # Sheet Size
        # ==========================

        sheet.set_default_row(30)

        sheet.set_column('A:A', 15)  # Project
        sheet.set_column('B:B', 20)  # Delivery Stage
        sheet.set_column('C:C', 20)  # Stage values
        sheet.set_column('D:D', 20)  # Stage values
        sheet.set_column('E:E', 35)  # Stage values
        sheet.set_column('F:F', 20)  # Stage values
        sheet.set_column('G:G', 35)  # Child PO
        sheet.set_column('H:H', 35)  # Child PO Total

        row = 0

        # ==========================
        # Title
        # ==========================

        sheet.set_row(row, 40)

        sheet.merge_range(
            row,
            0,
            row,
            7,
            "Project Wise Delivery Stage Breakdown",
            title_format
        )

        row += 2

        # ==========================
        # Headers
        # ==========================

        headers = [
            "Project",
            "Delivery Stage",
            "DS Total",
            "DS GP$",
            "Total Parent Live Unit Cost",
            "Total Child PO",
            "Child Purchase Order",
            "Child Purchase Order Total",
        ]

        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)

        sheet.set_row(row, 35)

        row += 1

        # ==========================
        # Data
        # ==========================

        for project in self:

            project_written = False

            for stage in project.child_sale_order_ids.sorted(
                    key=lambda x: x.id
            ):

                stage_written = False

                child_pos = stage.purchase_order_id.child_purchase_order_ids.sorted(
                    key=lambda x: x.id
                )

                # Total of all child purchase orders
                child_po_total = sum(
                    child_pos.mapped('amount_total')
                )

                for po in child_pos:

                    # ==========================
                    # Project
                    # ==========================

                    if not project_written:

                        sheet.write(
                            row,
                            0,
                            project.burgtec_quote_reference,
                            cell_format
                        )

                        project_written = True

                    else:

                        sheet.write(
                            row,
                            0,
                            "",
                            cell_format
                        )

                    # ==========================
                    # Delivery Stage
                    # ==========================

                    if not stage_written:

                        sheet.write(
                            row,
                            1,
                            stage.burgtec_quote_reference,
                            cell_format
                        )

                        sheet.write(
                            row,
                            2,
                            stage.amount_untaxed,
                            currency_format
                        )

                        sheet.write(
                            row,
                            3,
                            stage.live_unit_cost,
                            currency_format
                        )

                        sheet.write(
                            row,
                            4,
                            stage.bom_component_id.total_parent_live_unit_cost
                            if stage.bom_component_id
                            else 0,
                            currency_format
                        )

                        sheet.write(
                            row,
                            5,
                            child_po_total,
                            currency_format
                        )

                        stage_written = True

                    else:

                        sheet.write(row, 1, "", cell_format)
                        sheet.write(row, 2, "", currency_format)
                        sheet.write(row, 3, "", currency_format)
                        sheet.write(row, 4, "", currency_format)
                        sheet.write(row, 5, "", currency_format)

                    # ==========================
                    # Child Purchase Order
                    # ==========================

                    sheet.write(
                        row,
                        6,
                        po.burgtec_purchase_reference,
                        cell_format
                    )

                    sheet.write(
                        row,
                        7,
                        po.amount_total,
                        currency_format
                    )

                    row += 1
                if child_pos:
                    row += 1

                # ==========================
                # Stage without Child PO
                # ==========================

                if not child_pos:

                    if not project_written:

                        sheet.write(
                            row,
                            0,
                            project.burgtec_quote_reference,
                            cell_format
                        )

                        project_written = True

                    else:

                        sheet.write(
                            row,
                            0,
                            "",
                            cell_format
                        )

                    sheet.write(
                        row,
                        1,
                        stage.burgtec_quote_reference,
                        cell_format
                    )

                    sheet.write(
                        row,
                        2,
                        stage.amount_untaxed,
                        currency_format
                    )

                    sheet.write(
                        row,
                        3,
                        stage.live_unit_cost,
                        currency_format
                    )

                    sheet.write(
                        row,
                        4,
                        stage.bom_component_id.total_parent_live_unit_cost
                        if stage.bom_component_id
                        else 0,
                        currency_format
                    )

                    sheet.write(
                        row,
                        5,
                        0,
                        currency_format
                    )

                    row += 2

        # ==========================
        # Save Workbook
        # ==========================

        workbook.close()

        output.seek(0)

        attachment = self.env['ir.attachment'].create({
            'name': 'Project_Wise_Delivery_Report.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': (
                'application/vnd.openxmlformats-officedocument'
                '.spreadsheetml.sheet'
            ),
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}',
            'target': 'new',
        }



class SaleOrderLineExt(models.Model):
    _inherit = 'sale.order.line'

    product_uom = fields.Many2one(comodel_name='uom.uom', string="Unit of Measure", readonly=True)
    is_product_fully_approved = fields.Boolean(
        string='Is Product Fully Approved ?',
        default=False,
        copy=False,
        help="Sale order Line becomes readonly when Product  is fully approved on Planning screen")

    origin_planning_screen_line = fields.Char('Origin Planning Screen Line',
                                              help="Sale order Line is created from this Planning Screen line")

    @api.depends('is_product_fully_approved')
    def _compute_product_uom_readonly(self):
        for line in self:
            # line.ids checks whether it's a new record not yet saved
            line.product_uom_readonly = line.ids and line.is_product_fully_approved

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'state')
    def _compute_qty_to_invoice(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        For combo product lines, first compute all other lines, and then set quantity to invoice
        only if at least one of its combo item lines is invoiceable.
        """
        combo_lines = []
        for line in self:
            if not line.display_type:
                if line.product_id.type == 'combo':
                    combo_lines.append(line)
                elif line.product_id.invoice_policy == 'order':
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
            else:
                line.qty_to_invoice = 0
        for combo_line in combo_lines:
            if any(
                    line.combo_item_id and line.qty_to_invoice
                    for line in combo_line.linked_line_ids
            ):
                combo_line.qty_to_invoice = combo_line.product_uom_qty - combo_line.qty_invoiced
            else:
                combo_line.qty_to_invoice = 0

    def unlink(self):
        for rec in self:
            if rec.is_product_fully_approved:
                raise UserError(_("You cannot delete a sale order line if the product is approved"))
        return super(SaleOrderLineExt, self).unlink()

    @api.model_create_multi
    def create(self, vals_list):
        res = super(SaleOrderLineExt, self).create(vals_list)
        for sol in res:
            if not sol.is_downpayment:
                if not sol.order_id.is_old_data and sol.order_id.planning_screen_id and not sol.display_type:
                    vals = {
                        'display_type': sol.display_type or False,
                        'name': sol.name if sol.display_type else False,
                        'product_reference': sol.product_template_id.default_code if sol.product_template_id else False,
                        'product_id': sol.product_template_id.id if sol.product_id else False,
                        'quantity': sol.product_uom_qty if sol.product_template_id else 0,
                        'order_line_id': sol.id,
                        'origin_order_line': sol.old_order_line if sol.old_order_line else False,
                        'item': len(sol.order_id.planning_screen_id.line_ids) + 1,
                        'do_stage_1': 0,
                    }
                    sol.order_id.planning_screen_id.line_ids = [Command.create(vals)]
                    # sol.order_id.bom_component_id.update_component_lines()
                if sol.order_id.is_old_data and sol.order_id.planning_screen_id and not sol.display_type:
                    vals = {
                        'display_type': sol.display_type or False,
                        'name': sol.name if sol.display_type else False,
                        'product_reference': sol.product_template_id.default_code if sol.product_template_id else False,
                        'product_id': sol.product_template_id.id if sol.product_id else False,
                        'quantity': sol.product_uom_qty if sol.product_template_id else 0,
                        'order_line_id': sol.id,
                        'origin_order_line': sol.old_order_line if sol.old_order_line else False,
                        'item': len(sol.order_id.planning_screen_id.line_ids) + 1,
                        'do_stage_1': 0,
                    }
                    sol.order_id.planning_screen_id.line_ids = [Command.create(vals)]
                    # sol.order_id.bom_component_id.update_component_lines()
                if sol.order_id.split_do_id and sol.order_id.is_old_data:
                    vals = {
                        'display_type': sol.display_type or False,
                        'name': sol.name if sol.display_type else False,
                        'product_reference': sol.product_template_id.default_code if sol.product_template_id else False,
                        'product_id': sol.product_template_id.id if sol.product_id else False,
                        'quantity': sol.product_uom_qty if sol.product_template_id else 0,
                        'order_line_id': sol.id,
                        'origin_order_line': sol.old_order_line if sol.old_order_line else False,
                        'do_stage_1': sol.product_uom_qty if sol.product_template_id else 0,
                    }
                    sol.order_id.split_do_id.line_ids = [Command.create(vals)]
                    # sol.order_id.bom_component_id.update_component_lines()
                if not sol.order_id.split_do_id and sol.order_id.is_old_data:
                    vals = {
                        'display_type': sol.display_type or False,
                        'name': sol.name if sol.display_type else False,
                        'product_reference': sol.product_template_id.default_code if sol.product_template_id else False,
                        'product_id': sol.product_template_id.id if sol.product_id else False,
                        'quantity': sol.product_uom_qty if sol.product_template_id else 0,
                        'order_line_id': sol.id,
                        'origin_order_line': sol.old_order_line if sol.old_order_line else False,
                        'do_stage_1': sol.product_uom_qty if sol.product_template_id else 0,
                    }
                    sol.order_id.split_do_id.line_ids = [Command.create(vals)]
                    # sol.order_id.bom_component_id.update_component_lines()
        return res

    def action_open_copy_wizard(self):
        if self.order_id.quote_type == 'delivery_stage' and not self.order_id.is_old_data:
            return None
        if self.is_product_fully_approved:
            return None
        return super().action_open_copy_wizard()

    # Called by action button to show a wizard
    def action_show_wizard_to_add_code(self):
        if self.order_id.quote_type == 'delivery_stage' and not self.order_id.is_old_data:
            return None
        return super().action_show_wizard_to_add_code()

    def action_show_wizard_to_add_product(self):
        # Don't include res_id key for wizards.
        if self.order_id.quote_type == 'delivery_stage' and not self.order_id.is_old_data:
            return None
        return super().action_show_wizard_to_add_product()

    def action_show_wizard_to_swap_groups(self):
        if self.order_id.quote_type == 'delivery_stage' and not self.order_id.is_old_data:
            return None
        return super().action_show_wizard_to_swap_groups()

    def action_show_wizard_to_swap_codes(self):
        if self.order_id.quote_type == 'delivery_stage' and not self.order_id.is_old_data:
            return None
        return super().action_show_wizard_to_swap_codes()

    @api.depends('order_id')
    def _set_unique_identifiers(self):
        set_value = 1
        group_lines = self.order_id.order_line.sorted(lambda o: o.sequence).filtered(
            lambda l: l.display_type == 'line_section')
        code_lines = self.order_id.order_line.sorted(lambda o: o.sequence).filtered(
            lambda l: l.display_type == 'line_note')
        product_lines = self.order_id.order_line.sorted(lambda o: o.sequence).filtered(lambda l: not l.display_type)
        down_payment_lines = self.order_id.down_payment_order_line_ids

        for line in group_lines:
            line.product_identifier = set_value
            set_value += 1
        set_value = 1

        for line in code_lines:
            line.product_identifier = set_value
            set_value += 1
        set_value = 1

        for line in product_lines:
            line.product_identifier = set_value
            set_value += 1
        set_value = 1

        if down_payment_lines:
            for line in down_payment_lines:
                line.product_identifier = set_value
                set_value += 1

    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced', 'order_id.quote_type')
    def _compute_invoice_status(self):
        """
        Compute the invoice status of a SO line. Possible statuses:
        - no: if the SO is not in status 'sale', we consider that there is nothing to
        invoice. This is also the default value if the conditions of no other status is met.
        - to invoice: we refer to the quantity to invoice of the line. Refer to method
        `_compute_qty_to_invoice()` for more information on how this quantity is calculated.
        - upselling: this is possible only for a product invoiced on ordered quantities for which
        we delivered more than expected. The could arise if, for example, a project took more
        time than expected but we decided not to invoice the extra cost to the client. This
        occurs only in state 'sale', the upselling opportunity is removed from the list.
        - invoiced: the quantity invoiced is larger or equal to the quantity ordered.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            # for project_quote type
            if line.order_id.quote_type == 'project_quote':
                if line.is_downpayment and line.untaxed_amount_to_invoice == 0:
                    line.invoice_status = 'invoiced'
                elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    line.invoice_status = 'to invoice'
                elif line.product_id.invoice_policy == 'order' and \
                        line.product_uom_qty >= 0.0 and \
                        float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1:
                    line.invoice_status = 'upselling'
                elif float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) >= 0:
                    line.invoice_status = 'invoiced'
                else:
                    line.invoice_status = 'to invoice'  # Default to 'to invoice' for project quotes
            # Original logic for non-project quotes
            elif line.state != 'sale':
                line.invoice_status = 'no'
            elif line.is_downpayment and line.untaxed_amount_to_invoice == 0:
                line.invoice_status = 'invoiced'
            elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                line.invoice_status = 'to invoice'
            elif line.state == 'sale' and line.product_id.invoice_policy == 'order' and \
                    line.product_uom_qty >= 0.0 and \
                    float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1:
                line.invoice_status = 'upselling'
            elif float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) >= 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'

    # When User Changes Product From Frontend Directly from the field this will ensure that no previous bom component lines linked with this sale order line are deleted.
    def write(self, vals):
        bom = False
        bom_lines = False
        if vals.get("product_id"):
            bom = self.order_id.bom_component_id
            bom_lines = bom.component_line_ids
            if bom_lines:
                bom_lines.filtered(lambda bl: bl.order_line_id.id == self.id).with_context(force_delete=True).unlink()
        res = super(SaleOrderLineExt, self).write(vals)
        return res
