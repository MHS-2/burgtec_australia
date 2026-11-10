import pytz
from email.policy import default
from markupsafe import Markup
from odoo.http import request
from odoo import _, fields, models, api, Command
import re
import string
import logging

_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError, ValidationError, AccessError

sale_state_dict = {
    'draft': 'Draft',
    'sent': 'Quotation Sent',
    'quotation_confirmed': 'Quotation Confirmed',
    'sale': 'Sales Order',
    'cancel': 'Cancelled',
}


class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    custom_project_id = fields.Many2one('project.project', string='Project Reference')
    bom_component_id = fields.Many2one(
        'sale.order.bom.component',
        string='BOM Components'
    )
    split_do_id = fields.Many2one(
        'split.do',
        string='Split Do',
        copy=False
    )
    is_old_data = fields.Boolean('Is Old Data ?', default=False, copy=True)
    is_having_delivery_stage = fields.Boolean('Is Having Delivery ?', default=False, copy=False)
    is_having_project_stage = fields.Boolean('Is Having Project Quote ?', default=False, copy=False)
    # is_in_builder_trend = fields.Boolean('Is Builder Trend ?', default=False, copy=False)

    system_cost_per_unit = fields.Monetary(string='Margin on System Cost', readonly=True, currency_field='currency_id')
    live_unit_cost = fields.Monetary(string='Margin on Live Cost', readonly=True, currency_field='currency_id')
    quoted_cost_per_unit = fields.Monetary(string='Margin on Quoted Cost', readonly=True, currency_field='currency_id')
    pre_project_cost_per_unit = fields.Monetary(string='Margin on Pre-Project Cost', readonly=True,
                                                currency_field='currency_id')
    system_cost_bom_total = fields.Monetary(string='Total Margin on System Cost', readonly=True, currency_field='currency_id')
    live_cost_bom_total = fields.Monetary(string='Total Margin on Live Cost', readonly=True, currency_field='currency_id')
    quoted_cost_bom_total = fields.Monetary(string='Total Margin on Quoted Cost', readonly=True, currency_field='currency_id')
    pre_project_cost_bom_total = fields.Monetary(string='Total Margin on Pre Project Cost', readonly=True,
                                                 currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    components_report_id = fields.Many2one('components.on.report', default=False)
    purchase_order_id = fields.Many2one('purchase.order')
    delivery_date = fields.Datetime('Custom Delivery Date')

    percentage_margin_system_cost = fields.Float(string="Percentage Margin (System Cost)")
    percentage_margin_live_cost = fields.Float(string="Percentage Margin (Live Cost)")
    percentage_margin_quoted_cost = fields.Float(string="Quoted Cost")
    percentage_margin_pre_project_cost = fields.Float(string="Pre-Project Cost")

    # Markup Fields
    percentage_markup_system_cost = fields.Float(string="Percentage Markup (System Cost)")
    percentage_markup_live_cost = fields.Float(string="Percentage Markup (Live Cost)")
    percentage_markup_quoted_cost = fields.Float(string="Quoted Cost Markup")
    percentage_markup_pre_project_cost = fields.Float(string="Pre-Project Cost Markup")

    state = fields.Selection(
        selection_add=[
            ("sent",),
            ("quotation_confirmed", "Quotation Confirmed"),
            ("sale",),
            ("cancel",),
        ],
        ondelete={'quotation_confirmed': 'set default'}
    )
    hubspot_reference = fields.Char(string="Hubspot Reference")
    burgtec_quote_reference = fields.Char(string="Burgtec Reference")
    manual_rev = fields.Char(string="Revision Name")

    system_revision = fields.Char()

    def action_update_prices(self):
        res = super(SaleOrderExt, self).action_update_prices()
        if self.bom_component_id:
            self.bom_component_id.update_component_lines()
        return res

    def action_mark_old_data(self):
        for order in self:
            order.write({
                'is_old_data': True
            })

    def action_mark_project_quote_with_delivery(self):
        for delivery in self:
            odoo_reference_on_delivery = delivery.name.split("-")[0].strip()
            project_quotes = self.env['sale.order'].search([
                ('quote_type', '=', 'project_quote'),
                ('name', 'ilike', odoo_reference_on_delivery)
            ])
            if project_quotes:
                project_quotes.write({
                    'is_having_delivery_stage': True,
                })

    def action_mark_sale_quote_with_project(self):
        for project_quote in self:
            odoo_reference_on_project_quote = project_quote.name.split("-")[0].strip()
            sales_quotes = self.env['sale.order'].search([
                ('quote_type', '=', 'sales_quote'),
                ('name', 'ilike', odoo_reference_on_project_quote)
            ])
            if sales_quotes:
                sales_quotes.write({
                    'is_having_project_stage': True,
                })


    def _confirmation_error_message(self):
        """ Return whether order can be confirmed or not if not then returm error message. """
        self.ensure_one()
        if self.state not in {'draft', 'quotation_confirmed', 'sent'}:
            return _("Some orders are not in a state requiring confirmation.")
        if any(
                not line.display_type
                and not line.is_downpayment
                and not line.product_id
                for line in self.order_line
        ):
            return _("A line on these orders missing a product, you cannot confirm it.")

        return False

    def action_quotation_confirm(self):
        for order in self:
            if not order.bom_component_id:
                raise UserError(_("Kindly Set and Save Bom Components!"))
            order.bom_component_id.update_component_lines()
            order.state = 'quotation_confirmed'

    def action_mark_as_quoation_sent(self):
        for rec in self:
            rec.write({
                'state': 'sent'
            })

    def web_save(self, vals, specification: dict[str, dict], next_id=None) -> list[dict]:
        if self:
            if self.state not in ('draft'):
                if not self.env.user.has_group("sales_team.group_sale_manager"):
                    raise AccessError(
                        _(f"Only Sales Administrator can edit a Sale Quotation in '{sale_state_dict[self.state]}' State"))
        return super(SaleOrderExt, self).web_save(vals, specification)

    def action_confirm(self):
        """Override action_confirm to set purchase line prices to zero and assign purchase order"""
        # if not self.delivery_stage:
        #     raise UserError(_("Delivery Stage is required to proceed!"))

        if not self.bom_component_id:
            raise UserError(_("Kindly set and save the Components before confirming!"))

        # if not self.split_do_id:
        #     raise UserError(("Kindly set and Save the Delivery Orders before confirming!"))

        res = super(SaleOrderExt, self).action_confirm()

        for order in self:
            purchase_lines = order.order_line.mapped('purchase_line_ids')
            if purchase_lines:
                purchase_lines.write({'price_unit': 0.0})
            order.activity_ids.filtered(lambda a: a.display_name == 'Exception').unlink()
        return res

    def action_show_component(self):
        self.ensure_one()
        bom_component = self.bom_component_id
        sale_order_lines = self.order_line
        # filtered_sale_order_lines = sale_order_lines.filtered(lambda l: l.product_id)
        if bom_component and not sale_order_lines:
            bom_component.unlink()
            bom_component = None
        return {
            'name': _('BOM Components'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.bom.component',
            'res_id': bom_component.id or False,
            'view_mode': 'form',
            'view_id': self.env.ref('bom_based_inventory.view_sale_order_bom_components_form').id,
            'target': 'current',
            'context': {
                'active_model': 'sale.order',
                'active_id': self.id,
                'default_order_id': self.id,
                'bom_id': bom_component.id or False,
            }
        }

    def action_show_delivery_orders(self):
        self.ensure_one()
        return {
            'name': _('Split Delivery Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'split.do',
            'res_id': self.split_do_id.id or False,
            'view_id': self.env.ref('bom_based_inventory.view_split_do_form').id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id}
        }


    def copy(self, default=None):
        default = dict(default or {})

        # Ensure we handle a single record
        self.ensure_one()
        for rec in self:
            base_name_match = re.match(r'^(S\d+)', rec.name)
            base_name = base_name_match.group(1) if base_name_match else rec.name

            # Search for all revisions of this order
            similar_orders = rec.search([('name', 'ilike', base_name)])

            # Extract existing revision letters
            revision_letters = []
            for order in similar_orders:
                match = re.search(r'Revision ([A-Z])$', order.name)
                if match:
                    revision_letters.append(match.group(1))

            # Determine next letter
            next_letter = 'A'
            if revision_letters:
                last_letter = max(revision_letters)
                if last_letter != 'Z':
                    next_letter = chr(ord(last_letter) + 1)
                else:
                    raise UserError(_("Revision limit reached (Z)"))

            # Build new name
            system_rev = f'Revision {next_letter}'
            new_name = f"{base_name} - Revision {next_letter}"
            default['name'] = new_name

            if not rec.bom_component_id:
                raise UserError(_("Kindly set and save the Components before duplicating!"))

            # Perform the duplication
            new_order = super(SaleOrderExt, rec).copy(default)
            _logger.info(" ------ >  NEW Order Created  < ----------")

            # Copy and relink the BOM component
            if rec.bom_component_id:
                new_bom = rec.bom_component_id.with_context(duplicating_sale_quote=True).copy(
                    {'order_id': new_order.id})
                new_order.write({'bom_component_id': new_bom.id, 'system_revision': system_rev})
                _logger.info(" ------ >  NEW BOM Created and Writen in Sale Order BOM Component ID < ----------")

                current_rec_order_line = rec.order_line
                new_rec_order_line = new_order.order_line

                if current_rec_order_line and new_rec_order_line:
                    for old_line, new_line in zip(current_rec_order_line, new_rec_order_line):
                        new_line.write({'old_order_line': old_line.id})
                    for new_line in new_rec_order_line:
                        new_components_line_based_on_old_id = new_bom.component_line_ids.filtered(
                            lambda l: l.order_line_id.id == int(new_line.old_order_line))
                        new_components_line_based_on_old_id.write({
                            'order_line_id': new_line.id
                        })

            _logger.info(" ------ >  MAPPING OF OLD ORDER LINE ID AND NEW ORDER LINE ID IS DONE < ----------")

            # Recompute components
            new_order.bom_component_id.update_component_lines()
            return new_order

    def _get_purchase_orders(self):
        origins = self.mapped('name')
        po_ids = self.env['purchase.order'].search([('origin', 'in', origins), ('state', '!=', 'cancel')], limit=1)
        self.purchase_order_id = po_ids.id
        return po_ids


    def action_cancel(self):
        for sale in self:
            # Step 1: Cancel Parent POs (linked directly via origin)
            parent_pos = self.env['purchase.order'].search([
                ('origin', '=', sale.name),
                ('state', 'not in', ['cancel', 'done'])
            ])
            for po in parent_pos:
                pickings = po.picking_ids
                # Step 2: Cancel all child POs using origin = parent PO's delivery (picking name)
                for picking in pickings:
                    child_pos = self.env['purchase.order'].search([
                        ('origin', '=', picking.name),
                        ('state', 'not in', ['cancel', 'done'])
                    ])
                    for child_po in child_pos:
                        child_po.button_cancel()

                # Cancel the parent PO
                po.button_cancel()

        # Finally, cancel the Sale Order as usual
        return super(SaleOrderExt, self).action_cancel()

    def open_record_in_new_window(self):
        root_url = request.httprequest.url_root
        record_url = f"{root_url}/odoo/orders/{self.id}"
        return {
            'type': 'ir.actions.act_url',
            'url': record_url,
            'target': 'new'
        }
    
    def update_bom_lines(self):
        for record in self:
            bom_component = record.bom_component_id
            if bom_component:
                bom_component.update_component_lines()
    
    def set_system_rev(self):
        for record in self:
            revision_name = False
            rev_name_group = False
            order_name = record.name
            if order_name:
                revision_name = re.search(r"Revision\s+[A-Z]", order_name)
                if not revision_name:
                    record.system_revision = False
                else:
                    rev_name_group = revision_name.group()
                    record.system_revision = rev_name_group



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _rec_name = 'id'

    old_order_line = fields.Char('Order Line', copy=False)
    component_html = fields.Html(string="Components")
    # is_component_shown = fields.Boolean(string="Is Component Shown", default=True)
    component_visible = fields.Boolean(string="Component Visible", default=True)

    excel_file = fields.Binary(string='Download Report Excel')

    file_name = fields.Char(string='Excel File')

    system_cost_per_unit = fields.Monetary(string='Margin on System Cost', readonly=True, currency_field='currency_id')
    live_unit_cost = fields.Monetary(string='Margin on Live Cost', readonly=True, currency_field='currency_id')
    quoted_cost_per_unit = fields.Monetary(string='Margin on Quoted Cost', readonly=True, currency_field='currency_id')
    pre_project_cost_per_unit = fields.Monetary(string='Margin on Pre-Project Cost', readonly=True,
                                                currency_field='currency_id')

    system_cost_bom_total = fields.Monetary(string='Total Margin on System Cost', readonly=True, currency_field='currency_id')
    live_cost_bom_total = fields.Monetary(string='Total Margin on Live Cost', readonly=True, currency_field='currency_id')
    quoted_cost_bom_total = fields.Monetary(string='Total Margin on Quoted Cost', readonly=True, currency_field='currency_id')
    pre_project_cost_bom_total = fields.Monetary(string='Total Margin on Pre Project Cost', readonly=True,
                                                 currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency')

    line_section_name = fields.Char()

    
    def fill_component_html(self):
        purchase_order_status = {'draft': 'Draft', 'sent': 'RFQ Sent', 'to approve': 'To Approve',
                                 'purchase': 'Purchase Order', 'done': 'Locked', 'cancel': 'Cancelled'}
        root_url = request.httprequest.url_root
        date_planned_user_timezone = False
        # print('Root URL', root_url)
        if self.order_id.bom_component_id:
            # print('SELF--------->',self) self.id is same as its sale order line id.
            sale_order = self.order_id
            purchase_order = self.order_id.purchase_order_id
            # NOW PARENT PO CAN BE MORE THAN 1 OR 1
            # parent_pos = sale_order._get_purchase_orders()
            parent_po = sale_order.purchase_order_id
            child_purchase_order = self.env['purchase.order']
            if parent_po.picking_ids:
                picking_name = parent_po.picking_ids[0].display_name
                child_purchase_order = self.env['purchase.order'].search([('origin', '=', picking_name)])
            # print('Sale Order BOM ID', sale_order.bom_component_id)
            # print('Sale Order BOM ID Componenet Line IDS', sale_order.bom_component_id.component_line_ids)
            # print('Sale Order',sale_order)
            # print('Purchase Order',purchase_order)
            # print('Parent PO', parent_po)
            # print('Component Lines', component_lines)
            # print('Self Product', self.product_id)
            # print('Self Product tEMPL', self.product_tmpl_id)

            table_code = Markup('''<table class="table table-bordered o_table" data-oe-version="1.2">
                                                       <tbody>
                                                           <tr class="fw-bold">
                                                               <td colspan="14">
                                                                   <div>
                                                                       {product_name}
                                                                   </div>
                                                               </td>
                                                           </tr>
                                                           <tr class="fw-bold">
                                                               <td><div>Product Reference</div></td>
                                                               <td colspan="3"><div>Product</div></td>
                                                               <td><div>Quantity</div></td>
                                                               <td><div>Live Unit Cost</div></td>
                                                               <td><div>System Cost Per Unit</div></td>
                                                               <td><div>Quoted Cost Per Unit</div></td>
                                                               <td><div>Pre Project Cost Per Unit</div></td>
                                                               <td><div>Note</div></td>
                                                               <td><div>Supplier</div></td>
                                                               <td><div>Delivery Date</div></td>
                                                               <td><div>Purchase Order</div></td>
                                                               <td><div>Purchase Order Status</div></td>
                                                           </tr>
                                                           ''').format(
                product_name=self.product_template_id.name if self.product_template_id else 'N/A')

            component_lines = sale_order.bom_component_id.component_line_ids.filtered(
                lambda l: l.parent_product_id.id == self.product_template_id.id and l.order_line_id.id == self.id)

            self.system_cost_per_unit = self.price_subtotal - sum(
                component_lines.mapped('system_cost_per_unit'))
            self.live_unit_cost = self.price_subtotal - sum(
                component_lines.mapped('live_unit_cost'))
            self.quoted_cost_per_unit = self.price_subtotal - sum(
                component_lines.mapped('quoted_cost_per_unit'))
            self.pre_project_cost_per_unit = self.price_subtotal - sum(
                component_lines.mapped('pre_project_cost_per_unit'))

            # Lines for report
            self.live_cost_bom_total = sum(component_lines.mapped('live_unit_cost'))
            self.system_cost_bom_total = sum(component_lines.mapped('system_cost_per_unit'))
            self.pre_project_cost_bom_total = sum(component_lines.mapped('pre_project_cost_per_unit'))
            self.quoted_cost_bom_total = sum(component_lines.mapped('quoted_cost_per_unit'))

            for line in component_lines:
                if not line.is_parent:

                    matching_po = child_purchase_order.filtered(lambda po: any(
                        ol.product_id.id == line.product_id.id for ol in
                        po.order_line) and po.partner_id.id == line.supplier_id.id)
                    matching_po = matching_po[0] if matching_po else False
                    user_timezone = pytz.timezone(self.env.context.get('tz') or self.env.user.tz)

                    if matching_po and matching_po.date_planned:
                        date_planned_user_timezone = pytz.utc.localize(matching_po.date_planned).astimezone(
                            user_timezone).strftime("%d/%m/%Y %H:%M:%S")
                    delivery_date = date_planned_user_timezone if matching_po else False
                    table_code += Markup('''<tr>
                                                   <td><div>{product_reference}</div></td>
                                                   <td colspan="3"><div>{product}</div></td>
                                                   <td><div>{quantity}</div></td>
                                                   <td><div>{live_unit_cost}</div></td>
                                                   <td><div>{system_cost_per_unit}</div></td>
                                                   <td><div>{quoted_cost_per_unit}</div></td>
                                                   <td><div>{pre_project_cost_per_unit}</div></td>
                                                   <td><div>{Note}</div></td>
                                                   <td><div>{supplier}</div></td>
                                                   <td><div>{delivery}</div></td>
                                                   <td>
                                                       <div>
                                                           {purchase_order_link}
                                                       </div>    
                                                   </td>
                                                   <td>
                                                       <div>
                                                           {purchase_order_status}
                                                       </div>
                                                   </td>
                                               </tr>
                                           ''').format(
                        product_reference=line.product_reference if line.product_reference else 'N/A',
                        product=line.product_id.name if line.product_id else 'N/A',
                        quantity=line.product_qty if line.product_qty else 0,
                        live_unit_cost=line.live_unit_cost if line.live_unit_cost else 0,
                        system_cost_per_unit=line.system_cost_per_unit if line.system_cost_per_unit else 0,
                        quoted_cost_per_unit=line.quoted_cost_per_unit if line.quoted_cost_per_unit else 0,
                        pre_project_cost_per_unit=line.pre_project_cost_per_unit if line.pre_project_cost_per_unit else 0,
                        Note=line.note if line.note else 'N/A',
                        supplier=line.supplier_id.name if line.supplier_id else 'N/A',
                        delivery=delivery_date if delivery_date else 'N/A',
                        matching_po=matching_po if matching_po else False,
                        purchase_order_link=Markup(
                            '<a href="{root_url}/odoo/purchase/{matching_po.id}">{matching_po.name}</a>').format(
                            root_url=root_url, matching_po=matching_po
                        ) if matching_po else 'N/A',
                        purchase_order=matching_po.name if matching_po else 'N/A',
                        purchase_order_status=purchase_order_status[matching_po.state] if matching_po else 'N/A',
                    )
            table_code += Markup('''</tbody></table><div><br></div>''')
            self.component_html = table_code


    # Updating Split Delivery Order!
    @api.onchange('product_uom_qty')
    def _update_split_delivery_order_vals(self):
        if self.product_uom_qty < 0:
            raise UserError(_('You cannot Assign Negative Values to Product Quantity.'))
        if self.order_id.split_do_id:
            split_do_line = self.order_id.split_do_id.line_ids.filtered(lambda l: l.order_line_id.id == self._origin.id)
            # split_do_line.do_stage_1 = self.product_uom_qty
            split_do_line.write(
                {
                    'quantity': self.product_uom_qty,
                    'do_stage_1': self.product_uom_qty,
                }
            )
            split_do_line.split_id.onchange_line_ids()
