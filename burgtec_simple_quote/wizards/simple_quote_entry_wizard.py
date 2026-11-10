# -*- coding: utf-8 -*-
from collections import defaultdict
import logging
from markupsafe import Markup
from odoo import models, fields, api, _, Command
from odoo.tools import groupby,is_html_empty
from odoo.tools.mail import html_keep_url
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SimpleQuoteEntryWizard(models.TransientModel):
    _name = 'simple.quote.entry.wizard'
    _description = 'Simple Quote Entry Wizard'

    name = fields.Char()

    # CRM LEAD FIELDS.
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company, readonly=False, store=True)
    partner_id = fields.Many2one('res.partner',check_company=True)
    series_sequence_id = fields.Many2one('sale.order.series', string="Series Sequence")
    project_name = fields.Char()
    location = fields.Selection([
        ('nsw', 'New South Wales'),
        ('act', 'Australian Capital Territory'),
        ('vic', 'Victoria'),
        ('qld', 'Queensland'),
        ('other', 'Other')
    ], string="Location")
    state = fields.Selection([
        ('deal','Add Deal Details'),
        ('quote','Add Quote Details')
    ], default="deal")

    # Sale Order Fields.
    simple_quote_entry_order_line_ids = fields.One2many('simple.quote.entry.order.line','simple_quote_entry_id')
    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string="Pricelist",
        compute='_compute_pricelist_id',
        store=True, readonly=False, precompute=True, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="If you change the pricelist, only newly added lines will be affected.")

    zone_type = fields.Selection(
        [
            ('zone1', 'Zone 1 [EASTCOAST METRO (BNE, SYD, CBR, MEL)]'),
            ('zone2', 'Zone 2 [SYD]'),
            ('zone3', 'Zone 3 [BNE/MEL]'),
        ], default="zone1"
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency_id',
        store=True,
        precompute=True,
        ondelete='restrict'
    )

    currency_rate = fields.Float(
        string="Currency Rate",
        compute='_compute_currency_rate',
        digits=0,
        store=True, precompute=True)

    user_id = fields.Many2one(
        comodel_name='res.users',
        string="Salesperson",
        default=lambda self: self.env.user,
        )
    
    date_order = fields.Datetime(
        string="Order Date",
        required=True,
        help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.",
        default=fields.Datetime.now, copy=False)

    partner_invoice_id = fields.Many2one(
        comodel_name='res.partner',
        string="Invoice Address",
        compute='_compute_partner_invoice_id',
        store=True, readonly=False, precompute=True,
        check_company=True,
        index='btree_not_null')

    partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string="Delivery Address",
        compute='_compute_partner_shipping_id',
        store=True, readonly=False, precompute=True,
        check_company=True,
        index='btree_not_null')
    
    note = fields.Html(
        string="Terms and conditions",
        compute='_compute_note',
        store=True, readonly=False, precompute=True)
    
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position',
        string="Fiscal Position",
        compute='_compute_fiscal_position_id',
        store=True, readonly=False, precompute=True, check_company=True,
        help="Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices."
            "The default value comes from the customer.",
    )

    payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string="Payment Terms",
        compute='_compute_payment_term_id',
        store=True, readonly=False, precompute=True, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    head_title = fields.Html(compute="compute_title",store=True)
    title = fields.Html(compute="compute_title",store=True)

    tax_country_id = fields.Many2one(
        comodel_name='res.country',
        compute='_compute_tax_country_id',
        # Avoid access error on fiscal position when reading a sale order with company != user.company_ids
        compute_sudo=True)  # used to filter available taxes depending on the fiscal country and position
    
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)
    terms_type = fields.Selection(related='company_id.terms_type')

    is_draft_available = fields.Boolean()


    @api.depends('pricelist_id', 'company_id')
    def _compute_currency_id(self):
        for record in self:
            record.currency_id = record.pricelist_id.currency_id or record.company_id.currency_id
    
    @api.depends('currency_id', 'date_order', 'company_id')
    def _compute_currency_rate(self):
        for record in self:
            record.currency_rate = self.env['res.currency']._get_conversion_rate(
                from_currency=record.company_id.currency_id,
                to_currency=record.currency_id,
                company=record.company_id,
                date=(record.date_order or fields.Datetime.now()).date(),
            )
    

    @api.depends('partner_id', 'company_id')
    def _compute_pricelist_id(self):
        for record in self:
            if not record.partner_id:
                record.pricelist_id = False
                continue
            record = record.with_company(record.company_id)
            record.pricelist_id = record.partner_id.property_product_pricelist

    @api.depends('state')
    def compute_title(self):
        for record in self:
            if record.state == 'deal':
                record.head_title = Markup('''
                    <div class="stepper mb-4" style="margin-left:auto; margin-right:auto;">
                        <div class="step active">
                            <div class="circle">1</div>
                            <span class="label">Add Deal Details</span>
                        </div>

                        <div class="line"></div>

                        <div class="step">
                            <div class="circle">2</div>
                            <span class="label">Add Quote Details</span>
                        </div>
                    </div>
                ''')
                record.title = Markup('''
                <div class="mb-2">
                    <strong class="fw-bold" style="color:#875A7B;font-size:16px;">Step 1 of 2 - Add Deal Details</strong>
                    <br></br>
                    <span style="font-size:12px;">Provide basic details to set up your quotation</span>
                </div>
                ''')
            if record.state == 'quote':
                record.head_title = Markup('''
                    <div class="stepper mb-4" style="margin-left:auto; margin-right:auto;">
                        <div class="step">
                            <div class="circle">1</div>
                            <span class="label">Add Deal Details</span>
                        </div>

                        <div class="line"></div>

                        <div class="step active">
                            <div class="circle">2</div>
                            <span class="label">Add Quote Details</span>
                        </div>
                    </div>
                ''')
                record.title = Markup('''
                <div class="mb-2">
                    <strong class="fw-bold" style="color:#875A7B;font-size:16px;">Step 2 of 2 - Add Quote Details</strong>
                    <br></br>
                    <span style="font-size:12px;">Provide basic details to set up your quotation</span>
                </div>
                ''')

    def next(self):
        self.state = 'quote'
        return {
            'name': 'Create Quotation Simple Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'simple.quote.entry.wizard',  # Uses the current wizard transient model
            'view_mode': 'form',
            'res_id': self.id,        # Keeps the exact same record open
            'target': 'new',          # Forces it to stay/reopen in a pop-up modal
        }
    
    def back(self):
        self.state = 'deal'
        return {
            'name': 'Create Quotation Simple Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'simple.quote.entry.wizard',  # Uses the current wizard transient model
            'view_mode': 'form',
            'res_id': self.id,        # Keeps the exact same record open
            'target': 'new',          # Forces it to stay/reopen in a pop-up modal
        }
    
    def _get_lang(self):
        self.ensure_one()

        if self.partner_id.lang and not self.partner_id.is_public:
            return self.partner_id.lang

        return self.env.lang
    
    @api.depends('partner_id')
    def _compute_partner_invoice_id(self):
        for record in self:
            record.partner_invoice_id = record.partner_id.address_get(['invoice'])['invoice'] if record.partner_id else False

    @api.depends('partner_id')
    def _compute_partner_shipping_id(self):
        for record in self:
            record.partner_shipping_id = record.partner_id.address_get(['delivery'])['delivery'] if record.partner_id else False
    
    @api.depends('partner_id')
    def _compute_note(self):
        use_invoice_terms = self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms')
        if not use_invoice_terms:
            return
        for record in self:
            record = record.with_company(record.company_id)
            if record.terms_type == 'html' and self.env.company.invoice_terms_html:
                baseurl = html_keep_url(record._get_note_url() + '/terms')
                context = {'lang': record.partner_id.lang or self.env.user.lang}
                record.note = _('Terms & Conditions: %s', baseurl)
                del context
            elif not is_html_empty(self.env.company.invoice_terms):
                if record.partner_id.lang:
                    record = record.with_context(lang=record.partner_id.lang)
                record.note = record.env.company.invoice_terms
    
    @api.model
    def _get_note_url(self):
        return self.env.company.get_base_url()
    
    @api.depends('partner_shipping_id', 'partner_id', 'company_id')
    def _compute_fiscal_position_id(self):
        """
        Trigger the change of fiscal position when the shipping address is modified.
        """
        cache = {}
        for record in self:
            if not record.partner_id:
                record.fiscal_position_id = False
                continue
            fpos_id_before = record.fiscal_position_id.id
            key = (record.company_id.id, record.partner_id.id, record.partner_shipping_id.id)
            if key not in cache:
                cache[key] = self.env['account.fiscal.position'].with_company(
                    record.company_id
                )._get_fiscal_position(record.partner_id, record.partner_shipping_id).id
            if fpos_id_before != cache[key] and record.simple_quote_entry_order_line_ids:
                record.show_update_fpos = True
            record.fiscal_position_id = cache[key]
    
    @api.depends('partner_id')
    def _compute_payment_term_id(self):
        for record in self:
            record = record.with_company(record.company_id)
            record.payment_term_id = record.partner_id.property_payment_term_id
    
    @api.depends('company_id', 'fiscal_position_id')
    def _compute_tax_country_id(self):
        for record in self:
            if record.fiscal_position_id.foreign_vat:
                record.tax_country_id = record.fiscal_position_id.country_id
            else:
                record.tax_country_id = False
    
    @api.depends_context('lang')
    @api.depends('simple_quote_entry_order_line_ids.price_subtotal', 'currency_id', 'company_id', 'payment_term_id')
    def _compute_tax_totals(self):
        AccountTax = self.env['account.tax']
        for record in self:
            simple_order_lines = record.simple_quote_entry_order_line_ids.filtered(lambda x: not x.display_type)
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in simple_order_lines]
            base_lines += record._add_base_lines_for_early_payment_discount()
            AccountTax._add_tax_details_in_base_lines(base_lines, record.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, record.company_id)
            record.tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=record.currency_id or record.company_id.currency_id,
                company=record.company_id,
            )
    
    def _add_base_lines_for_early_payment_discount(self):
        """
        When applying a payment term with an early payment discount, and when said payment term computes the tax on the
        'mixed' setting, the tax computation is always based on the discounted amount untaxed.
        Creates the necessary line for this behavior to be displayed.
        :returns: array containing the necessary lines or empty array if the payment term isn't epd mixed
        """
        self.ensure_one()
        epd_lines = []
        if (
            self.payment_term_id.early_discount
            and self.payment_term_id.early_pay_discount_computation == 'mixed'
            and self.payment_term_id.discount_percentage
        ):
            percentage = self.payment_term_id.discount_percentage
            currency = self.currency_id or self.company_id.currency_id
            for line in self.simple_quote_entry_order_line_ids.filtered(lambda x: not x.display_type):
                line_amount_after_discount = (line.price_subtotal / 100) * percentage
                epd_lines.append(self.env['account.tax']._prepare_base_line_for_taxes_computation(
                    record=self,
                    price_unit=-line_amount_after_discount,
                    quantity=1.0,
                    currency_id=currency,
                    sign=1,
                    special_type='early_payment',
                    tax_ids=line.tax_id,
                ))
                epd_lines.append(self.env['account.tax']._prepare_base_line_for_taxes_computation(
                    record=self,
                    price_unit=line_amount_after_discount,
                    quantity=1.0,
                    currency_id=currency,
                    sign=1,
                    special_type='early_payment',
                ))
        return epd_lines
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        draft_record = self.env['simple.quote.draft'].search([('user_id','=',self.env.user.id)])
        if draft_record:
            res['is_draft_available'] = True
            return res

        if not res.get('simple_quote_entry_order_line_ids'):
            res['simple_quote_entry_order_line_ids'] = [
                (0, 0, {
                    'name': 'Group Name',
                    'display_type': 'line_section',
                    'sequence':10,
                }),
                (0, 0, {
                    'name': 'Code Name',
                    'display_type': 'line_note',
                    'sequence':11,
                }),
            ]

        return res
    
    def action_add_group(self):
        vals = {}
        simple_order_lines = self.simple_quote_entry_order_line_ids.sorted(lambda o: o.sequence)
        sequence = False
        if simple_order_lines:
            sequence = simple_order_lines[-1].sequence
            sequence+=1
            vals.update(
                {
                    'simple_quote_entry_id': self.id,
                    'name': 'Group NEW',
                    'display_type': 'line_section',
                    'sequence': sequence,
                }
            )

        new_group_record = self.env['simple.quote.entry.order.line'].sudo().create(vals)

        self.simple_quote_entry_order_line_ids = [Command.link(new_group_record.id)]
        return {
            'name': 'Create Quotation Simple Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'simple.quote.entry.wizard',  # Uses the current wizard transient model
            'view_mode': 'form',
            'res_id': self.id,        # Keeps the exact same record open
            'target': 'new',          # Forces it to stay/reopen in a pop-up modal
        }
    
    def create_quotation(self):
        #Two Steps.
        #1. Create CRM Lead First from the crm lead fields of the wizard.
        lead_obj = self.env['crm.lead'].sudo()
        order_obj = self.env['sale.order'].sudo()
        simple_order_lines = self.simple_quote_entry_order_line_ids.sorted(lambda s:s.sequence)
        lead_vals = {
            'partner_id': self.partner_id.id,
            'series_sequence_id':self.series_sequence_id.id,
            'project_name':self.project_name,
            'location':self.location
        }
        lead_res = lead_obj.create(lead_vals)
        lead_res.action_generate_deal_number() 
        lead_res.import_deal_from_hubspot()

        #2. Create Sales Order First from the so fields of the wizard.
        sequence = 10
        order_line_vals_list = []
        order_line_vals = {}
        order_vals= {
            'partner_id': self.partner_id.id,
            'project_name': self.project_name,
            'quote_type': 'sales_quote',
            'zone_type': self.zone_type,
            'date_order': self.date_order,
            'company_id': self.company_id.id,
            'opportunity_id': lead_res.id,
            'new_sale_order_number': lead_res.odoo_deal_number_6digit,
            'origin': 'Simple Quote Wizard',
            'is_simple_quote':True,
        }
        for line in simple_order_lines:
            order_line_vals = {
                'display_type':line.display_type,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'name': line.name,
                'company_id': line.company_id.id,
                'sequence':sequence,
            }
            order_line_vals_list.append((0,0,order_line_vals))
            order_line_vals = {}
            sequence+=1
        if order_line_vals_list:
            order_vals['order_line'] = order_line_vals_list
        
        order_res = order_obj.create(order_vals)
        context = {'simple_quote': 1, **self.env.context}
        return {
            'name': 'Sales Quotation',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',  # Uses the current wizard transient model
            'view_mode': 'form',
            'view_id': self.env.ref('burgtec_simple_quote.simple_quote_view_sale_order_form').id,
            'context':context,
            'res_id': order_res.id, 
            'target': 'current',      
        }
    
    def save_as_draft(self):
        draft_object = self.env['simple.quote.draft'].sudo()
        draft_data = self.copy_data()[0]
        draft_data_lines = self.simple_quote_entry_order_line_ids.copy_data()
        vals = {
            'user_id': self.env.user.id,
            'data': draft_data
        }
        if draft_data_lines:
            vals['lines_data'] = draft_data_lines
        draft_object.create(vals)
    
    def continue_draft(self):
        line_vals_list = []
        draft_record = self.env['simple.quote.draft'].search([('user_id','=',self.env.user.id)])
        data = draft_record.data
        lines_data = draft_record.lines_data
        for line_rec in lines_data:
            line_rec.pop('simple_quote_entry_id', None)
            line_vals_list.append((0,0,line_rec))
        data['simple_quote_entry_order_line_ids'] = line_vals_list
        if draft_record:
            draft_record.unlink()
        self.is_draft_available = False
        self.write(data)
        return {
            'name': 'Create Quotation Simple Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'simple.quote.entry.wizard',  # Uses the current wizard transient model
            'view_mode': 'form',
            'res_id': self.id,        # Keeps the exact same record open
            'target': 'new',          # Forces it to stay/reopen in a pop-up modal
        }


    def start_fresh(self):
        draft_record = self.env['simple.quote.draft'].search([('user_id','=',self.env.user.id)])
        if draft_record:
            draft_record.unlink()
        self.is_draft_available = False
        return {
            'name': 'Create Quotation Simple Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'simple.quote.entry.wizard',  # Uses the current wizard transient model
            'view_mode': 'form',
            'res_id': self.id,        # Keeps the exact same record open
            'target': 'new',          # Forces it to stay/reopen in a pop-up modal
        }
    

        






class SimpleQuoteOrderLine(models.TransientModel):
    _name= "simple.quote.entry.order.line"
    _description = 'Simple Quote Entry Wizard Order Lines'
    _order = 'sequence, id'


    simple_quote_entry_id = fields.Many2one('simple.quote.entry.wizard')
    sequence = fields.Integer(string="Sequence", default=10)

    # Order-related fields
    company_id = fields.Many2one(
        related='simple_quote_entry_id.company_id',
        store=True, index=True, precompute=True)
    currency_id = fields.Many2one(
        related='simple_quote_entry_id.currency_id',
        depends=['simple_quote_entry_id.currency_id'],
        store=True, precompute=True)
    order_partner_id = fields.Many2one(
        related='simple_quote_entry_id.partner_id',
        string="Customer",
        store=True, index=True, precompute=True)
    salesman_id = fields.Many2one(
        related='simple_quote_entry_id.user_id',
        string="Salesperson",
        store=True, precompute=True)

    # Fields specifying custom line logic
    display_type = fields.Selection(
        selection=[
            ('line_section', "Section"),
            ('line_note', "Note"),
        ],
        default=False)
    
    # Generic configuration fields
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        change_default=True, ondelete='restrict', index='btree_not_null',
        domain="[('sale_ok', '=', True),('product_bom_type','!=','components')]")

    product_template_id = fields.Many2one(
        string="Product Template",
        comodel_name='product.template',
        compute='_compute_product_template_id',
        readonly=False,
        search='_search_product_template_id',
        # previously related='product_id.product_tmpl_id'
        # not anymore since the field must be considered editable for product configurator logic
        # without modifying the related product_id when updated.
        domain=[('sale_ok', '=', True),('product_bom_type','!=','components')])

    
    name = fields.Text(
        string="Description",
        compute='_compute_name',
        store=True, readonly=False, required=True, precompute=True)
    
    product_uom_qty = fields.Float(
        string="Quantity",
        compute='_compute_product_uom_qty',
        digits='Product Unit of Measure', default=1.0,
        store=True, readonly=False, required=True, precompute=True)
    product_uom = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        compute='_compute_product_uom',
        store=True, readonly=False, precompute=True, ondelete='restrict',
        domain="[('category_id', '=', product_uom_category_id)]")
    
    # Pricing fields
    tax_id = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        compute='_compute_tax_id',
        store=True, readonly=False, precompute=True,
        context={'active_test': False},
        check_company=True)

    
    pricelist_item_id = fields.Many2one(
        comodel_name='product.pricelist.item',
        compute='_compute_pricelist_item_id')

    price_unit = fields.Float(
        string="Unit Price",
        compute='_compute_price_unit',
        digits='Product Price',
        store=True, required=True, precompute=True)
    
    technical_price_unit = fields.Float()

    product_template_attribute_value_ids = fields.Many2many(
        relation="prod_temp_att_value_simple_rel",
        related='product_id.product_template_attribute_value_ids',
        depends=['product_id'])

    # M2M holding the values of product.attribute with create_variant field set to 'no_variant'
    # It allows keeping track of the extra_price associated to those attribute values and add them to the SO line description
    product_no_variant_attribute_value_ids = fields.Many2many(
        relation="prod_no_var_att_value_simple_rel",
        comodel_name='product.template.attribute.value',
        string="Extra Values",
        compute='_compute_no_variant_attribute_values',
        store=True, readonly=False, precompute=True, ondelete='restrict')
    
    discount = fields.Float(
        string="Discount (%)",
        compute='_compute_discount',
        digits='Discount',
        store=True, readonly=False, precompute=True)
    
    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute='_compute_amount',
        store=True, precompute=True)
    price_tax = fields.Float(
        string="Total Tax",
        compute='_compute_amount',
        store=True, precompute=True)
    price_total = fields.Monetary(
        string="Total",
        compute='_compute_amount',
        store=True, precompute=True)
    
    product_type = fields.Selection(related='product_id.type', depends=['product_id'])

    line_group_id_value = fields.Char(compute="compute_line_group_code_id_value",store=True)
    line_code_id_value = fields.Char(compute="compute_line_group_code_id_value",store=True)

    @api.depends('simple_quote_entry_id.simple_quote_entry_order_line_ids')
    def compute_line_group_code_id_value(self):
        for record in self:
            group_lines = False
            code_lines = False
            simple_order_lines = record.simple_quote_entry_id.simple_quote_entry_order_line_ids.sorted(lambda l:l.sequence)
            if not simple_order_lines:
                record.line_group_id_value = False
                record.line_code_id_value = False
                continue
            # Groups Dont need this.
            if record.display_type =='line_section':
                record.line_group_id_value = False
                record.line_code_id_value = False
                continue
            # Code Knows Its Group.
            if record.display_type =='line_note':
                group_lines = simple_order_lines.filtered(lambda l:l.display_type == 'line_section' and l.sequence < record.sequence)
                if not group_lines:
                    record.line_group_id_value = False
                    continue
                record.line_group_id_value = group_lines[-1].id
            
            # Product Knows Its Group and Code
            if not record.display_type:
                group_lines = simple_order_lines.filtered(lambda l:l.display_type == 'line_section' and l.sequence < record.sequence)
                code_lines = simple_order_lines.filtered(lambda l:l.display_type == 'line_note' and l.sequence < record.sequence)
                if not group_lines and not code_lines:
                    record.line_group_id_value = False
                    record.line_code_id_value = False
                    continue
                if group_lines:
                    record.line_group_id_value = group_lines[-1].id
                if code_lines:
                    record.line_code_id_value = code_lines[-1].id
    


    def _get_sale_order_line_multiline_description_sale(self):

        """ Compute a default multiline description for this sales order line.

        In most cases the product description is enough but sometimes we need to append information that only
        exists on the sale order line itself.
        e.g:
        - custom attributes and attributes that don't create variants, both introduced by the "product configurator"
        - in event_sale we need to know specifically the sales order line as well as the product to generate the name:
        the product is not sufficient because we also need to know the event_id and the event_ticket_id (both which belong to the sale order line).
        """
        self.ensure_one()
        description = (
            self.product_id.get_product_multiline_description_sale()
            
        )
        return description

    

    @api.depends('product_id',)
    def _compute_name(self):
        for line in self:
            if not line.product_id:
                continue

            lang = line.simple_quote_entry_id._get_lang()
            if lang != self.env.lang:
                line = line.with_context(lang=lang)

            if line.product_id:
                line.name = line._get_sale_order_line_multiline_description_sale()
                continue
    
    @api.depends('display_type', 'product_id',)
    def _compute_product_uom_qty(self):
        for line in self:
            if line.display_type:
                line.product_uom_qty = 0.0
                continue

    @api.depends('product_id')
    def _compute_product_uom(self):
        for line in self:
            if not line.product_uom or (line.product_id.uom_id.id != line.product_uom.id):
                line.product_uom = line.product_id.uom_id
    
    @api.depends('product_id', 'company_id')
    def _compute_tax_id(self):
        lines_by_company = defaultdict(lambda: self.env['simple.quote.entry.order.line'])
        cached_taxes = {}
        for line in self:
            if line.product_type == 'combo':
                line.tax_id = False
                continue
            lines_by_company[line.company_id] += line
        for company, lines in lines_by_company.items():
            for line in lines.with_company(company):
                taxes = None
                if line.product_id:
                    taxes = line.product_id.taxes_id._filter_taxes_by_company(company)
                if not line.product_id or not taxes:
                    # Nothing to map
                    line.tax_id = False
                    continue
                fiscal_position = line.simple_quote_entry_id.fiscal_position_id
                cache_key = (fiscal_position.id, company.id, tuple(taxes.ids))
                cache_key += line._get_custom_compute_tax_cache_key()
                if cache_key in cached_taxes:
                    result = cached_taxes[cache_key]
                else:
                    result = fiscal_position.map_tax(taxes)
                    cached_taxes[cache_key] = result
                # If company_id is set, always filter taxes by the company
                line.tax_id = result
        
    def _get_custom_compute_tax_cache_key(self):
        """Hook method to be able to set/get cached taxes while computing them"""
        return tuple()
    
    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_pricelist_item_id(self):
        for line in self:
            if not line.product_id or line.display_type or not line.simple_quote_entry_id.pricelist_id:
                line.pricelist_item_id = False
            else:
                line.pricelist_item_id = line.simple_quote_entry_id.pricelist_id._get_product_rule(
                    line.product_id,
                    quantity=line.product_uom_qty or 1.0,
                    uom=line.product_uom,
                    date=line._get_order_date(),
                )
    
    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        for line in self:
            # Don't compute the price for deleted lines.
            if not line.simple_quote_entry_id:
                continue
            # User Cannot manually change the unit price in this wizard.

            line = line.with_context(sale_write_from_compute=True)
            if not line.product_uom or not line.product_id:
                line.price_unit = 0.0
                line.technical_price_unit = 0.0
            else:
                line = line.with_company(line.company_id)
                price = line._get_display_price()
                line.price_unit = line.product_id._get_tax_included_unit_price_from_price(
                    price,
                    product_taxes=line.product_id.taxes_id.filtered(
                        lambda tax: tax.company_id == line.env.company
                    ),
                    fiscal_position=line.simple_quote_entry_id.fiscal_position_id,
                )
                line.technical_price_unit = line.price_unit
    
    @api.depends('product_id')
    def _compute_product_template_id(self):
        for line in self:
            line.product_template_id = line.product_id.product_tmpl_id

    def _search_product_template_id(self, operator, value):
        return [('product_id.product_tmpl_id', operator, value)]
    
    def _get_order_date(self):
        self.ensure_one()
        return self.simple_quote_entry_id.date_order
    
    def _get_display_price(self):
        """Compute the displayed unit price for a given line.

        Overridden in custom flows:
        * where the price is not specified by the pricelist
        * where the discount is not specified by the pricelist

        Note: self.ensure_one()
        """
        self.ensure_one()
        return self._get_display_price_ignore_combo()
    
    def _get_display_price_ignore_combo(self):
        """ This helper method allows to compute the display price of a SOL, while ignoring combo
        logic.

        I.e. this method returns the display price of a SOL as if it were neither a combo line nor a
        combo item line.
        """
        self.ensure_one()

        pricelist_price = self._get_pricelist_price()

        if not self.pricelist_item_id._show_discount():
            # No pricelist rule found => no discount from pricelist
            return pricelist_price

        base_price = self._get_pricelist_price_before_discount()

        # negative discounts (= surcharge) are included in the display price
        return max(base_price, pricelist_price)
    
    def _get_pricelist_price(self):
        """Compute the price given by the pricelist for the given line information.

        :return: the product sales price in the order currency (without taxes)
        :rtype: float
        """
        self.ensure_one()
        self.product_id.ensure_one()

        price = self.pricelist_item_id._compute_price(
            product=self.product_id.with_context(**self._get_product_price_context()),
            quantity=self.product_uom_qty or 1.0,
            uom=self.product_uom,
            date=self._get_order_date(),
            currency=self.currency_id,
        )

        return price
    
    
    def _get_pricelist_price_before_discount(self):
        """Compute the price used as base for the pricelist price computation.

        :return: the product sales price in the order currency (without taxes)
        :rtype: float
        """
        self.ensure_one()
        self.product_id.ensure_one()

        return self.pricelist_item_id._compute_price_before_discount(
            product=self.product_id.with_context(**self._get_product_price_context()),
            quantity=self.product_uom_qty or 1.0,
            uom=self.product_uom,
            date=self._get_order_date(),
            currency=self.currency_id,
        )
    
    def _get_product_price_context(self):
        """Gives the context for product price computation.

        :return: additional context to consider extra prices from attributes in the base product price.
        :rtype: dict
        """
        self.ensure_one()
        return self.product_id._get_product_price_context(
            self.product_no_variant_attribute_value_ids,
        )

    @api.depends('product_id')
    def _compute_no_variant_attribute_values(self):
        for line in self:
            if not line.product_id:
                line.product_no_variant_attribute_value_ids = False
                continue
            if not line.product_no_variant_attribute_value_ids:
                continue
            valid_values = line.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
            # remove the no_variant attributes that don't belong to this template
            for ptav in line.product_no_variant_attribute_value_ids:
                if ptav._origin not in valid_values:
                    line.product_no_variant_attribute_value_ids -= ptav
    
    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            **{
                'tax_ids': self.tax_id,
                'quantity': self.product_uom_qty,
                'partner_id': self.simple_quote_entry_id.partner_id,
                'currency_id': self.simple_quote_entry_id.currency_id or self.simple_quote_entry_id.company_id.currency_id,
                'rate': self.simple_quote_entry_id.currency_rate,
                **kwargs,
            },
        )
    
    
    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_discount(self):
        discount_enabled = self.env['product.pricelist.item']._is_discount_feature_enabled()
        for line in self:
            if not line.product_id or line.display_type:
                line.discount = 0.0

            if not (line.simple_quote_entry_id.pricelist_id and discount_enabled):
                continue

            line.discount = 0.0

            if not line.pricelist_item_id._show_discount():
                # No pricelist rule was found for the product
                # therefore, the pricelist didn't apply any discount/change
                # to the existing sales price.
                continue

            line = line.with_company(line.company_id)
            pricelist_price = line._get_pricelist_price()
            base_price = line._get_pricelist_price_before_discount()

            if base_price != 0:  # Avoid division by zero
                discount = (base_price - pricelist_price) / base_price * 100
                if (discount > 0 and base_price > 0) or (discount < 0 and base_price < 0):
                    # only show negative discounts if price is negative
                    # otherwise it's a surcharge which shouldn't be shown to the customer
                    line.discount = discount
    
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        for line in self:
            base_line = line._prepare_base_line_for_taxes_computation()
            self.env['account.tax']._add_tax_details_in_base_line(base_line, line.company_id)
            line.price_subtotal = base_line['tax_details']['raw_total_excluded_currency']
            line.price_total = base_line['tax_details']['raw_total_included_currency']
            line.price_tax = line.price_total - line.price_subtotal
    
    def add_code(self):
        vals = {}
        simple_order_lines = False
        last_line = False
        # active_simple_order_line_id = self.env.context.get('active_id')
        # simple_order_line_obj = self.env['simple.quote.entry.order.line'].sudo().browse(active_simple_order_line_id)
        group_sequence = self.sequence
        new_code_sequence = group_sequence + 1
        simple_entry_obj = self.simple_quote_entry_id
        simple_order_lines = simple_entry_obj.simple_quote_entry_order_line_ids.sorted(lambda o: o.sequence)  # Save Before Clearing.

        lines_in_group = simple_order_lines.filtered(lambda l: int(l.line_group_id_value) == self.id)
        if lines_in_group:
            last_line = lines_in_group[-1]
            new_code_sequence = last_line.sequence + 1

        lines_to_update = simple_order_lines.filtered(
            lambda l: l.id != self.id and l.sequence >= new_code_sequence)
        if lines_to_update:
            for line in lines_to_update:
                line.sequence += 1


        vals.update(
            {
                'simple_quote_entry_id': simple_entry_obj.id,
                'name': 'Code New',
                'display_type': 'line_note',
                'sequence': new_code_sequence,
            }
        )

        new_code_record = self.env['simple.quote.entry.order.line'].sudo().create(vals)

        simple_entry_obj.simple_quote_entry_order_line_ids = [Command.link(new_code_record.id)]
        return {
            'name': 'Create Quotation Simple Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'simple.quote.entry.wizard',  # Uses the current wizard transient model
            'view_mode': 'form',
            'res_id': self.simple_quote_entry_id.id,        # Keeps the exact same record open
            'target': 'new',          # Forces it to stay/reopen in a pop-up modal
        }
    
    def action_show_wizard_to_add_product(self):
        # Don't include res_id key for wizards.
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': 'Perform Add Product Action',
            'view_id': self.env.ref('burgtec_simple_quote.simple_quote_entry_sale_order_line_wizard_add_product_form_view').id,
            'view_mode': 'form',
            'res_model': 'sale.order.line.wizard',
            'context': {
                'dialog_size': 'extra-large',
                'default_simple_quote_entry_id': self.simple_quote_entry_id.id,
                'default_pricelist_id': self.simple_quote_entry_id.pricelist_id.id,
                'default_date_order': self.simple_quote_entry_id.date_order,
                'default_currency_id': self.currency_id.id,
            }
        }
    



