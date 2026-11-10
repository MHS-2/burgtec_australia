from odoo import models, fields, api, _


class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    pdf_report_name = fields.Char(compute="_compute_pdf_report_name",readonly=False, store=True)
    burgtec_quote_reference = fields.Char(string="Burgtec Reference", compute="_compute_new_sale_ref", store=True)
    # site_address = fields.Char(string="Site Address")



    def update_vendor_of_all_quotations(self):
        for record in self:
            component_lines = record.bom_component_id.component_line_ids.filtered(
                lambda l: not l.display_type
            )
            for line in component_lines:
                if line.product_id.seller_ids:
                    seller = line.product_id.seller_ids[0]
                    line.write({
                        'supplier_id': seller.partner_id.id
                    })



    def _attach_sale_orders_with_old_crm_lead(self):
        crm_data = self.env['crm.lead'].search_read(
            fields=['id', 'odoo_deal_number_6digit']
        )
        crm_map = {
            lead['odoo_deal_number_6digit']: lead['id']
            for lead in crm_data
            if lead['odoo_deal_number_6digit']
        }
        for order in self:
            if order.burgtec_quote_reference:
                ref = order.burgtec_quote_reference.split("-")[0].strip()
                if ref:
                    lead_id = crm_map.get(ref)
                    if lead_id:
                        order.opportunity_id = lead_id

    def action_view_opportunity(self):
        self.ensure_one()
        return {
            'name': _('Deal'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'res_id': self.opportunity_id.id,
        }
    

    @api.depends('burgtec_quote_reference','project_name','opportunity_id')
    def _compute_pdf_report_name(self):
        for record in self:
            if not record.burgtec_quote_reference and record.opportunity_id:
                record.pdf_report_name = f"Burgtec - {record.opportunity_id.odoo_deal_number_6digit}"
            else:
                record.pdf_report_name = f"Burgtec - {record.burgtec_quote_reference}"
            # if not record.project_name:
            #     record.pdf_report_name = f"Burgtec - {record.burgtec_quote_reference}"
            # if record.project_name and record.manual_rev:
            #     record.pdf_report_name = f"{record.project_name} - {record.manual_rev}"
            # elif record.project_name and not record.manual_rev:
            #     record.pdf_report_name = f"{record.project_name}"
    
    @api.depends('new_sale_order_number', 'system_revision', 'is_old_data','project_name')
    def _compute_new_sale_ref(self):
        for record in self:
            if record.quote_type == 'delivery_stage':
                if record.is_old_data:
                    # Use hubspot_reference logic
                    if record.hubspot_reference:
                        record.burgtec_quote_reference = record.hubspot_reference
                    else:
                        record.burgtec_quote_reference = False
                else:
                    if record.new_sale_order_number:
                        record.burgtec_quote_reference = record.new_sale_order_number
                    else:
                        record.burgtec_quote_reference = False
            if record.quote_type not in ('project_quote','delivery_stage'):
                if record.is_old_data:
                    # Use hubspot_reference logic
                    if record.hubspot_reference and not record.system_revision:
                        record.burgtec_quote_reference = record.hubspot_reference
                    elif record.system_revision and not record.hubspot_reference:
                        record.burgtec_quote_reference = record.system_revision
                    elif record.hubspot_reference and record.system_revision:
                        record.burgtec_quote_reference = f"{record.hubspot_reference}-{record.system_revision}"
                    else:
                        record.burgtec_quote_reference = False
                else:
                    # Use new_sale_order_number logic
                    if record.new_sale_order_number and not record.system_revision:
                        if not record.project_name:
                            record.burgtec_quote_reference = record.new_sale_order_number
                        else:
                            record.burgtec_quote_reference = f"{record.new_sale_order_number} - {record.project_name}"
                    elif record.system_revision and not record.new_sale_order_number:
                        record.burgtec_quote_reference = record.system_revision
                    elif record.new_sale_order_number and record.system_revision and not record.project_name:
                        record.burgtec_quote_reference = f"{record.new_sale_order_number} {record.system_revision}"
                    elif record.new_sale_order_number and record.system_revision and record.project_name:
                        record.burgtec_quote_reference = f"{record.new_sale_order_number} {record.system_revision} - {record.project_name}"
                    else:
                        record.burgtec_quote_reference = False
    
    
                


