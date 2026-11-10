import secrets
from markupsafe import Markup, escape
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    quotation_review_token = fields.Char(copy=False, index=True, readonly=True)
    quotation_review_url = fields.Char(string="Quotation Review Url", compute="_compute_quotation_review_url")

    _sql_constraints = [
        ('quotation_review_token_uniq', 'unique(quotation_review_token)',
         'Quotation review token must be unique.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('quote_type') == 'delivery_stage':
                vals['quotation_review_token'] = secrets.token_urlsafe(32)
        return super().create(vals_list)

    def _compute_quotation_review_url(self):
        for order in self:
            order.quotation_review_url = (
                f"{order.get_base_url()}/quote/review/{order.quotation_review_token}"
                if order.quotation_review_token else False
            )

    def post_review_finish_changes(self, changes):
        # changes = list of dicts returned by update_sale_order_line_finishes()
        count = len(changes)
        product_list = ''
        for change in changes:
            product_list += f"""
                           <li style="margin-bottom: 5px;">
                               <b>Line {escape(change['product_identifier'] or '')} - {escape(change['product'])}:</b>
                               {escape(change['old_finishes'])} &#8594; <b>{escape(change['new_finishes'])}</b>
                           </li>"""

        message_body = Markup(f"""
            <div style="background-color: #fff3e0; border: 2px solid #ef6c00; border-radius: 5px; padding: 15px; margin: 10px 0;">
                <h4 style="color: #ef6c00; margin: 0 0 10px 0;">
                    <span style="font-size: 18px;">🎨</span> Finishes Changed From Review Link
                </h4>
                <p style="margin: 5px 0; color: #333; font-weight: bold;">
                    {count} Sale Order Line(s) have been changed by the user with the quotation review link.
                </p>
                <details style="margin-top: 10px;">
                    <summary style="cursor: pointer; color: #ef6c00; font-weight: bold;">
                        View Changed Products
                    </summary>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        {product_list}
                    </ul>
                </details>
                <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
                    Changed by: User with review link on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        """)

        self.message_post(
            body=message_body,
            subject='Finishes Changed From Review Link',
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )


class SaleOrderLineExt(models.Model):
    _inherit = 'sale.order.line'

    public_comment = fields.Char('Public Comment')

    user_feedback =fields.Selection([('approve',"Approve"),('rev_required','Revision Required')],string="User Feedback")

    customer_finish_preference = fields.Char(string="Customer Finish Preference")

    user_selected_ptav_ids = fields.Many2many('product.attribute.value')


    def update_sale_order_line_comment(self,comment):
        self.public_comment = comment

    def set_revision_approved(self):
        self.user_feedback = 'approve'

    def set_revision_required(self):
        self.user_feedback = 'rev_required'

    def update_sale_order_line_finishes(self, selected_values):
        # selected_values = {attribute_line_id: attribute_value_id} from review page
        self.ensure_one()
        selected = self.env['product.attribute.value'].browse(list(selected_values.values())).exists()
        if selected:
            self.user_selected_ptav_ids = selected
        new_text = "%s (%s)" % (self.product_id.product_tmpl_id.name, ", ".join(selected.mapped('name')))
        old_text = self.customer_finish_preference or self.product_id.display_name
        self.customer_finish_preference = new_text  # always write

        current = (self.product_template_attribute_value_ids
                   | self.product_no_variant_attribute_value_ids).product_attribute_value_id
        if set(selected.ids) == set(current.ids):
            return False  # written, but no chatter for unchanged
        return {
            'product_identifier': self.product_identifier,
            'product': self.product_id.display_name,
            'old_finishes': old_text,
            'new_finishes': new_text,
        }

    # def update_sale_order_line_finishes(self, selected_values):
    #     # selected_values = {attribute_line_id: attribute_value_id} selected on review page
    #     selected_value_ids = list(selected_values.values())
    #     product_tmpl_id = self.product_id.product_tmpl_id
    #
    #     # find the variant of the template that has the selected finishes
    #     new_product = False
    #     for variant in product_tmpl_id.product_variant_ids:
    #         # finishes of this variant e.g. [103, 107]
    #         variant_value_ids = variant.product_template_attribute_value_ids.product_attribute_value_id.ids
    #
    #         # check every finish of this variant is selected by user
    #         is_same_finishes = True
    #         for value_id in variant_value_ids:
    #             if value_id not in selected_value_ids:
    #                 is_same_finishes = False
    #                 break
    #
    #         if is_same_finishes:
    #             new_product = variant
    #             break
    #
    #     if not new_product:
    #         raise ValidationError(_("No product variant found for the selected finishes of %s.") % self.product_id.display_name)
    #
    #     if new_product == self.product_id:
    #         return False
    #
    #     old_product_name = self.product_id.display_name
    #     product_identifier = self.product_identifier
    #     order_id = self.order_id
    #     line_vals = self.copy_data()[0]
    #     line_vals['order_id'] = order_id.id
    #     line_vals['product_id'] = new_product.id
    #     line_vals.pop('name', None)
    #     self.unlink()
    #     new_line = self.env['sale.order.line'].create(line_vals)
    #     component = order_id.bom_component_id
    #     if component:
    #         component.update_component_lines(lines_vals=[{
    #             'order_id': order_id.id,
    #             'product_id': new_line.product_id.id,
    #             'product_uom_qty': new_line.product_uom_qty,
    #             'sequence': new_line.sequence,
    #         }])
    #     return {
    #         'product_identifier': product_identifier,
    #         'old_product': old_product_name,
    #         'new_product': new_line.product_id.display_name,
    #     }