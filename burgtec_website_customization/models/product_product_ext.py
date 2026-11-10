from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError
import logging
from odoo import models, tools
import base64
import logging
from odoo.tools import image_process

_logger = logging.getLogger(__name__)



class ProductProductExt(models.Model):
    _inherit = 'product.product'

    api_variant_list_price = fields.Float(string="Variant Sales Price")

    api_variant_three_d_attachment_ids = fields.Many2many(
        'ir.attachment',
        'product_api_variant_3d_rel',
        'product_id',
        'attachment_id',
        string="Variant 3D Configurator Attachments"
    )

    is_product_published = fields.Boolean(default=False, compute="_compute_is_product_published", store=True,
                                          readonly=False)
    is_modular_variant_product = fields.Boolean(default=False, string='Is Modular Variant Product')
    is_purchasable_online_variant = fields.Boolean(default=False, string='Is Purchasable Online Variant')
    api_variant_delivery_code_selection_id = fields.Many2one('product.delivery.cost.group.code',string='API Variant Delivery Code Selections')


    api_variant_featured_attachment_ids = fields.Many2many(
        'ir.attachment',
        'product_api_variant_featured_rel',
        'product_id',
        'attachment_id',
        string="Variant Featured Image"
    )

    is_preconfigured = fields.Boolean(default=False)

    preconfigured_attribute_line_ids = fields.One2many('preconfigured.attribute.line', 'product_id',
                                                       compute="_compute_preconfigured_attribute_lines", store=True,
                                                       readonly=False)

    preconfigured_attribute_option_ids = fields.Many2many('preconfigured.attribute.option')

    api_variant_unit = fields.Selection([
        ('1','1'),
        ('2','2')
        ], default="1"
    )

    optional_group_ids = fields.One2many('optional.groups.line','product_product_id')

    api_variant_height = fields.Char()
    api_variant_width = fields.Char()
    api_variant_depth = fields.Char()

    api_variant_worktop_height = fields.Char()
    api_variant_worktop_width = fields.Char()

    api_variant_seat_height = fields.Char()
    api_variant_seat_depth = fields.Char()
    api_variant_seat_width = fields.Char()

    api_variant_website_name = fields.Char(compute="_compute_api_variant_website_name", store=True, readonly=False)

    @api.depends('name')
    def _compute_api_variant_website_name(self):
        for record in self:
            if not record.name:
                record.api_variant_website_name = False
            if record.name:
                record.api_variant_website_name = record.name

    # def action_update_product_product_image_1920(self):
    #     for rec in self:
    #         attachment = rec.api_variant_featured_attachment_ids[:1]
    #         if attachment:
    #             rec.image_1920 = attachment.datas
    def action_update_product_product_image_1920(self):
        for rec in self:
            attachment = rec.api_variant_featured_attachment_ids[:1]
            if attachment:
                try:
                    # Decode the base64 data first
                    # raw_data = base64.b64decode(attachment.datas)
                    #
                    # # Process with Odoo's image_process with chunk handling
                    # processed = image_process(
                    #     raw_data,
                    #     size=(1920, 1920),
                    #     crop='center',
                    #     quality=85,
                    #     verify_resolution=False
                    # )
                    #
                    # # Assign the processed image
                    # rec.image_1920 = base64.b64encode(processed)
                    rec.image_1920 = attachment.datas

                    _logger.info(f"Successfully updated image for product {rec.id}")

                except Exception as e:
                    _logger.error(
                        f"Failed to update image for product {rec.id}: {str(e)}"
                    )
                    continue

    @api.depends('product_tmpl_id.is_product_published')
    def _compute_is_product_published(self):
        for record in self:
            if record.product_tmpl_id:
                record.is_product_published = record.product_tmpl_id.is_product_published
            else:
                record.is_product_published = False

    @api.depends('is_preconfigured', 'product_template_attribute_value_ids.sub_attribute_line_ids',
                 'product_template_attribute_value_ids.material_allocation_id', 'product_tmpl_id.attribute_line_ids')
    def _compute_preconfigured_attribute_lines(self):
        for record in self:
            list_of_vals = []
            values = {}
            list_of_update_vals = []
            update_values = {}
            id_to_update = []
            prconfigured_line_record = False
            if record.is_preconfigured:
                if not record.preconfigured_attribute_line_ids:
                    if record.product_template_attribute_value_ids:
                        # print(record.product_template_attribute_value_ids.mapped('name'))
                        for variant_value in record.product_template_attribute_value_ids:
                            if variant_value.sub_attribute_line_ids:
                                for sub_attribute in variant_value.sub_attribute_line_ids:
                                    values['sub_attribute_line_id'] = sub_attribute._origin.id
                                    values['product_template_attribute_value_id'] = variant_value._origin.id
                                    values['material_allocation_id'] = variant_value.material_allocation_id.id
                                    values['sub_attribute_id'] = sub_attribute.sub_attribute_id.id
                                    list_of_vals.append(values)
                                    values = {}
                        # print(list_of_vals)
                        # record.preconfigured_attribute_line_ids = [Command.clear()]
                        record.preconfigured_attribute_line_ids = [Command.create(val) for val in list_of_vals]

                elif record.preconfigured_attribute_line_ids:
                    # record.preconfigured_attribute_line_ids = [Command.clear()]
                    list_of_sub_attribute_line_id = record.preconfigured_attribute_line_ids.mapped(
                        'sub_attribute_line_id.id')
                    # print(list_of_sub_attribute_line_id)
                    if record.product_template_attribute_value_ids:
                        # print(record.product_template_attribute_value_ids.mapped('name'))
                        for variant_value in record.product_template_attribute_value_ids:
                            if variant_value.sub_attribute_line_ids:
                                for sub_attribute in variant_value.sub_attribute_line_ids:
                                    if sub_attribute._origin.id not in list_of_sub_attribute_line_id:
                                        values['sub_attribute_line_id'] = sub_attribute._origin.id
                                        values['product_template_attribute_value_id'] = variant_value._origin.id
                                        values['material_allocation_id'] = variant_value.material_allocation_id.id
                                        values['sub_attribute_id'] = sub_attribute.sub_attribute_id.id
                                        list_of_vals.append(values)
                                        values = {}
                                    else:
                                        update_values['sub_attribute_line_id'] = sub_attribute._origin.id
                                        update_values['product_template_attribute_value_id'] = variant_value._origin.id
                                        update_values['material_allocation_id'] = variant_value.material_allocation_id.id
                                        update_values['sub_attribute_id'] = sub_attribute.sub_attribute_id.id
                                        list_of_update_vals.append(update_values)
                                        prconfigured_line_record = record.env[
                                            'preconfigured.attribute.line'].sudo().search(
                                            [('sub_attribute_line_id', '=', sub_attribute._origin.id)], limit=1)
                                        id_to_update.append(prconfigured_line_record.id)
                                        update_values = {}

                        # print('------>',list_of_vals)
                        if list_of_vals:
                            # print("VREATEEEEE")
                            # record.preconfigured_attribute_line_ids = [Command.clear()]
                            record.preconfigured_attribute_line_ids = [Command.create(val) for val in list_of_vals]
                        # print('-----> Update  ',list_of_update_vals)
                        if list_of_update_vals:
                            record.preconfigured_attribute_line_ids = [
                                Command.update(rec_id, values)
                                for rec_id, values in zip(id_to_update, list_of_update_vals)
                            ]

    def create_preconfigured_options(self):
        for record in self:
            list_option_values = []
            option_values = {}
            options_length = 0
            if not record.preconfigured_attribute_line_ids:
                raise UserError(_("No Preconfigured Attribute Lines Found!"))
            if record.preconfigured_attribute_line_ids:
                for line in record.preconfigured_attribute_line_ids:
                    option_values['product_template_attribute_value_id'] = line.product_template_attribute_value_id.id
                    option_values['material_allocation_id'] = line.material_allocation_id.id
                    option_values['sub_attribute_id'] = line.sub_attribute_id.id
                    option_values['sub_attribute_value_ids'] = line.sub_attribute_value_ids.ids
                    list_option_values.append((0, 0, option_values))
                    option_values = {}
                if not record.preconfigured_attribute_option_ids:
                    options_length = 1
                if record.preconfigured_attribute_option_ids:
                    options_length = len(record.preconfigured_attribute_option_ids)
                    options_length += 1

                # vals = {
                #     "name":f"Option {options_length}",
                #     "preconfigured_option_line_ids": [(0, 0, vals) for vals in option_values]
                # }
                # res = record.env['preconfigured.attribute.option'].sudo().create(vals)

                res = record.env['preconfigured.attribute.option'].sudo().create({
                    'name': f"Option {options_length}",
                    # 'preconfigured_option_line_ids': [Command.create(vals) for vals in option_values],
                }
                )

                # print("Option",list_option_values)

                # # Now create lines for this
                if res:
                    res.update({'preconfigured_option_line_ids': list_option_values})

                record.preconfigured_attribute_option_ids = [Command.link(res.id)]

    def open_preconfigured_options(self):
        return {
            'name': _('Preconfigured Options'),
            'type': 'ir.actions.act_window',
            'res_model': 'preconfigured.attribute.option',
            'domain': [('id', 'in', self.preconfigured_attribute_option_ids.ids)],
            'view_mode': 'list,form',
            'target': 'fullscreen',
        }
    
    def get_optional_groups(self):
        optional_groups = self.optional_group_ids
        if optional_groups:
            return [{
        'id': line.id,
        'optional_group_id': {
            'id': line.optional_group_id.id,
            'name': line.optional_group_id.name,
            'products': line.optional_group_id.product_ids.mapped('display_name')
        },
        # Add other fields as needed
    } for line in optional_groups]
        else:
            return False
    
    def get_optional_group_product_mapping(self):
        optional_groups = self.optional_group_ids
        map_dict = {}
        list_of_product_id = []
        list_of_product_name = []
        if optional_groups:
            for line in optional_groups:
                product_name = line.optional_group_id.product_ids.mapped('display_name')
                product_id = line.optional_group_id.product_ids.mapped('id')
                list_of_product_id.extend(product_id)
                list_of_product_name.extend(product_name)

            map_dict = dict(zip(list_of_product_name,list_of_product_id))
            return map_dict
        else:
            return False
