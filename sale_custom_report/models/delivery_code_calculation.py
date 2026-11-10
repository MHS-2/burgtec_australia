from io import BytesIO
import xlsxwriter
import base64
from odoo import fields, models,api, _, Command
from odoo.exceptions import UserError

class DeliveryCodeCalculation(models.Model):
    _name = 'delivery.code.calculation'
    _description = 'Delivery Code Calculation'

    order_id = fields.Many2one('sale.order',string='Sale Order', ondelete='cascade')

    delivery_code_calculation_line_ids = fields.One2many('delivery.code.calculation.line','delivery_code_calculation_id')

    company_id = fields.Many2one('res.company', store=True, copy=False,
                                string="Company",
                                default=lambda self: self.env.user.company_id.id)

    currency_id = fields.Many2one('res.currency', string="Currency",
                                 related='company_id.currency_id',)

    final_total_cost = fields.Monetary(compute="_compute_total_cost")

    final_cbm_flatpacked = fields.Float(compute="_compute_total_cost")

    final_cbm_assembled = fields.Float(compute="_compute_total_cost")

    final_total_installation_cost = fields.Monetary(compute="_compute_total_cost")

    final_total_delivery_cost = fields.Monetary(compute="_compute_total_cost")

    is_individual_products = fields.Boolean()

    manual_percentage = fields.Float()

    final_total_cost_with_markup = fields.Monetary(compute="_compute_final_wih_markup")

    zone_type = fields.Selection(
        [
            ('zone1','Zone 1 [EASTCOAST METRO (BNE, SYD, CBR, MEL)]'),
            ('zone2','Zone 2 [SYD]'),
            ('zone3','Zone 3 [BNE/MEL]'),
        ], compute="_compute_zone_type"
    )

    delivery_code_calculation_summary_line_ids = fields.One2many('delivery.code.calculations.summary.line','delivery_code_calculation_id',compute="_compute_summary_lines", store=True)

    excel_file = fields.Binary(string='Download Report Excel')

    file_name = fields.Char(string='Excel File')


    def _compute_display_name(self):
        for record in self:
            if record.order_id:
                record.display_name = _('Delivery Code Calculation - %s',record.order_id.burgtec_quote_reference)


    @api.depends('order_id.zone_type')
    def _compute_zone_type(self):
        for record in self:
            if not record.order_id:
                record.sudo().write({
                    'zone_type':False
                })
            if record.order_id:
                record.sudo().write({
                    'zone_type':record.order_id.zone_type
                })
            
    
 

    @api.depends("manual_percentage","final_total_cost")
    def _compute_final_wih_markup(self):
        for record in self:
            if record.manual_percentage:
                record.final_total_cost_with_markup = record.final_total_cost * (record.manual_percentage + 1)
            else:
                record.final_total_cost_with_markup = record.final_total_cost

    @api.depends("delivery_code_calculation_line_ids","zone_type")
    def _compute_total_cost(self):
        for record in self:
            group_total = 0
            section_total = 0
            final_total_delivery_cost = 0
            final_total_installation_cost = 0
            individual_total = 0
            individual_cbm_assembled_total = 0
            individual_cbm_flatpacked_total = 0
            group_cbm_assembled_total = 0
            group_cbm_flatpacked_total = 0
            section_cbm_assembled_total = 0
            section__cbm_flatpacked_total = 0
            record.final_total_cost= 0 
            record.is_individual_products = False
            lines = record.delivery_code_calculation_line_ids
            if lines:
                # Individual Products
                individual_prodcuts = lines.filtered(lambda i: not i.display_type and not i.line_group_name and not i.line_section_name)
                if individual_prodcuts:
                    record.is_individual_products = True
                    individual_delivery_total = sum(individual_prodcuts.mapped('total_delivery_cost'))
                    individual_installation_total = sum(individual_prodcuts.mapped('total_installation_cost'))
                    individual_total = individual_delivery_total + individual_installation_total
                    individual_cbm_assembled_total = sum(individual_prodcuts.mapped('total_cbm_assembled'))
                    individual_cbm_flatpacked_total = sum(individual_prodcuts.mapped('total_cbm_flatpacked'))
                    record.final_total_cost = record.final_total_cost + individual_total
                    record.final_cbm_assembled = record.final_cbm_assembled + individual_cbm_assembled_total
                    record.final_cbm_flatpacked = record.final_cbm_flatpacked + individual_cbm_flatpacked_total
                group_lines = lines.filtered(lambda g: g.display_type == 'line_section')
                if not group_lines:
                    raise UserError(_('No Group Found. Kindly make sure you have added a Group and Code Line Before a Product.'))
                if group_lines:
                    for group in group_lines:
                        group_total = 0
                        group_cbm_assembled_total = 0
                        group_cbm_flatpacked_total = 0
                        section_lines = lines.filtered(lambda s: s.display_type == 'line_note' and s.line_group_name == group.name)
                        if not section_lines:
                            raise UserError(_('No Code Found. Kindly make sure you have added a Group and Code Line Before a Product.'))
                        if section_lines:
                            for section in section_lines:
                                section_delivery_total = sum(lines.filtered(lambda p: not p.display_type and p.line_group_name == group.name and p.line_section_name == section.name).mapped('total_delivery_cost'))
                                section_installation_total = sum(lines.filtered(lambda p: not p.display_type and p.line_group_name == group.name and p.line_section_name == section.name).mapped('total_installation_cost'))
                                final_total_delivery_cost = final_total_delivery_cost + section_delivery_total
                                final_total_installation_cost = final_total_installation_cost + section_installation_total
                                section_total = section_installation_total + section_delivery_total
                                section_cbm_assembled_total = sum(lines.filtered(lambda p: not p.display_type and p.line_group_name == group.name and p.line_section_name == section.name).mapped('total_cbm_assembled'))
                                section__cbm_flatpacked_total = sum(lines.filtered(lambda p: not p.display_type and p.line_group_name == group.name and p.line_section_name == section.name).mapped('total_cbm_flatpacked'))
                                group_total = group_total +  section_total
                                group_cbm_assembled_total = group_cbm_assembled_total + section_cbm_assembled_total
                                group_cbm_flatpacked_total = group_cbm_flatpacked_total + section__cbm_flatpacked_total
                                section.total_cost = section_total
                                section.total_cbm_assembled_final = section_cbm_assembled_total
                                section.total_cbm_flatpacked_final = section__cbm_flatpacked_total
                            group.total_cost = group_total
                            group.total_cbm_assembled_final = group_cbm_assembled_total
                            group.total_cbm_flatpacked_final = group_cbm_flatpacked_total
                            record.final_total_cost = record.final_total_cost + group_total
                            record.final_cbm_assembled = record.final_cbm_assembled + group_cbm_assembled_total
                            record.final_cbm_flatpacked = record.final_cbm_flatpacked + group_cbm_flatpacked_total
                        record.final_total_delivery_cost = final_total_delivery_cost
                        record.final_total_installation_cost = final_total_installation_cost
    
    @api.model_create_multi
    def create(self, vals_list):
        res = super(DeliveryCodeCalculation, self).create(vals_list)
        model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if model and active_id:
            sale_order = self.env[model].browse(active_id)
            sale_order.delivery_code_calculation_id = res.id
        return res
                

            

    @api.model
    def default_get(self, fields_list):
        res = super(DeliveryCodeCalculation,self).default_get(fields_list)
        sale_order_id = self.env.context.get('active_id')
        if not sale_order_id:
            return res
        sale_order = self.env['sale.order'].browse(sale_order_id)

        lines = []
        for sol in sale_order.order_line:
            if not sol.is_downpayment:
                vals = {
                    'display_type': sol.display_type or False,
                    'name': sol.name if sol.display_type else False,
                    'product_id':  sol.product_template_id.id if sol.product_template_id else False,
                    'quantity': sol.product_uom_qty if sol.product_uom_qty else 0,
                    'line_group_name': sol.line_group_name,
                    'line_section_name': sol.line_section_name,
                    'line_group_id_value': sol.line_group_id_value,
                    'line_section_id_value': sol.line_section_id_value,
                    'sale_order_line_id': sol.id,
                }
                lines.append((0, 0, vals))
        res.update({
            'order_id': sale_order_id,
            'zone_type': sale_order.zone_type,
            'delivery_code_calculation_line_ids': lines,

        })
        return res

    
    # Logic to summarise Delivery Code Calculation
    @api.depends('delivery_code_calculation_line_ids','delivery_code_calculation_line_ids.quantity','delivery_code_calculation_line_ids.product_group_delivery_code_id')
    def _compute_summary_lines(self):
        for record in self:
            vals_list = []
            new_record_vals = {}
            qty = 0
            # Fetch Lines
            delivery_code_lines = record.delivery_code_calculation_line_ids
            if not delivery_code_lines:
                raise UserError(_('No Sale Order Lines Found!'))
            available_delivery_codes = delivery_code_lines.mapped('product_group_delivery_code_id')
            for code in available_delivery_codes:
                qty = sum(delivery_code_lines.filtered(lambda l: l.product_group_delivery_code_id.id == code.id).mapped('quantity'))
                new_record_vals = {
                        'delivery_code': code.delivery_code,
                        'delivery_code_description': code.description,
                        'total_quantity': qty,
                    }
                vals_list.append(new_record_vals)
                new_record_vals = {}
            record.delivery_code_calculation_summary_line_ids = [
                Command.clear(),
            ]
            for vals in vals_list:
                record.delivery_code_calculation_summary_line_ids = [
                Command.create(vals),
            ]
    
    def action_xlswriter_report(self):
        fp = BytesIO()
        file_name = 'Delivery Code Calculation Summary.xls'
        workbook = xlsxwriter.Workbook(fp,{'in_memory': True})
        sheet = workbook.add_worksheet()
        # Headers and style
        header_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'border': 2,  # 2 = thick border in xlsxwriter
        })

        headers = [
            'Delivery Code', 'Description', 'Total Quantity',
        ]

        # Set column widths

        column_widths = [25 for h in headers]
        for idx, width in enumerate(column_widths):
            sheet.set_column(idx, idx, width)

        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        
        delivery_summary_lines = self.delivery_code_calculation_summary_line_ids
        row = 1

        if not delivery_summary_lines:
            raise UserError(_('There are No Summary lines to export on Excel Sheet!'))
        if delivery_summary_lines:
            for record in delivery_summary_lines:
                sheet.write(row, 0, record.delivery_code or 'N/A') 
                sheet.write(row, 1, record.delivery_code_description or 'N/A')
                sheet.write(row, 2, record.total_quantity)
                row +=1
    
            workbook.close() #saves the file
            excel_file = base64.b64encode(fp.getvalue())
            file_name = file_name
            fp.close()

            # Store the binary data in the model field
            self.excel_file = excel_file
            self.file_name = file_name


            # Return file download action
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/delivery.code.calculation/{self.id}/excel_file/{file_name}?download=true',
                'target': 'self'
            }
    
    def force_compute_cbm_fields(self):
        for record in self:
            delivery_lines = record.delivery_code_calculation_line_ids
            if delivery_lines:
                for line in delivery_lines:
                    line._compute_cbm_assembled()
                    line._compute_cbm_flatpacked()
                 


class DeliveryCodeCalculationLine(models.Model):
    _name = 'delivery.code.calculation.line'
    _description = 'Delivery Code Calculation Line'
    
    name = fields.Char(compute="_compute_line_name",store=True)
    delivery_code_calculation_id = fields.Many2one('delivery.code.calculation', ondelete='cascade')
    product_id = fields.Many2one('product.template', string="Product Template")
    company_id = fields.Many2one('res.company', store=True, copy=False,
                                string="Company",
                                default=lambda self: self.env.user.company_id.id)

    currency_id = fields.Many2one('res.currency', string="Currency",
                                 related='company_id.currency_id',)
    product_group_delivery_code_id = fields.Many2one(related='product_variant_id.variant_delivery_code_selection_id', store=True)

    # ------------------------------------- CBM FIELDS -------------------------------
    # cbm_flatpacked = fields.Float(related='product_id.cbm_flatpacked', store=True)
    cbm_flatpacked = fields.Float(compute="_compute_cbm_flatpacked", store=True)

    # cbm_assembled = fields.Float(related='product_id.cbm_assembled', store=True)
    cbm_assembled = fields.Float(compute="_compute_cbm_assembled", store=True)

    total_cbm_flatpacked = fields.Float(compute="_compute_total_cbm_flatpacked", store=True)
    total_cbm_assembled = fields.Float(compute="_compute_total_cbm_assembled", store=True)

    # ------------------------------------ Delivery Cost Fields ------------------------
    # product_delivery_cost = fields.Monetary(related='product_group_delivery_code_id.delivery_code_cost', readonly=False, store=True)
    product_delivery_cost = fields.Monetary(compute="_compute_product_delivery_cost", readonly=False, store=True)
    # zone2_delivery_cost = fields.Monetary(related="product_group_delivery_code_id.zone2_delivery_cost", store=True, readonly=False)
    zone2_delivery_cost = fields.Monetary(compute="compute_zone2_delivery_cost", store=True, readonly=False)
    # zone3_delivery_cost = fields.Monetary(related="product_group_delivery_code_id.zone3_delivery_cost", store=True, readonly=False)
    zone3_delivery_cost = fields.Monetary(compute="compute_zone3_delivery_cost", store=True, readonly=False)
    total_delivery_cost = fields.Monetary(compute="_compute_total_delivery_cost", store=True)

    # -------------------------- Installation Cost Fields ----------------
    # installation_cost = fields.Monetary(related='product_group_delivery_code_id.installation_cost', store=True, readonly=False)
    installation_cost = fields.Monetary(compute="compute_installation_cost", store=True, readonly=False)
    # zone2_installation_cost = fields.Monetary(related='product_group_delivery_code_id.zone2_installation_cost', store=True, readonly=False)
    zone2_installation_cost = fields.Monetary(compute="compute_zone2_installation_cost", store=True, readonly=False)
    # zone3_installation_cost = fields.Monetary(related='product_group_delivery_code_id.zone3_installation_cost', store=True, readonly=False)
    zone3_installation_cost = fields.Monetary(compute="compute_zone3_installation_cost", store=True, readonly=False)
    total_installation_cost = fields.Monetary(compute="_compute_total_installation_cost", store=True)


    line_group_name = fields.Char(related='sale_order_line_id.line_group_name')
    line_section_name = fields.Char(related='sale_order_line_id.line_section_name')
    line_group_id_value = fields.Char(related='sale_order_line_id.line_group_id_value')
    line_section_id_value = fields.Char(related='sale_order_line_id.line_section_id_value')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note"),
        ('line_group', "Group"),
    ], string="Display Type")

    # ------------------------------------- FINAL TOTAL FIELDS -------------------------------------
    total_cost = fields.Monetary()
    total_cbm_flatpacked_final = fields.Float()
    total_cbm_assembled_final = fields.Float()

    # ------------------------------- FIELDS FOR SAME BEHAVIOUR IN MODEL -------------------------

    sale_order_line_id = fields.Many2one('sale.order.line', ondelete='cascade')

    sequence = fields.Integer(related='sale_order_line_id.sequence')

    quantity = fields.Float(related="sale_order_line_id.product_uom_qty")

    product_variant_id = fields.Many2one(related="sale_order_line_id.product_id", string="Product Variant", store=True)    


    is_manual_edit = fields.Boolean(default=False,store=True)

    # ------------------------------------  COMPUTED FIELDS TO RELATED FIELDS ---------------------------------------

    @api.depends('product_variant_id.cbm_flatpacked')
    def _compute_cbm_flatpacked(self):
         for rec in self:
            if rec.product_variant_id:
                rec.cbm_flatpacked = rec.product_variant_id.variant_cbm_flatpacked
            else:
                rec.cbm_flatpacked = 0.0

    @api.depends('product_variant_id.cbm_assembled')
    def _compute_cbm_assembled(self):
         for rec in self:
            if rec.product_variant_id:
                rec.cbm_assembled = rec.product_variant_id.variant_cbm_assembled
            else:
                rec.cbm_flatpacked = 0.0
    
    @api.depends('product_group_delivery_code_id.delivery_code_cost')
    def _compute_product_delivery_cost(self):
        for rec in self:
            if rec.product_group_delivery_code_id:
                rec.product_delivery_cost = rec.product_group_delivery_code_id.delivery_code_cost
            else:
                rec.product_delivery_cost = 0.0
    
    @api.depends('product_group_delivery_code_id.zone2_delivery_cost')
    def compute_zone2_delivery_cost(self):
        for rec in self:
            if rec.product_group_delivery_code_id:
                rec.zone2_delivery_cost = rec.product_group_delivery_code_id.zone2_delivery_cost
            else:
                rec.zone2_delivery_cost = 0.0

    @api.depends('product_group_delivery_code_id.zone3_delivery_cost')
    def compute_zone3_delivery_cost(self):
        for rec in self:
            if rec.product_group_delivery_code_id:
                rec.zone3_delivery_cost = rec.product_group_delivery_code_id.zone3_delivery_cost
            else:
                rec.zone3_delivery_cost = 0.0
    
    @api.depends('product_group_delivery_code_id.installation_cost')
    def compute_installation_cost(self):
        for rec in self:
            if rec.product_group_delivery_code_id:
                rec.installation_cost = rec.product_group_delivery_code_id.installation_cost
            else:
                rec.installation_cost = 0.0
    
    @api.depends('product_group_delivery_code_id.zone2_installation_cost')
    def compute_zone2_installation_cost(self):
        for rec in self:
            if rec.product_group_delivery_code_id:
                rec.zone2_installation_cost = rec.product_group_delivery_code_id.zone2_installation_cost
            else:
                rec.zone2_installation_cost = 0.0
    
    @api.depends('product_group_delivery_code_id.zone3_installation_cost')
    def compute_zone3_installation_cost(self):
        for rec in self:
            if rec.product_group_delivery_code_id:
                rec.zone3_installation_cost = rec.product_group_delivery_code_id.zone3_installation_cost
            else:
                rec.zone3_installation_cost = 0.0
    

    
    

    @api.onchange('cbm_flatpacked', 'cbm_assembled', 'installation_cost', 'product_delivery_cost', 'zone2_installation_cost', 'zone2_delivery_cost', 'zone3_installation_cost', 'zone3_delivery_cost')
    def _set_is_manual_edit(self):
        for record in self:
            if record.cbm_assembled or record.cbm_assembled or record.installation_cost or record.product_delivery_cost or record.zone2_installation_cost or record.zone2_delivery_cost or record.zone3_delivery_cost or record.zone3_installation_cost:
                record.is_manual_edit = True

    @api.depends("sale_order_line_id.name")
    def _compute_line_name(self):
        for record in self:
            record.name = record.sale_order_line_id.name

    @api.depends("delivery_code_calculation_id.zone_type","product_delivery_cost","zone2_delivery_cost","zone3_delivery_cost","quantity")
    def _compute_total_delivery_cost(self):
        for record in self:
            total_delivery_cost = 0
            if record.delivery_code_calculation_id.zone_type == 'zone1':
                total_delivery_cost = record.quantity * record.product_delivery_cost
                # total_delivery_cost = record.quantity * record.product_group_delivery_code_id.delivery_code_cost
                record.total_delivery_cost = total_delivery_cost
            elif record.delivery_code_calculation_id.zone_type == 'zone2':
                # total_delivery_cost = record.quantity * record.product_group_delivery_code_id.zone2_delivery_cost
                total_delivery_cost = record.quantity * record.zone2_delivery_cost
                record.total_delivery_cost = total_delivery_cost
            elif record.delivery_code_calculation_id.zone_type == 'zone3':
                # total_delivery_cost = record.quantity * record.product_group_delivery_code_id.zone3_delivery_cost
                total_delivery_cost = record.quantity * record.zone3_delivery_cost
                record.total_delivery_cost = total_delivery_cost
            else:
                record.total_delivery_cost = total_delivery_cost

    @api.depends("delivery_code_calculation_id.zone_type","installation_cost","zone2_installation_cost", "zone3_installation_cost", "quantity")
    def _compute_total_installation_cost(self):
        for record in self:
            total_installation_cost = 0
            if record.delivery_code_calculation_id.zone_type == 'zone1':
                total_installation_cost = record.quantity * record.installation_cost
                record.total_installation_cost = total_installation_cost
            elif record.delivery_code_calculation_id.zone_type == 'zone2':
                total_installation_cost = record.quantity * record.zone2_installation_cost
                record.total_installation_cost = total_installation_cost
            elif record.delivery_code_calculation_id.zone_type == 'zone3':
                total_installation_cost = record.quantity * record.zone3_installation_cost
                record.total_installation_cost = total_installation_cost
            else:
                record.total_installation_cost = total_installation_cost
                
    
    @api.depends('cbm_flatpacked','quantity')
    def _compute_total_cbm_flatpacked(self):
        for record in self:
            record.total_cbm_flatpacked = record.cbm_flatpacked * record.quantity

    @api.depends('cbm_assembled','quantity')
    def _compute_total_cbm_assembled(self):
        for record in self:
            record.total_cbm_assembled = record.cbm_assembled * record.quantity
    

    
class DeliveryCodeCalculationSummaryLine(models.Model):
    _name='delivery.code.calculations.summary.line'
    _description = "Shows Total Summary Of Delivery Codes and Its Quantities"

    delivery_code_calculation_id = fields.Many2one('delivery.code.calculation', ondelete='cascade')
    delivery_code = fields.Char()
    delivery_code_description = fields.Text()
    total_quantity = fields.Float()

