from odoo import models, fields, api
from datetime import date, datetime, timedelta
from pytz import timezone, UTC

from odoo.addons.sale_purchase_inter_company_rules.models.purchase_order import purchase_order


class PurchaseOrderExt(models.Model):
    _inherit = 'purchase.order'

    hubspot_dispatch_date = fields.Datetime('Hubspot Dispatch Date', compute="_compute_hubspot_dispatch_date",
                                            tracking=True, store=True)
    dispatch_arrival_mismatch = fields.Boolean(
        string="Dispatch/Arrival Mismatch",
        compute="_compute_dispatch_arrival_mismatch",
        store=True
    )
    last_po_weekly_update_date = fields.Datetime('Last Weekly Update Date', tracking=1)

    po_weekly_update_date_tracking = fields.Datetime('PO Weekly Update Date Tracking', store=True)

    is_manual_expected_arrival = fields.Boolean(string="Manual Expected Arrival")

    date_planned = fields.Datetime(compute='_compute_date_planned', tracking=True, store=True, compute_sudo=True)

    overdue_po_weekly_update = fields.Boolean(
        string="Overdue PO Weekly Update",
    )
    po_due_in_two_days = fields.Boolean('PO Due In Two Days')

    po_due_after_dispatch = fields.Boolean('PO Due After Dispatch')

    required_arrival_date = fields.Date(compute='_compute_required_arrival_date',store=True,tracking=True)

    @api.depends('hubspot_dispatch_date')
    def _compute_required_arrival_date(self):
        for record in self:
            user_tz = False
            local_dt = False
            # if not record.required_arrival_date:
            if not record.hubspot_dispatch_date:
                record.required_arrival_date = False
            if record.hubspot_dispatch_date:
                user_tz = timezone(self.env.user.tz or 'UTC')
                local_dt = UTC.localize(record.hubspot_dispatch_date).astimezone(user_tz)
                record.required_arrival_date = (local_dt - timedelta(days=7)).date()



    @api.depends("hubspot_dispatch_date", "date_planned")
    def _compute_dispatch_arrival_mismatch(self):
        for order in self:
            if order.hubspot_dispatch_date and order.date_planned:
                order.dispatch_arrival_mismatch = (
                        order.hubspot_dispatch_date < order.date_planned
                )
                if order.dispatch_arrival_mismatch:
                    order.po_due_after_dispatch = True
                else:
                    order.po_due_after_dispatch = False
            else:
                order.dispatch_arrival_mismatch = False

    def action_assign_dispatch_date_to_parent_and_child_pos(self):
        for po in self:
            sale_orders = po._get_sale_orders()
            if sale_orders:
                sale_order = sale_orders[0]
                po.hubspot_dispatch_date = sale_order.hubspot_ticket_schedule_dispatch
                for picking in po.picking_ids:
                    child_pos = self.env['purchase.order'].search([('origin', '=', picking.name)])
                    child_pos.write({
                        'hubspot_dispatch_date': po.hubspot_dispatch_date

                    })

    def compute_overdue_po_weekly_update(self):
        threshold = fields.Datetime.now() - timedelta(days=7)
        purchase_orders = purchase_orders = self.env['purchase.order'].search(
            [('state', 'not in', ('done', 'cancel')), ('tag', '=', 'child')])
        for order in purchase_orders:
            order.overdue_po_weekly_update = (
                    order.po_weekly_update_date_tracking and
                    order.po_weekly_update_date_tracking < threshold
            )

    def compute_po_due_in_two_days(self):
        purchase_orders = self.env['purchase.order'].search(
            [('state', 'not in', ('done', 'cancel')), ('tag', '=', 'child')])
        for order in purchase_orders:
            if order.hubspot_dispatch_date and order.date_planned:
                if order.date_planned < order.hubspot_dispatch_date:
                    date_diff = order.hubspot_dispatch_date - order.date_planned
                    if date_diff.days == 2:
                        order.po_due_in_two_days = True
                    else:
                        order.po_due_in_two_days = False
            else:
                order.po_due_in_two_days = False

    def write(self, vals):
        if 'last_po_weekly_update_date' in vals and self.tag == 'child' and self.state not in ['done',
                                                                                               'cancel']:
            vals['po_weekly_update_date_tracking'] = fields.Datetime.now()
        res = super(PurchaseOrderExt, self).write(vals)
        return res

    def correct_po_weekly_update_date(self):
        for record in self:
            if record.last_po_weekly_update_date:
                record.po_weekly_update_date_tracking = record.last_po_weekly_update_date

    @api.depends(
        'parent_po_id.order_line.sale_order_id.hubspot_ticket_schedule_dispatch',
        'order_line.sale_order_id.hubspot_ticket_schedule_dispatch',
    )
    def _compute_hubspot_dispatch_date(self):
        for record in self:
            sale_orders = record._get_sale_orders()
            sale_order = False
            if record.tag == 'parent':
                if sale_orders:
                    sale_order = sale_orders[0]
                    record.hubspot_dispatch_date = sale_order.hubspot_ticket_schedule_dispatch
                else:
                    record.hubspot_dispatch_date = False
            elif record.tag == 'child':
                if record.parent_po_id:
                    sale_orders = record.parent_po_id._get_sale_orders()
                    if sale_orders:
                        sale_order = sale_orders[0]
                        record.hubspot_dispatch_date = sale_order.hubspot_ticket_schedule_dispatch
                    else:
                        record.hubspot_dispatch_date = False
                else:
                    record.hubspot_dispatch_date = False
            else:
                record.hubspot_dispatch_date = False

    @api.depends('partner_id', 'hubspot_dispatch_date', 'shipping_address_type', 'receipt_status')
    def _compute_date_planned(self):
        today = fields.Datetime.now()
        eta_date = False
        for order in self:
            if order.shipping_address_type != 'burgtec_vendor' and not order.is_manual_expected_arrival:
                order.date_planned = False
                order.is_manual_expected_arrival = True
                continue
            if (not order.hubspot_dispatch_date or order.receipt_status == 'full' or order.is_manual_expected_arrival):
                continue
            dispatch_date = order.hubspot_dispatch_date
            if not dispatch_date:
                continue
            # skip past dispatch POs
            if dispatch_date:
                if dispatch_date < today:
                    continue
                days_difference = (dispatch_date - today).days
                # within 7 days → ETA = today
                if days_difference < 7:
                    eta_date = today
                else:
                    eta_date = dispatch_date - timedelta(days=7)
                order.date_planned = eta_date

    
    def fix_estimated_arrival(self):
        mail_message_object = self.env['mail.message'].sudo()
        date_planned_field_object = self.env.ref("burgtec_hubspot_customization.field_purchase_order__date_planned")

        for record in self:
            mail_message_record = mail_message_object.search(
                ["&", "&", ("date", ">=", "2026-06-01 14:00:00"), ("date", "<=", "2026-06-01 15:00:00"), ("res_id", "=", record.id)]
            )
            message_track_record = mail_message_record.tracking_value_ids.filtered(
                lambda t: t.field_id.id == date_planned_field_object.id
            )

            # If multiple tracking records found, take the one with the lowest ID
            if len(message_track_record) > 1:
                message_track_record = message_track_record.sorted(key=lambda t: t.id)[0]

            if not message_track_record:
                continue

            old_value = message_track_record.old_value_datetime
            new_value = message_track_record.new_value_datetime
            # print("---------------------------")
            # print(old_value, new_value)
            # print("---------------------------")
            record.write({
                'date_planned': old_value
            })


