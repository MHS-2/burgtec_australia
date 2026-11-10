import json
from odoo import http
from odoo.http import request

class WarehouseWebhook(http.Controller):

    # this controller will receive the call from warehouse odoo 19 instance when create or write method of product.product is triggered.
    # api call will have a token in param if the token is same as the token saved on this side, it means it is a authenticate call

    @http.route('/warehouse/product_sync', type='http', auth='public',methods=['POST'], csrf=False)
    def product_sync(self, token=None, **kw):
        icp = request.env['ir.config_parameter'].sudo()
        webhook_auth_token = (icp.get_param('burgtec_warehouse_integration.burgtec_webhook_authentication_token') or '')
        if token != webhook_auth_token:
            return request.make_response('forbidden', status=403)

        data = json.loads(request.httprequest.get_data() or b'{}')
        code = (data.get('default_code') or '').strip()
        if code:
            products = request.env['product.product'].sudo().search(
                [('default_code', '=', code),('variant_bom_type','=','components')])
            products.write({'is_present_in_warehouse': True})
        return request.make_response('ok')