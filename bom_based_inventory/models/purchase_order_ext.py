from odoo import fields, models, _, api
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero


class PurchaseOrderExt(models.Model):
    _inherit = 'purchase.order'

    builder_trend_po = fields.Char('Buildertrend PO #', copy=False)
    delivery_stage = fields.Char('Delivery Stage #', copy=False)
    tag = fields.Selection([('child', 'Child PO'),
                            ('parent', 'Parent PO')], readonly=True)
    burgtec_purchase_reference = fields.Char(string="Burgtec Reference", compute="_compute_po_ref", store=True)
    is_builder_trend = fields.Boolean('Is Builder Trend ?', default=False, copy=False)
    child_po_count = fields.Integer()
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
    ], default="draft_to_approve", string="Burgtec PO Status")

    delivery_stage_link = fields.Char()
    onedrive_po_folder_link = fields.Char()
    wh_rack_location = fields.Char(string='WH Rack Location')
    hubspot_reference = fields.Char('Hubspot Reference')
    is_old_data = fields.Boolean('Is Old Data ?', default=False)

    is_not_readonly_for_group = fields.Boolean(
        string='Is Not Readonly for Specific Group',
        compute='_compute_is_not_readonly_for_group'
    )

    required_arrival_date = fields.Date(tracking=True)

    # This Over ride was removing email cc as well. Followers are already handeled with _notify_get_recipients so no need fot this overwrite.

    # def action_rfq_send(self):
    #     result = super().action_rfq_send()
    #     if "context" in result:
    #         result["context"]["default_partner_ids"] = self.partner_id.ids
    #     return result

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        recipients = super()._notify_get_recipients(message, msg_vals, **kwargs)

        # Only filter when sending from the email wizard
        if not self.env.context.get("mark_rfq_as_sent"):
            return recipients

        # These are the partners explicitly on the message/wizard
        explicit_pids = set(
            msg_vals.get("partner_ids", []) if msg_vals
            else message.sudo().partner_ids.ids
        )

        follower_pids = set(self.message_follower_ids.mapped("partner_id").ids)

        return [
            r for r in recipients
            if r["id"] not in follower_pids  # not a follower, keep
               or r["id"] in explicit_pids  # follower but explicitly added by user, keep
        ]

    def _compute_is_not_readonly_for_group(self):
        for record in self:
            # Check if the current user has the specific group
            if self.env.user.has_group('bom_based_inventory.group_purchase_order_line_edit'):
                record.is_not_readonly_for_group = False
            else:
                record.is_not_readonly_for_group = True

    def action_mark_old_data(self):
        for order in self:
            order.write({
                'is_old_data': True
            })

    def action_mark_builder_trend(self):
        for order in self:
            order.write({
                'is_builder_trend': True
            })

    @api.depends('delivery_stage', 'child_po_count')
    def _compute_po_ref(self):
        for record in self:
            if record.delivery_stage and record.tag == 'parent':
                record.burgtec_purchase_reference = f"P{record.delivery_stage}"
            elif record.delivery_stage and record.tag == 'child':
                # record.burgtec_purchase_reference = f"P{record.delivery_stage}-{record.child_po_count}"
                record.burgtec_purchase_reference = f"PO-{record.delivery_stage}-{str(record.child_po_count).zfill(2)}"
            else:
                record.burgtec_purchase_reference = False

    def action_create_invoice(self):
        """Create the invoice associated to the PO.
        """
        if self.tag == 'parent':
            raise UserError(_("You CANNOT CREATE THE BILL FOR PARENT PURCHASE ORDER"))
        res = super(PurchaseOrderExt, self).action_create_invoice()
        account_move = self.env['account.move'].sudo().browse(res['res_id'])
        if account_move:
            child_purchase_ref = self.burgtec_purchase_reference
            desire_ref_for_bill = child_purchase_ref.split('-', 1)[1]
            formatted_number = str(self.invoice_count).zfill(2)
            burgtec_bill_reference = f"BILL-{desire_ref_for_bill}-{formatted_number}"
            # burgtec_bill_reference = f"BILL-{desire_ref_for_bill}-01"
            account_move.write({'burgtec_bill_reference': burgtec_bill_reference})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super(PurchaseOrderExt, self).create(vals_list)
        for record in res:
            if record:
                sale_obj = self.env['sale.order'].sudo().search([('name', '=', record.origin)])
                dropship_obj = self.env['stock.picking'].sudo().search([('name', '=', record.origin)])

                # If parent PO IT WILL HAVE SALE OBJ
                if sale_obj:
                    for order_line in sale_obj.order_line.filtered(lambda s: not s.display_type):
                        order_line.fill_component_html()
                # If Child POS It will have dropship as origin
                if dropship_obj:
                    for order_line in dropship_obj.sale_id.order_line.filtered(lambda s: not s.display_type):
                        order_line.fill_component_html()

        return res

    def button_confirm(self):
        # if not self.builder_trend_po:
        #     raise UserError(_('Buildertrend PO # is required to proceed!'))
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue
            order = order.with_context(
                purchase_order_id=order.id,
                default_purchase_id=order.id,
            )
            order.order_line._validate_analytic_distribution()
            # order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True

    def write(self, vals):
        res = super(PurchaseOrderExt, self).write(vals)
        for record in self:
            if 'date_planned' in vals:
                sale_obj = self.env['sale.order'].sudo().search([('name', '=', record.origin)])
                dropship_obj = self.env['stock.picking'].sudo().search([('name', '=', record.origin)])

                # If parent PO IT WILL HAVE SALE OBJ
                if sale_obj:
                    for order_line in sale_obj.order_line.filtered(lambda s: not s.display_type):
                        order_line.fill_component_html()
                # If Child POS It will have dropship as origin
                if dropship_obj:
                    for order_line in dropship_obj.sale_id.order_line.filtered(lambda s: not s.display_type):
                        order_line.fill_component_html()
            if 'state' in vals:
                sale_obj = self.env['sale.order'].sudo().search([('name', '=', record.origin)])
                dropship_obj = self.env['stock.picking'].sudo().search([('name', '=', record.origin)])

                # If parent PO IT WILL HAVE SALE OBJ
                if sale_obj:
                    for order_line in sale_obj.order_line.filtered(lambda s: not s.display_type):
                        order_line.fill_component_html()
                # If Child POS It will have dropship as origin
                if dropship_obj:
                    for order_line in dropship_obj.sale_id.order_line.filtered(lambda s: not s.display_type):
                        order_line.fill_component_html()

        return res

    def open_record_in_new_window(self):
        root_url = request.httprequest.url_root
        record_url = f"{root_url}/odoo/purchase/{self.id}"
        return {
            'type': 'ir.actions.act_url',
            'url': record_url,
            'target': 'new'
        }


class PurchaseOrderLineExt(models.Model):
    _inherit = 'purchase.order.line'

    note = fields.Text('Note')
