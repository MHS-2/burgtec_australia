import logging
from odoo import models, fields, _
from markupsafe import Markup
from odoo.exceptions import ValidationError, UserError
import math


_logger = logging.getLogger(__name__)


class BulkActionOperationsExt(models.TransientModel):
    _inherit = 'bulk.action.operations'

    operation_type = fields.Selection(
        selection_add=[('modify_zone_for_delivery_component', 'Modify Zone For Delivery Component'),
                       ('modify_zone_for_install_component', 'Modify Zone For Install Component'),
                       ('add_delivery_component', 'Add Delivery Component'),
                       ('add_install_component', 'Add Install Component'),
                       ('reset_sale_price_to_pricelist_price', 'Reset Sale Price To Pricelist Price')])


    zone_type = fields.Selection([('zone_1', 'Zone 1'), ('zone_2', 'Zone 2'), ('zone_3', 'Zone 3')], string="Zone Type",
                                 default=None)

    def action_modify_zone_for_delivery_component(self):
        operation_type = self.operation_type
        zone_type = self.zone_type
        sale_order = self.sale_order_id
        sale_order_bom_component_id = sale_order.bom_component_id

        if operation_type == 'modify_zone_for_delivery_component':
            selected_lines = self.bulk_lines.filtered(lambda l: l.is_check)
            if not selected_lines:
                raise UserError('You Have not Selected Any Lines')
            selected_fully_approved_lines = selected_lines.order_line_id.filtered(
                lambda l: l.is_product_fully_approved)
            if selected_fully_approved_lines:
                product_names = '\n'.join(
                    f'• {short_name}' for short_name in selected_fully_approved_lines.mapped('name_short'))
                raise UserError(
                    f'You Can’t Modify Zone for Delivery Component of Following Products because they are Fully Approved.\n{product_names}')

            if sale_order_bom_component_id:
                zone_field_map = {
                    'zone_1': 'delivery_code_cost',
                    'zone_2': 'zone2_delivery_cost',
                    'zone_3': 'zone3_delivery_cost',
                }
                zone_label_map = {
                    'zone_1': 'Zone 1',
                    'zone_2': 'Zone 2',
                    'zone_3': 'Zone 3',
                }
                cost_field = zone_field_map.get(zone_type)
                zone_label = zone_label_map.get(zone_type, zone_type)
                parent_products = []

                for line in selected_lines:
                    parent_line = sale_order_bom_component_id.component_line_ids.filtered(
                        lambda l: l.order_line_id == line.order_line_id and l.is_parent
                    )
                    child_freight_component = sale_order_bom_component_id.component_line_ids.filtered(
                        lambda l: l.order_line_id == line.order_line_id
                                  and l.parent_product_id == parent_line.product_id.product_tmpl_id
                                  and l.product_id.default_code == 'freight-out'
                    )
                    if not child_freight_component:
                        raise ValidationError(f'Delivery Component not found for Product {parent_line.product_id.name}')
                    delivery_code = parent_line.product_id.variant_delivery_code_selection_id
                    if not delivery_code:
                        raise ValidationError(f'Delivery Code not found for Product {parent_line.product_id.name}')
                    if child_freight_component and delivery_code and cost_field:
                        cost = getattr(delivery_code, cost_field, 0.0)
                        child_freight_component.write({
                            'live_unit_cost': child_freight_component.product_qty * cost,
                            'manual_live_unit_cost': cost,
                        })
                        parent_products.append((parent_line.product_id.display_name or '-', zone_label, cost))

                sale_order_bom_component_id.update_component_lines()

                product_list_html = ''.join(
                    f"<li style='margin: 4px 0; color: #555;'><b>{name}</b></li>"
                    for name, zone, cost in parent_products
                )

                message_body = Markup(f"""
                    <div style="background-color: #F0E599; border: 2px solid #e65100; border-radius: 5px; padding: 15px; margin: 10px 0;">
                        <h4 style="color: #e65100; margin: 0 0 10px 0;">
                            <span style="font-size: 18px;">✎𓂃</span> Bulk Zone Modification of Delivery Component Action
                        </h4>
                        <p style="margin: 5px 0; color: #333; font-weight: bold;">
                            <b style="color: #e65100;">{zone_label}</b> Cost Has Been Applied.
                        </p>
                        <details style="margin-top: 10px;">
                            <summary style="cursor: pointer; color: #e65100; font-weight: bold;">
                                View Parent Products ({len(parent_products)})
                            </summary>
                            <ul style="margin: 10px 0; padding-left: 20px;">
                                {product_list_html}
                            </ul>
                        </details>
                        <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
                            Modified by: {self.env.user.name} on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        </p>
                    </div>
                """)
                sale_order.message_post(
                    body=message_body,
                    subject='Modify Zone of Delivery Component Action',
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )

    def action_modify_zone_for_install_component(self):
        operation_type = self.operation_type
        zone_type = self.zone_type
        sale_order = self.sale_order_id
        sale_order_bom_component_id = sale_order.bom_component_id
        if operation_type == 'modify_zone_for_install_component':
            selected_lines = self.bulk_lines.filtered(lambda l: l.is_check)

            if not selected_lines:
                raise UserError('You Have not Selected Any Lines')
            selected_fully_approved_lines = selected_lines.order_line_id.filtered(
                lambda l: l.is_product_fully_approved)
            if selected_fully_approved_lines:
                product_names = '\n'.join(
                    f'• {short_name}' for short_name in selected_fully_approved_lines.mapped('name_short'))
                raise UserError(
                    f'You Can’t Modify Zone for Install Component of Following Products because they are Fully Approved.\n{product_names}')


            if sale_order_bom_component_id:
                zone_field_map = {
                    'zone_1': 'installation_cost',
                    'zone_2': 'zone2_installation_cost',
                    'zone_3': 'zone3_installation_cost',
                }
                zone_label_map = {
                    'zone_1': 'Zone 1',
                    'zone_2': 'Zone 2',
                    'zone_3': 'Zone 3',
                }
                cost_field = zone_field_map.get(zone_type)
                zone_label = zone_label_map.get(zone_type, zone_type)
                parent_products = []

                for line in selected_lines:
                    parent_line = sale_order_bom_component_id.component_line_ids.filtered(
                        lambda l: l.order_line_id == line.order_line_id and l.is_parent
                    )
                    child_install_component = sale_order_bom_component_id.component_line_ids.filtered(
                        lambda l: l.order_line_id == line.order_line_id
                                  and l.parent_product_id == parent_line.product_id.product_tmpl_id
                                  and l.product_id.default_code == 'assy-inst'
                    )
                    if not child_install_component:
                        raise ValidationError(f'Install Component not found for Product {parent_line.product_id.name}')
                    delivery_code = parent_line.product_id.variant_delivery_code_selection_id
                    if not delivery_code:
                        raise ValidationError(f'Delivery Code not found for Product {parent_line.product_id.name}')
                    if child_install_component and delivery_code and cost_field:
                        cost = getattr(delivery_code, cost_field, 0.0)
                        child_install_component.write({
                            'live_unit_cost': child_install_component.product_qty * cost,
                            'manual_live_unit_cost': cost,
                        })
                        parent_products.append((parent_line.product_id.display_name or '-', zone_label, cost))

                sale_order_bom_component_id.update_component_lines()

                product_list_html = ''.join(
                    f"<li style='margin: 4px 0; color: #555;'><b>{name}</b></li>"
                    for name, zone, cost in parent_products
                )

                message_body = Markup(f"""
                                    <div style="background-color: #F0E599; border: 2px solid #e65100; border-radius: 5px; padding: 15px; margin: 10px 0;">
                                        <h4 style="color: #e65100; margin: 0 0 10px 0;">
                                            <span style="font-size: 18px;">✎𓂃</span> Bulk Zone Modification of Install Component Action
                                        </h4>
                                        <p style="margin: 5px 0; color: #333; font-weight: bold;">
                                            <b style="color: #e65100;">{zone_label}</b> Cost Has Been Applied.
                                        </p>
                                        <details style="margin-top: 10px;">
                                            <summary style="cursor: pointer; color: #e65100; font-weight: bold;">
                                                View Parent Products ({len(parent_products)})
                                            </summary>
                                            <ul style="margin: 10px 0; padding-left: 20px;">
                                                {product_list_html}
                                            </ul>
                                        </details>
                                        <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
                                            Modified by: {self.env.user.name} on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                                        </p>
                                    </div>
                                """)
                sale_order.message_post(
                    body=message_body,
                    subject='Modify Zone of Install Component Action',
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )

    def action_add_delivery_component(self):
        operation_type = self.operation_type
        sale_order = self.sale_order_id
        multiply_qty = 1
        if operation_type == 'add_delivery_component' and sale_order.bom_component_id:
            selected_lines = self.bulk_lines.filtered(lambda l: l.is_check)

            if not selected_lines:
                raise UserError('You Have not Selected Any Lines')
            selected_fully_approved_lines = selected_lines.order_line_id.filtered(
                lambda l: l.is_product_fully_approved)
            if selected_fully_approved_lines:
                product_names = '\n'.join(
                    f'• {short_name}' for short_name in selected_fully_approved_lines.mapped('name_short'))
                raise UserError(
                    f'You Can’t Add Delivery Component to Following Products because they are Fully Approved.\n{product_names}')

            new_lines = []
            parent_products = []
            for line in selected_lines:
                parent_line = sale_order.bom_component_id.component_line_ids.filtered(
                    lambda l: l.order_line_id == line.order_line_id and l.is_parent
                )
                existing_freight = sale_order.bom_component_id.component_line_ids.filtered(
                    lambda
                        l: l.order_line_id == line.order_line_id and not l.is_parent and l.product_id.default_code == 'freight-out'
                )
                if existing_freight:
                    raise ValidationError(f'This Product {line.order_line_id.name_short} Already have a Delivery Component')
                freight_product = self.env['product.product'].search([('default_code', '=', 'freight-out')],
                                                                     limit=1)


                if freight_product and parent_line and not existing_freight:
                    multiply_qty = 1 * parent_line.product_qty
                    new_lines.append((0, 0, {
                        'component_id': sale_order.bom_component_id.id,
                        'order_line_id': line.order_line_id.id,
                        'parent_product_id': parent_line.product_id.product_tmpl_id.id,
                        'product_id': freight_product.id,
                        'is_parent': False,
                        'is_freight_or_assembly': True,
                        'product_qty': multiply_qty,
                        'supplier_id': self._get_product_suppiler(freight_product),
                        'live_unit_cost': multiply_qty * self._get_live_unit_for_delivery_or_installation(line.product_id,
                                                                                           freight_product),
                        'manual_live_unit_cost': self._get_live_unit_for_delivery_or_installation(line.product_id,
                                                                                                  freight_product),
                    }))
                    parent_products.append((parent_line.product_id.display_name))
            product_list_html = ''.join(
                f"<li style='margin: 4px 0; color: #555;'><b>{name}</b></li>"
                for name in parent_products
            )
            if new_lines:
                sale_order.bom_component_id.write({
                    'component_line_ids': new_lines,
                })
                sale_order.bom_component_id.update_component_lines()
            message_body = Markup(f"""
                                  <div style="background-color: #FFE9D9; border: 2px solid #e65100; border-radius: 5px; padding: 15px; margin: 10px 0;">
                                      <h4 style="color: #e65100; margin: 0 0 10px 0;">
                                          <span style="font-size: 18px;">✚</span> Bulk Add Delivery Component Action
                                      </h4>
                                      <p style="margin: 5px 0; color: #333; font-weight: bold;">
                                          Delivery Component has been added for Product(s).
                                      </p>
                                      <details style="margin-top: 10px;">
                                          <summary style="cursor: pointer; color: #e65100; font-weight: bold;">
                                              View Parent Products ({len(parent_products)})
                                          </summary>
                                          <ul style="margin: 10px 0; padding-left: 20px;">
                                          {product_list_html}
                                          </ul>
                                      </details>
                                      <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
                                          Modified by: {self.env.user.name} on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                                      </p>
                                  </div>
                              """)
            sale_order.message_post(
                body=message_body,
                subject='Add Delivery Component Action',
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )


    def _get_live_unit_for_delivery_or_installation(self, parent_product, product):
        if not parent_product.variant_delivery_code_selection_id:
            return 0.0
        if parent_product.variant_delivery_code_selection_id:
            if product.default_code == 'freight-out':
                return parent_product.variant_delivery_code_selection_id.delivery_code_cost
            if product.default_code == 'assy-inst':
                return parent_product.variant_delivery_code_selection_id.installation_cost

    def action_add_install_component(self):
        operation_type = self.operation_type
        sale_order = self.sale_order_id
        multiply_qty = 1
        if operation_type == 'add_install_component' and sale_order.bom_component_id:
            selected_lines = self.bulk_lines.filtered(lambda l: l.is_check)

            if not selected_lines:
                raise UserError('You Have not Selected Any Lines')
            selected_fully_approved_lines = selected_lines.order_line_id.filtered(
                lambda l: l.is_product_fully_approved)
            if selected_fully_approved_lines:
                product_names = '\n'.join(
                    f'• {short_name}' for short_name in selected_fully_approved_lines.mapped('name_short'))
                raise UserError(
                    f'You Can’t Add Install Component to Following Products because they are Fully Approved.\n{product_names}')


            new_lines = []
            parent_products = []
            for line in selected_lines:
                parent_line = sale_order.bom_component_id.component_line_ids.filtered(
                    lambda l: l.order_line_id == line.order_line_id and l.is_parent
                )
                existing_install = sale_order.bom_component_id.component_line_ids.filtered(
                    lambda
                        l: l.order_line_id == line.order_line_id and not l.is_parent and l.product_id.default_code == 'assy-inst'
                )
                if existing_install:
                    raise ValidationError(f'This Product {line.order_line_id.name_short} Already have a Install Component')
                install_product = self.env['product.product'].search([('default_code', '=', 'assy-inst')],
                                                                     limit=1)

                if install_product and parent_line and not existing_install:
                    multiply_qty = 1 * parent_line.product_qty
                    new_lines.append((0, 0, {
                        'component_id': sale_order.bom_component_id.id,
                        'order_line_id': line.order_line_id.id,
                        'parent_product_id': parent_line.product_id.product_tmpl_id.id,
                        'product_id': install_product.id,
                        'is_parent': False,
                        'is_freight_or_assembly': True,
                        'product_qty': multiply_qty,
                        'supplier_id': self._get_product_suppiler(install_product),
                        'live_unit_cost': multiply_qty * self._get_live_unit_for_delivery_or_installation(line.product_id,
                                                                                           install_product),
                        'manual_live_unit_cost': self._get_live_unit_for_delivery_or_installation(line.product_id,
                                                                                                  install_product),
                    }))
                    parent_products.append((parent_line.product_id.display_name))
            product_list_html = ''.join(
                f"<li style='margin: 4px 0; color: #555;'><b>{name}</b></li>"
                for name in parent_products
            )

            if new_lines:
                sale_order.bom_component_id.write({
                    'component_line_ids': new_lines,
                })
                sale_order.bom_component_id.update_component_lines()
            message_body = Markup(f"""
                                    <div style="background-color: #FFE9D9; border: 2px solid #e65100; border-radius: 5px; padding: 15px; margin: 10px 0;">
                                        <h4 style="color: #e65100; margin: 0 0 10px 0;">
                                            <span style="font-size: 18px;">+</span> Bulk Add Install Component Action
                                        </h4>
                                        <p style="margin: 5px 0; color: #333; font-weight: bold;">
                                            Install Component has been added for Product(s).
                                        </p>
                                        <details style="margin-top: 10px;">
                                            <summary style="cursor: pointer; color: #e65100; font-weight: bold;">
                                                View Parent Products ({len(parent_products)})
                                            </summary>
                                            <ul style="margin: 10px 0; padding-left: 20px;">
                                            {product_list_html}
                                            </ul>
                                        </details>
                                        <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
                                            Modified by: {self.env.user.name} on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                                        </p>
                                    </div>
                                """)
            sale_order.message_post(
                body=message_body,
                subject='Add Install Component Action',
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )

    def _get_product_suppiler(self, product_id):
        if product_id.seller_ids:
            return product_id.seller_ids[0].partner_id.id
        return False


    def action_add_bulk_margin(self):
        sale_order  = self.sale_order_id
        applied_margin = self.margin_percentage
        if applied_margin < 0:
            raise ValidationError('Applied Margin Cant be Negative')
        applied_margin_in_decimal = applied_margin / 100
        new_applied_margin = 1 - applied_margin_in_decimal
        selected_lines_to_add_margin = self.bulk_lines.filtered(lambda l: l.is_check)
        if not selected_lines_to_add_margin:
            raise UserError('You Have not Selected Any Lines')
        selected_fully_approved_lines = selected_lines_to_add_margin.order_line_id.filtered(lambda l:l.is_product_fully_approved)
        if selected_fully_approved_lines:
            product_names = '\n'.join(f'• {short_name}' for short_name in selected_fully_approved_lines.mapped('name_short'))
            raise UserError(f'You Can’t Add Margin to Following Products because they are Fully Approved.\n{product_names}')
        for line in selected_lines_to_add_margin:
            matching_bom_line = sale_order.bom_component_id.component_line_ids.filtered(lambda l:l.is_parent and line.order_line_id == l.order_line_id)
            if matching_bom_line:
                matching_bom_line_manual_live_unt_cost = matching_bom_line.manual_live_unit_cost
                resultant_margin = matching_bom_line_manual_live_unt_cost / new_applied_margin if new_applied_margin else 0.0
                sale_price_rounded_off = math.floor((resultant_margin + 5) / 10) * 10
                line.order_line_id.sudo().write({
                    'price_unit' : sale_price_rounded_off,
                    'applied_margin' : applied_margin / 100,
                })
        if sale_order.bom_component_id:
            sale_order.bom_component_id.update_component_lines()
        message_body = Markup(f"""
                       <div style="background-color: #27D3F5; border: 2px solid #009EC4; border-radius: 5px; padding: 15px; margin: 10px 0;">
                           <h4 style="color: #c62828; margin: 0 0 10px 0;">
                               <span style="font-size: 18px;">📈</span> Margin Applied Action
                           </h4>
                           <p style="margin: 5px 0; color: #333; font-weight: bold;">
                               A Margin of {int(applied_margin)}% has been Successfully Applied on the Sale Order Lines
                           </p>
                           <p style="margin: 10px 0 0 0; font-size: 12px; color: #333;">
                               Margin Applied by: {self.env.user.name} on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                           </p>
                       </div>
                   """)
        sale_order.message_post(
            body=message_body,
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )
        return {'type': 'ir.actions.act_window_close'}

    def action_bulk_delete(self):
        """Delete selected lines from sale order"""
        selected_lines = self.bulk_lines.filtered(lambda l: l.is_check)
        if not selected_lines:
            raise UserError(_('No lines selected for deletion.'))

        # Get the original sale order lines
        order_lines_to_delete = selected_lines.mapped('order_line_id')
        fully_approved_order_lines_to_delete = order_lines_to_delete.filtered(lambda l: l.is_product_fully_approved)
        if fully_approved_order_lines_to_delete:
            product_short_names = '\n'.join(f'• {short_name}' for short_name in fully_approved_order_lines_to_delete.mapped('name_short'))
            raise UserError(f'You Can’t Delete the Following Products because they are Fully Approved.\n{product_short_names}')
        count = len(order_lines_to_delete)

        # Prepare product list
        product_list = ''
        for line in order_lines_to_delete:
            product_name = line.product_id.display_name or line.name or 'N/A'
            qty = line.product_uom_qty
            product_list += f'<li>{product_name} (Qty: {qty})</li>'

        # Delete from sale order
        order_lines_to_delete.unlink()

        # Post message on sale order
        message_body = Markup(f"""
            <div style="background-color: #af709e; border: 2px solid #c62828; border-radius: 5px; padding: 15px; margin: 10px 0;">
                <h4 style="color: #c62828; margin: 0 0 10px 0;">
                    <span style="font-size: 18px;">🗑️</span> Bulk Delete Action
                </h4>
                <p style="margin: 5px 0; color: #333; font-weight: bold;">
                    {count} Sale Order Line(s) have been deleted.
                </p>
                <details style="margin-top: 10px;">
                    <summary style="cursor: pointer; color: #c62828; font-weight: bold;">
                        View Deleted Products
                    </summary>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        {product_list}
                    </ul>
                </details>
                <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
                    Deleted by: {self.env.user.name} on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        """)

        self.sale_order_id.message_post(
            body=message_body,
            subject='Bulk Delete Action',
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        # Close wizard and reload sale order
        return {'type': 'ir.actions.act_window_close'}


    def action_reset_sale_price_to_pricelist_price(self):
        product_list = ''
        reset_count = 0
        sale_order  = self.sale_order_id
        selected_lines_to_reset_sales_price = self.bulk_lines.filtered(lambda l: l.is_check)
        if not selected_lines_to_reset_sales_price:
            raise UserError('You Have not Selected Any Lines')
        selected_fully_approved_lines = selected_lines_to_reset_sales_price.order_line_id.filtered(lambda l:l.is_product_fully_approved)
        if selected_fully_approved_lines:
            product_names = '\n'.join(f'• {short_name}' for short_name in selected_fully_approved_lines.mapped('name_short'))
            raise UserError(f'You Can’t Reset Sales Price of Following Products to the Pricelist Price, because they are Fully Approved.\n{product_names}')
        sale_order_pricelist_id = sale_order.pricelist_id
        for line in selected_lines_to_reset_sales_price:
            line_pricelist_item_id = line.order_line_id.pricelist_item_id
            if line_pricelist_item_id:
                if line_pricelist_item_id.pricelist_id == sale_order_pricelist_id:
                    line.order_line_id.sudo().write({
                        'price_unit': line_pricelist_item_id.fixed_price,
                        'applied_margin': 0.0
                    })
                    product_name = line.product_id.display_name or line.name or 'N/A'
                    product_list += f'<li>{product_name}</li>'
                    reset_count += 1
                else:
                    raise UserError(
                        _('Product %s belongs to pricelist "%s" but the Sale Order uses pricelist "%s".')
                        % (
                            line.product_id.display_name,
                            line_pricelist_item_id.pricelist_id.display_name,
                            sale_order.pricelist_id.display_name,
                        )
                    )
        if sale_order.bom_component_id:
            sale_order.bom_component_id.update_component_lines()
        message_body = Markup(f"""
                   <div style="background-color: #98E0EB; border: 2px solid #c62828; border-radius: 5px; padding: 15px; margin: 10px 0;">
                       <h4 style="color: #a53186; margin: 0 0 10px 0; font-weight: bold;">
                           <span style="font-size: 18px;">🗘</span> Reset Sales Price To Pricelist Price Action
                       </h4>
                       <p style="margin: 5px 0; color: #333; font-weight: bold;">
                           {reset_count} Sale Order Line(s) Sale Price has been Reset.
                       </p>
                       <details style="margin-top: 10px;">
                           <summary style="cursor: pointer; color: #a53186; font-weight: bold;">
                               View Products whose Sale Price has been Reset
                           </summary>
                           <ul style="margin: 10px 0; padding-left: 20px;">
                               {product_list}
                           </ul>
                       </details>
                       <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
                           Reset by: {self.env.user.name} on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                       </p>
                   </div>
               """)

        sale_order.message_post(
            body=message_body,
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )
        return {'type': 'ir.actions.act_window_close'}



