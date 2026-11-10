import json
from werkzeug.exceptions import NotFound
from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount, format_date, formatLang


class QuotationReviewController(http.Controller):

    def _get_quotation_by_token(self, token):
        if not token or len(token) < 20:
            return request.env["sale.order"]
        return request.env["sale.order"].sudo().search(
            [("quotation_review_token", "=", token), ("state", "!=", "cancel")], limit=1)

    @http.route("/quote/review/<string:token>", website=True, type="http", auth="public",
                methods=["GET"], sitemap=False)
    def quotation_review(self, token, **kw):
        order = self._get_quotation_by_token(token)
        if not order:
            return request.not_found()

        return request.render("burgtec_online_quotation_link.quotation_review_page", {
            "order": order,
            "main_object": order,
            "props_json": json.dumps({"token": token}),
        })

    @http.route("/quote/review/<string:token>/data", type="json", auth="public",
                methods=["POST"])
    def quotation_review_data(self, token, **kw):
        order = self._get_quotation_by_token(token)
        if not order:
            raise NotFound()
        order_type = order.quote_type
        env = request.env
        currency = order.currency_id
        partner = order.partner_id
        approved_lines = 0
        revision_required_lines = 0
        incomplete_lines = 0
        validations = ''
        lines = []
        atr_vals = {}
        value_vals = {}
        planning_line = False
        if order and order.is_frozen_due_to_project_creation:
            validations = "The quotation you are trying to access is not available anymore. Contact sales person for latest link of quotation."
            return {
                "order": {},
                "customer": {},
                "lines": False,
                "validations": validations,
                "feedback_totals": {},
            }
        if order_type == 'sales_quote':
            planning_line = order.sale_quote_planning_screen_id.sale_quote_line_ids
        elif order_type == 'project_quote':
            planning_line = order.planning_screen_id.line_ids.filtered(lambda l: not l.is_fully_approved)
        if not planning_line:
            validations = "Quotation is Empty"
            return {
                "order": {},
                "customer": {},
                "lines": False,
                "validations": validations,
                "feedback_totals": {},
            }

        for line in planning_line:
            order_line = line.order_line_id
            user_selected_ptav_ids = order_line.user_selected_ptav_ids
            user_selected = False
            if user_selected_ptav_ids and line.user_feedback:
                user_selected = True
            attribute_data = []
            selected_pav_ids = []

            if not order_line.user_feedback:
                incomplete_lines += 1
            elif order_line.user_feedback == 'approve':
                approved_lines += 1
            elif order_line.user_feedback == 'rev_required':
                revision_required_lines += 1
            attributes_and_value = {}
            product_tmpl_id = order_line.product_id.product_tmpl_id
            if product_tmpl_id:
                product_attributes = product_tmpl_id.attribute_line_ids
                if product_attributes:
                    selected_pav_ids = (order_line.product_template_attribute_value_ids
                                        | order_line.product_no_variant_attribute_value_ids
                                        ).product_attribute_value_id.ids  # -> [103, 104, 107]

                    for attribute in product_attributes:
                        atr_vals = {
                            'id': attribute.id,
                            'name': attribute.attribute_id.name,
                        }
                        value_data = []
                        for val in attribute.value_ids:
                            value_vals = {
                                'id': val.id,
                                'value': val.name,
                            }
                            value_data.append(value_vals)
                        atr_vals.update({'values': value_data})
                        attribute_data.append(atr_vals)

            vals = {
                "id": order_line.id,
                "display_type": order_line.display_type or False,
                "name": order_line.name,
            }
            if not order_line.display_type:
                vals.update({
                    "product_name": order_line.product_id.display_name,
                    "public_comment": order_line.public_comment,
                    "user_feedback": order_line.user_feedback,
                    "qty": formatLang(env, order_line.product_uom_qty, dp="Product Unit of Measure"),
                    "uom": order_line.product_uom.name,
                    "price_unit": format_amount(env, order_line.price_unit, currency),
                    "discount": formatLang(env, order_line.discount) if order_line.discount else False,
                    "subtotal": format_amount(env, order_line.price_subtotal, currency),
                    "image_url": f"/quote/review/{token}/image/{order_line.id}" if order_line.image_128 else False,
                    'attributes_and_values': attribute_data,
                    'selected_value_ids': selected_pav_ids if not user_selected_ptav_ids else user_selected_ptav_ids,
                    'artwork_image_url': line.artwork_image_url,
                    'user_selected': user_selected,
                })
            lines.append(vals)
        return {
            "order": {
                "name": order.name,
                "date": format_date(env, order.date_order),
                "validity_date": format_date(env, order.validity_date) if order.validity_date else False,
                "salesperson": order.user_id.name or "",
                "salesperson_email": order.user_id.email or "",
                "amount_untaxed": format_amount(env, order.amount_untaxed, currency),
                "amount_tax": format_amount(env, order.amount_tax, currency),
                "amount_total": format_amount(env, order.amount_total, currency),
            },
            "customer": {
                "name": partner.display_name,
                "address": partner._display_address(without_company=True).strip(),
                "email": partner.email or "",
                "phone": partner.phone or "",
            },
            "lines": lines,
            "validations": validations,
            "feedback_totals": {
                "approved_lines": approved_lines,
                "revision_required_lines": revision_required_lines,
                "incomplete_lines": incomplete_lines,
                "total_items": approved_lines + revision_required_lines + incomplete_lines,
            },
        }

    # get sale order line of the order related to token (used by comment and feedback)
    def _get_line_by_token(self, token, line_id):
        order = self._get_quotation_by_token(token)
        if not order or order.is_frozen_due_to_project_creation:
            raise NotFound()
        line = order.order_line.filtered(lambda l: l.id == line_id)
        if not line or line.display_type:
            raise NotFound()
        return line

    @http.route("/quote/review/<string:token>/line/<int:line_id>/comment", type="json",
                auth="public", methods=["POST"])
    def quotation_review_line_comment(self, token, line_id, comment=None, **kw):
        line = self._get_line_by_token(token, line_id)
        line.update_sale_order_line_comment(comment or False)
        return {"ok": True}
    
    @http.route("/quote/review/<string:token>/line/<int:line_id>/update_user_ptav", type="json",
                    auth="public", methods=["POST"])
    def quotation_review_line_update_user_ptav(self, token, line_id, attribute_id=False, attribute_values=False, **kw):
        order = self._get_quotation_by_token(token)
        # for av in attribute_values:
        #     if not order_line or order_line.display_type:
        #         continue
        #     for attribute_id, value_id in av.get('values', {}).items():
        #         selected_values[int(attribute_id)] = int(value_id)
        selected_values = {}
        order_line = order.order_line.filtered(lambda l: l.id == line_id)
        selected_values[int(attribute_id)] = int(attribute_values)
        order_line.update_sale_order_line_finishes(selected_values)

    @http.route("/quote/review/<string:token>/line/<int:line_id>/feedback", type="json",
                auth="public", methods=["POST"])
    def quotation_review_line_feedback(self, token, line_id, feedback=None, attribute_values=False, **kw):
        line = self._get_line_by_token(token, line_id)
        order = self._get_quotation_by_token(token)
        if feedback == "approve":
            for av in attribute_values:
                line_id = int(av.get('line_id'))
                order_line = order.order_line.filtered(lambda l: l.id == line_id)
                if not order_line or order_line.display_type:
                    continue
                selected_values = {}
                for attribute_id, value_id in av.get('values', {}).items():
                    selected_values[int(attribute_id)] = int(value_id)
                order_line.update_sale_order_line_finishes(selected_values)
            line.set_revision_approved()
        elif feedback == "rev_required":
            for av in attribute_values:
                line_id = int(av.get('line_id'))
                order_line = order.order_line.filtered(lambda l: l.id == line_id)
                if not order_line or order_line.display_type:
                    continue
                selected_values = {}
                for attribute_id, value_id in av.get('values', {}).items():
                    selected_values[int(attribute_id)] = int(value_id)
                order_line.update_sale_order_line_finishes(selected_values)
            line.set_revision_required()
        else:
            raise NotFound()
        return {"ok": True}

    # Component calls this from submitReview() to write selected finishes on order lines
    @http.route("/quote/review/<string:token>/submit", type="json", auth="public", methods=["POST"])
    def quotation_review_submit(self, token, lines=None, **kw):
        order = self._get_quotation_by_token(token)
        if not order or order.is_frozen_due_to_project_creation:
            raise NotFound()
        if not lines:
            lines = []
        changes = []
        try:
            for line_data in lines:
                line_id = int(line_data.get('line_id'))
                order_line = order.order_line.filtered(lambda l: l.id == line_id)
                if not order_line or order_line.display_type:
                    continue
                selected_values = {}
                for attribute_id, value_id in line_data.get('values', {}).items():
                    selected_values[int(attribute_id)] = int(value_id)
                change = order_line.update_sale_order_line_finishes(selected_values)
                if change:
                    changes.append(change)
        except UserError as e:
            request.env.cr.rollback()
            return {"status": "error", "message": str(e)}
        if changes:
            order.post_review_finish_changes(changes)
        return {"status": "success"}

    # Product image need to work on
    @http.route("/quote/review/<string:token>/image/<int:line_id>", type="http",
                auth="public", methods=["GET"], sitemap=False)
    def quotation_review_image(self, token, line_id, **kw):
        order = self._get_quotation_by_token(token)
        line = order.order_line.filtered(lambda l: l.id == line_id)
        if not line or not line.product_id:
            return request.not_found()
        return request.env["ir.binary"]._get_image_stream_from(
            line, "image_128").get_response()
