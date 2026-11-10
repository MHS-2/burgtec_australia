# -*- coding: utf-8 -*-
import ast
from odoo import http,_
from odoo.http import request
import json


class CopilotStudioAgentConnector(http.Controller):

    @http.route(
        route='/create_lead',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def create_lead(self, **kwargs):
        lead = False
        raw_data = request.httprequest.data
        res_partner_object = request.env['res.partner'].sudo()
        res_country_object = request.env['res.country'].sudo()
        sale_order_series_object = request.env['sale.order.series'].sudo()
        partner_rec = False
        country_rec = False
        sale_series_rec = False

        data = json.loads(raw_data)   # bytes → string
        data = ast.literal_eval(data) # string with single quotes → dict


        params = data.get('params', {})
        kwargs_ = params.get('kwargs', {})

        if kwargs_:

            country_rec = res_country_object.search([
                ('name','ilike',kwargs_.get('country'))
            ],limit=1)
            

            #  Create Partner If not exist otherwise use the one in odoo.
            partner_rec = res_partner_object.search([
                ('name','=',kwargs_.get('name')),
                ('email','=',kwargs_.get('email_from')),
                # ('country_id','=',country_rec.id)
            ],limit=1)
            if not partner_rec:
                partner_rec = res_partner_object.create({
                    'name': kwargs_.get('name'),
                    'email': kwargs_.get('email_from'),
                    'phone': kwargs_.get('phone'),
                    'city':  kwargs_.get('city'),
                    'company_type': 'company',
                    'country_id': country_rec.id if country_rec else False
                })
            sale_series_rec = sale_order_series_object.search([
                ('sequence','=',kwargs_.get('series_number_first_digit'))
            ])
            if not sale_series_rec:
                return request.make_json_response({
                'success': False,
                'error': 'Sequence Series Digit Not Valid'
            })
            
            lead = request.env['crm.lead'].sudo().create({
                'series_sequence_id': sale_series_rec.id,
                'project_name': kwargs_.get('project_name'),
                'partner_id': partner_rec.id,
            })

            lead.message_post(
                    body=(_('Lead Created From Micrsoft Copilot Studio.')),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note')
            
            lead.action_generate_deal_number()

        return request.make_json_response({
            'success': True,
            'lead_id': lead.id if lead else False,
        })
    
    def _prepare_opportunity_quotation_vals(self,oppotunity):
        """ Prepares the vals for a new quotation (sale.order) by sharing the values of common fields """
        quotation_vals = {
            'opportunity_id': oppotunity.id,
            'partner_id': oppotunity.partner_id.id,
            'campaign_id': oppotunity.campaign_id.id,
            'medium_id': oppotunity.medium_id.id,
            'origin': oppotunity.name,
            'source_id': oppotunity.source_id.id,
            'company_id': oppotunity.company_id.id or oppotunity.env.company.id,
            'tag_ids': [(6, 0, oppotunity.tag_ids.ids)],
            'new_sale_order_number': oppotunity.odoo_deal_number_6digit,
            'project_name': oppotunity.project_name,
        }
        if oppotunity.team_id:
            quotation_vals['team_id'] = oppotunity.team_id.id
        if oppotunity.user_id:
            quotation_vals['user_id'] = oppotunity.user_id.id
        return quotation_vals
    
    @http.route(
        route='/create_sale_quote',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def create_sale_quote(self, **kwargs):
        error_message = ''
        success_message = ''
        res = False
        lead = False
        root_url = ''
        record_url = ''
        sale_order_vals = {}
        raw_data = request.httprequest.data
        opportunity_object = request.env['crm.lead'].sudo()
        sale_order_object = request.env['sale.order'].sudo()

        data = json.loads(raw_data)   # bytes → string
        data = ast.literal_eval(data) # string with single quotes → dict 

        params = data.get('params', {})
        kwargs_ = params.get('kwargs', {})

        if kwargs_:
            # Fetching Lead, Because Sale Quote Needs A Opportunity Lead.
            lead = opportunity_object.search([
                ('odoo_deal_number_6digit','=',kwargs_.get('odoo_six_digit_number'))
            ],limit=1)

            if not lead:
                return request.make_json_response({
                    'success': False,
                    'Error': f"Deal with number {kwargs_.get('odoo_six_digit_number')} was not found in Odoo. Create Opportunity First Then Create its Sale Quote!"
                })
            
            if lead and not lead.is_deal_imported:
                error_message = f"Deal with number {lead.odoo_deal_number_6digit} was not imported from hubspot in Odoo."
                return request.make_json_response({
                    'success': False,
                    'error': error_message
                })
            if lead and lead.is_deal_imported:
                if lead.order_ids:
                    error_message = f"Could not create Quotation in Odoo for the deal with number {lead.odoo_deal_number_6digit}, It already have Sale Quotes Created."
                    return request.make_json_response({
                        'success': False,
                        'error': error_message
                    })

                sale_order_vals = self._prepare_opportunity_quotation_vals(lead)
                res = sale_order_object.create(sale_order_vals)
                if not res:
                    error_message = f"Could not create Quotation in Odoo for the deal with number {lead.odoo_deal_number_6digit}"
                    return request.make_json_response({
                        'success': False,
                        'error': error_message
                    })
                if res:
                    res.message_post(
                    body=(_('Sales Order, Created From Micrsoft Copilot Studio.')),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note')
                    root_url = request.httprequest.url_root
                    record_url = f"{root_url}odoo/orders/{res.id}"
                    return request.make_json_response(record_url)
    
    @http.route(route='/get_sale_order', type='http', auth='public', methods=['POST'], csrf=False)
    def get_sales_order(self, **kwargs):
        sale_order_object = request.env['sale.order'].sudo()
        sale_order = False
        quote_type = ''
        domain = []
        sale_order_list = []

        raw_data = request.httprequest.data

        data = json.loads(raw_data)   # bytes → string
        data = ast.literal_eval(data) # string with single quotes → dict 

        # data = json.loads(data)
        params = data.get('params', {})
        kwargs_ = params.get('kwargs', {})

        if kwargs_:
            if kwargs_.get('quote_Type') == 'Sales Quote':
                quote_type = 'sales_quote'
            elif kwargs_.get('quote_Type') == 'Project Quote':
                quote_type = 'project_quote'
            domain = [
                ('quote_type','=', quote_type),
                ('new_sale_order_number','=', kwargs_.get('sale_reference'))
            ]
            # if kwargs_.get('revision') != 'No Revision':
            #     domain = [
            #     ('quote_type','=', quote_type),
            #     ('new_sale_order_number','=', kwargs_.get('sale_reference')),
            #     ('system_revision','=',kwargs_.get('revision'))
            # ]
            sale_order = sale_order_object.search(domain=domain)

            if not sale_order:
                return request.make_json_response({
                    'success': False,
                    'Error': f"No Sale Order Found In Odoo To Add Products."
                })
            
            if sale_order:
                sale_order_list = sale_order.mapped('burgtec_quote_reference')
                return request.make_json_response(sale_order_list)
    
    @http.route(route='/get_sale_order_groups', type='http', auth='public', methods=['POST'], csrf=False)
    def get_sales_order_groups(self, **kwargs):
        sale_order_object = request.env['sale.order'].sudo()
        sale_order = False
        order_lines = False
        quote_type = ''
        domain = []
        groups = []

        raw_data = request.httprequest.data

        data = json.loads(raw_data)   # bytes → string
        data = ast.literal_eval(data) # string with single quotes → dict 

        params = data.get('params', {})
        kwargs_ = params.get('kwargs', {})

        if kwargs_:
            # if kwargs_.get('quote_Type') == 'Sales Quote':
            #     quote_type = 'sales_quote'
            # elif kwargs_.get('quote_Type') == 'Project Quote':
            #     quote_type = 'project_quote'
            domain = [('burgtec_quote_reference','=',kwargs_.get('selected_sale_order'))]
            # if kwargs_.get('revision') != 'No Revision':
            #     domain = [
            #     ('quote_type','=', quote_type),
            #     ('new_sale_order_number','=', kwargs_.get('sale_reference')),
            #     ('system_revision','=',kwargs_.get('revision'))
            # ]
            sale_order = sale_order_object.search(domain=domain)
            order_lines = sale_order.order_line

            if not order_lines:
                return request.make_json_response({
                    'success': False,
                    'Error': f"No Sale Order Lines Found In Sales Order {sale_order.burgtec_quote_reference}."
                })
            
            if order_lines:
                groups = order_lines.filtered(lambda ol:ol.display_type == 'line_section').mapped('name')
                return request.make_json_response(groups)
        

    @http.route(route='/get_sale_order_codes', type='http', auth='public', methods=['POST'], csrf=False)
    def get_sales_order_codes(self, **kwargs):
        sale_order_object = request.env['sale.order'].sudo()
        sale_order = False
        order_lines = False
        quote_type = ''
        domain = []
        codes = []

        raw_data = request.httprequest.data

        data = json.loads(raw_data)   # bytes → string
        data = ast.literal_eval(data) # string with single quotes → dict ✅

        params = data.get('params', {})
        kwargs_ = params.get('kwargs', {})

        if kwargs_:
            # if kwargs_.get('quote_Type') == 'Sales Quote':
            #     quote_type = 'sales_quote'
            # elif kwargs_.get('quote_Type') == 'Project Quote':
            #     quote_type = 'project_quote'
            domain = [('burgtec_quote_reference','=',kwargs_.get('selected_sale_order'))]
            # if kwargs_.get('revision') != 'No Revision':
            #     domain = [
            #     ('quote_type','=', quote_type),
            #     ('new_sale_order_number','=', kwargs_.get('sale_reference')),
            #     ('system_revision','=',kwargs_.get('revision'))
            # ]
            sale_order = sale_order_object.search(domain=domain)
            order_lines = sale_order.order_line.filtered(lambda ol: ol.line_group_name == kwargs_.get('selected_group') and ol.display_type == 'line_note')

            if not order_lines:
                return request.make_json_response({
                    'success': False,
                    'Error': f"No Sale Order Lines Found In Sales Order {sale_order.burgtec_quote_reference}."
                })
            
            if order_lines:
                codes = order_lines.mapped('name')
                return request.make_json_response(codes)
        
    @http.route(route='/add_products', type='http', auth='public', methods=['POST'], csrf=False)
    def add_products_to_sales_order(self, **kwargs):
        sale_order_object = request.env['sale.order'].sudo()
        sale_order = False
        domain = []
        vals_list = []
        vals = {}
        sequence= 10
        root_url = ''
        record_url = ''
        product_obj=False
        product_default_code = ''
        product_list = []
        order_lines = []

        raw_data = request.httprequest.data

        data = json.loads(raw_data)   # bytes → string
        data = ast.literal_eval(data) # string with single quotes → dict ✅
        params = data.get('params', {})
        kwargs_ = params.get('kwargs', {})
        if kwargs_:
            product_list = kwargs_.get('products',[])
            sale_order = sale_order_object.search([
                    ('burgtec_quote_reference','=',kwargs_.get('selected_sale_order'))
                ])
            order_lines = sale_order.order_line.sorted(lambda o:o.sequence)


            if sale_order:
                if not order_lines:
                    # Group
                    vals = {
                        'order_id': sale_order.id,
                        'name': kwargs_.get('product_group'),
                        'display_type': 'line_section',
                        'sequence': sequence
                    }
                    vals_list.append(vals)
                    vals = {}
                    # Code
                    sequence+=1
                    vals = {
                        'order_id': sale_order.id,
                        'name': kwargs_.get('product_code'),
                        'display_type': 'line_note',
                        'sequence': sequence
                    }
                    vals_list.append(vals)
                    vals = {}
                    if product_list:
                        for product_data in product_list:
                            product_default_code = product_data['product_default_code'].replace('\n', '').replace('\r', '').strip()
                            product_obj = request.env['product.product'].sudo().search([
                                ('default_code','=',product_default_code),
                            ],limit=1)

                            if not product_obj:
                                return request.make_json_response({
                                    'success': False,
                                    'Error': f"No Product Found With Internal Reference {product_default_code}"
                                })
                            # Product
                            sequence+=1
                            vals = {
                                'order_id': sale_order.id,
                                'product_id': product_obj.id if product_obj else False,
                                'product_uom_qty': int(product_data['qty']),
                                'sequence': sequence,
                            }
                            vals_list.append(vals)
                            vals={}
                if order_lines:
                    # Product Line
                    if not order_lines[-1].display_type: 
                        sequence = order_lines[-1].sequence + 1
                         # Group
                        vals = {
                            'order_id': sale_order.id,
                            'name': kwargs_.get('product_group'),
                            'display_type': 'line_section',
                            'sequence': sequence
                        }
                        vals_list.append(vals)
                        vals = {}
                        # Code
                        sequence+=1
                        vals = {
                            'order_id': sale_order.id,
                            'name': kwargs_.get('product_code'),
                            'display_type': 'line_note',
                            'sequence': sequence
                        }
                        vals_list.append(vals)
                        vals = {}
                        # Product

                        if product_list:
                            for product_data in product_list:
                                product_default_code = product_data['product_default_code'].replace('\n', '').replace('\r', '').strip()
                                product_obj = request.env['product.product'].sudo().search([
                                    ('default_code','=',product_default_code),
                                ])

                                if not product_obj:
                                    return request.make_json_response({
                                        'success': False,
                                        'Error': f"No Product Found With Internal Reference {product_default_code}"
                                    })
                                # Product
                                sequence+=1
                                vals = {
                                    'order_id': sale_order.id,
                                    'product_id': product_obj.id if product_obj else False,
                                    'product_uom_qty': int(product_data['qty']),
                                    'sequence': sequence,
                                }
                                vals_list.append(vals)
                                vals={}
                if vals_list:
                    request.env['sale.order.line'].sudo().create(vals_list)

                root_url = request.httprequest.url_root
                record_url = f"{root_url}odoo/orders/{sale_order.id}"
                return request.make_json_response(record_url)

    @http.route(route='/add_code_with_products', type='http', auth='public', methods=['POST'], csrf=False)
    def add_code_with_products_to_sales_order(self, **kwargs):
        sale_order_object = request.env['sale.order'].sudo()
        sale_order = False
        domain = []
        vals_list = []
        vals = {}
        sequence= 10
        last_line_sequence = 10
        root_url = ''
        record_url = ''
        product_obj=False
        product_default_code = ''
        product_list = []
        order_lines = []
        specific_group_order_lines = []
        order_lines_to_update = False

        raw_data = request.httprequest.data

        data = json.loads(raw_data)   # bytes → string
        data = ast.literal_eval(data) # string with single quotes → dict ✅


        params = data.get('params', {})
        kwargs_ = params.get('kwargs', {})

        if kwargs_:
            product_list = kwargs_.get('products',[])
            sale_order = sale_order_object.search([
                    ('burgtec_quote_reference','=',kwargs_.get('selected_sale_order'))
                ])
                
            order_lines = sale_order.order_line.sorted(lambda o:o.sequence)
            specific_group_order_lines = order_lines.filtered(lambda ol: ol.line_group_name == kwargs_.get('product_group','')).sorted(lambda o:o.sequence)
            
            if sale_order:
                if specific_group_order_lines:
                    # Product Line
                    if not specific_group_order_lines[-1].display_type: 
                        last_line_sequence = specific_group_order_lines[-1].sequence
                        sequence = specific_group_order_lines[-1].sequence + 1
                        # Code
                        vals = {
                            'order_id': sale_order.id,
                            'name': kwargs_.get('product_code'),
                            'display_type': 'line_note',
                            'sequence': sequence
                        }
                        vals_list.append(vals)
                        vals = {}
                        # Product
                        if product_list:
                            for product_data in product_list:
                                product_default_code = product_data['product_default_code'].replace('\n', '').replace('\r', '').strip()
                                product_obj = request.env['product.product'].sudo().search([
                                    ('default_code','=',product_default_code),
                                ],limit=1)

                                if not product_obj:
                                    return request.make_json_response({
                                        'success': False,
                                        'Error': f"No Product Found With Internal Reference {product_default_code}"
                                    })
                                # Product
                                sequence+=1
                                vals = {
                                    'order_id': sale_order.id,
                                    'product_id': product_obj.id if product_obj else False,
                                    'product_uom_qty': int(product_data['qty']),
                                    'sequence': sequence,
                                }
                                vals_list.append(vals)
                                vals={}
                            
                            order_lines_to_update = order_lines.filtered(lambda ol:ol.sequence > last_line_sequence)
                            if order_lines_to_update:
                                sequence+=1
                                for line in order_lines_to_update:
                                    line.sequence=sequence
                                    sequence+=1 
                if vals_list:
                    request.env['sale.order.line'].sudo().create(vals_list)

                root_url = request.httprequest.url_root
                record_url = f"{root_url}odoo/orders/{sale_order.id}"
                return request.make_json_response(record_url)
    
    @http.route(route='/add_products_in_group_code', type='http', auth='public', methods=['POST'], csrf=False)
    def add_products_in_group_code_to_sales_order(self, **kwargs):
        sale_order_object = request.env['sale.order'].sudo()
        sale_order = False
        domain = []
        vals_list = []
        vals = {}
        sequence= 10
        last_line_sequence = 10
        root_url = ''
        record_url = ''
        product_obj=False
        product_default_code = ''
        product_list = []
        order_lines = []
        specific_code_order_lines = []
        order_lines_to_update = False

        raw_data = request.httprequest.data

        data = json.loads(raw_data)   # bytes → string
        data = ast.literal_eval(data) # string with single quotes → dict ✅

        params = data.get('params', {})
        kwargs_ = params.get('kwargs', {})

        if kwargs_:
            product_list = kwargs_.get('products',[])
            sale_order = sale_order_object.search([
                    ('burgtec_quote_reference','=',kwargs_.get('selected_sale_order'))
                ])
                
            order_lines = sale_order.order_line.sorted(lambda o:o.sequence)
            specific_code_order_lines = order_lines.filtered(lambda ol: ol.line_group_name == kwargs_.get('product_group','') and ol.line_section_name == kwargs_.get('product_code','')).sorted(lambda o:o.sequence)
            
            if sale_order:
                if specific_code_order_lines:
                    # Product Line
                    if not specific_code_order_lines[-1].display_type: 
                        last_line_sequence = specific_code_order_lines[-1].sequence
                        sequence = specific_code_order_lines[-1].sequence + 1
                        # Product
                        if product_list:
                            for product_data in product_list:
                                product_default_code = product_data['product_default_code'].replace('\n', '').replace('\r', '').strip()
                                product_obj = request.env['product.product'].sudo().search([
                                    ('default_code','=',product_default_code),
                                ],limit=1)

                                if not product_obj:
                                    return request.make_json_response({
                                        'success': False,
                                        'Error': f"No Product Found With Internal Reference {product_default_code}"
                                    })
                                # Product
                                vals = {
                                    'order_id': sale_order.id,
                                    'product_id': product_obj.id if product_obj else False,
                                    'product_uom_qty': int(product_data['qty']),
                                    'sequence': sequence,
                                }
                                vals_list.append(vals)
                                vals={}
                                sequence+=1
                            
                            order_lines_to_update = order_lines.filtered(lambda ol:ol.sequence > last_line_sequence)
                            if order_lines_to_update:
                                for line in order_lines_to_update:
                                    line.sequence=sequence
                                    sequence+=1 
                if vals_list:
                    request.env['sale.order.line'].sudo().create(vals_list)

                root_url = request.httprequest.url_root
                record_url = f"{root_url}odoo/orders/{sale_order.id}"
                return request.make_json_response(record_url)



        


                
    

        

