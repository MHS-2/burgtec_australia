from odoo import api, models, _
from odoo.exceptions import UserError, ValidationError
import base64


class SaleQuoteBurgtecReport(models.AbstractModel):
    _name = 'report.sale_custom_report.burgtec_sale_quote'
    _description = 'Sale Custom Report Quote'

    def _get_report_values(self, docids, data=None):

        print("OLD EXECUTED!")
        print()
        print()
        print()
        # dictionary
        lines_dict = {}
        lines_total_cost = {}
        same_product_sale_order_lines = []
        final_order_lines = {}
        group_lines_list = []
        group_dict = {}
        product_list = []

        group_name = ""
        section_name = ""
        group_id = False
        section_id = False
        section_total = 0.0
        floor_total = 0.0
        section_total_dict = {}
        floor_total_dict = {}
        id_map = {}

        # for validation strings
        validation_group_name = ""
        validation_section_name = ""
        is_group = False
        is_group_check = False
        is_section = False
        is_product_line = False
        # get the report action back as we will need its data
        report = self.env['ir.actions.report']._get_report_from_name('sale_custom_report.burgtec_sale_quote')
        # get the records selected for this rendering of the report
        docs = self.env[report.model].browse(docids)

        # Setting up order lines according to sale order's project field.

        for doc in docs:  # Initialize nested dictionary for this document
            if doc.id not in lines_dict:
                lines_dict[doc.id] = {}

            if not doc.order_line:
                raise UserError(_("There are no Sale Order Lines."))

            if doc.order_line:

                # VALIDATION
                # First Line check for section

                if len(doc.order_line) > 1:
                    # VALIDATION FOR FIRST LINESS
                    if doc.order_line[0].display_type == 'line_note':
                        raise UserError(f"Code {doc.order_line[0].name} must be inside a group.")
                    if doc.order_line[0].display_type == 'line_section':
                        if doc.order_line[1].display_type != 'line_note':
                            raise UserError(
                                f"Group {doc.order_line[0].name} must be followed by a code and its products.")

                    # VALIDATION FOR LAST LINESSS
                    if doc.order_line[-1].display_type == 'line_section':
                        raise UserError(f"Group {doc.order_line[-1].name} must be followed by a code and its products.")
                    if doc.order_line[-1].display_type == 'line_note':
                        if doc.order_line[-2].display_type == 'line_section':
                            raise UserError(f"Code {doc.order_line[-1].name} must have products.")
                        if doc.order_line[-2].display_type != 'line_section':
                            raise UserError(f"Code {doc.order_line[-1].name} must have products.")


                elif len(doc.order_line) == 1:
                    if doc.order_line[0].display_type == 'line_note':
                        raise UserError(f"Code {doc.order_line[0].name} must be inside a group.")
                    if doc.order_line[0].display_type == 'line_section':
                        raise UserError(f"Group {doc.order_line[0].name} must be followed by a code and its products.")

                for line in doc.order_line:
                    if not validation_group_name:
                        if line.display_type == 'line_note':
                            raise UserError(f"Code {line.name} must be in a group.")
                    if is_group_check:
                        if line.display_type == 'line_note':
                            is_group_check = False  # section found
                            is_section = True
                            validation_section_name = line.name
                            continue
                        else:
                            raise UserError(f"Group {validation_group_name} must be followed by a code.")
                    if is_section:
                        if line.display_type == 'line_note':
                            raise UserError(
                                f"Code {validation_section_name} and Code {line.name} are coming consecutive, without there respective products.")
                        elif line.display_type == 'line_section':
                            raise UserError(
                                f"Group {line.name} and Code {validation_section_name} are coming consecutive, without products!")
                        else:
                            is_section = False
                            is_group_check = False  # section found
                            continue
                    if line.display_type == 'line_section':
                        if is_group_check:
                            raise UserError(
                                f"Group {line.name} is coming right after Group {validation_group_name} without there respective code and products.")
                        if is_section:
                            raise UserError(
                                f"Group {line.name} is coming right after code {validation_section_name} without any products!")
                        is_group_check = True
                        validation_group_name = line.name
                        continue
                    if line.display_type == 'line_note':
                        is_section = True
                        validation_section_name = line.name
                        continue

                # Split Groups and sections for the report.
                for line in doc.order_line:
                    if line.display_type == 'line_section':
                        floor_total = 0.0
                        is_group = True
                        group_name = line.name
                        group_id = line.id
                        product_list = []
                        lines_dict[doc.id][group_id] = {}
                        section_name = ""
                        section_id = False
                        if group_id not in id_map:
                            id_map[group_id] = group_name
                    if line.display_type == 'line_note':
                        section_total = 0.0
                        product_list = []
                        section_name = line.name
                        section_id = line.id
                        lines_dict[doc.id][group_id][section_id] = {}
                        if section_id not in id_map:
                            id_map[section_id] = section_name
                    if not line.display_type:
                        section_total = section_total + line.price_subtotal
                        floor_total = floor_total + line.price_subtotal
                        vals = {
                            'product_default_code': line.product_id.default_code,
                            'custom_product_name': line.custom_product_name,
                            'product_name': line.product_template_id.name,
                            'product_description': line.name,
                            'product_image': line.product_id.image_1920 if not line.image_128 else line.image_128,
                            'product_qty': line.product_uom_qty,
                            'product_price_subtotal': line.price_subtotal,
                            'product_code': line.line_section_name,
                            'product_price_total': line.price_total,
                            'product_price_unit': line.price_unit,
                            'section_total': section_total,
                            'product_dimensions': line.product_template_id.quotation_dimensions,
                            'product_features': line.product_template_id.quotation_features,
                            'product_finishes': line.product_template_id.quotation_finishes,
                            'product_warranty': line.product_template_id.quotation_warranty,
                            'product_lead_time': line.product_template_id.quotation_lead_time,
                            'product_other_details': line.product_template_id.quotation_other_details
                        }
                        product_list.append(
                            vals
                        )
                        vals = {}
                        if not group_id and not section_id:
                            lines_dict[doc.id]['N/A'] = {}  # initializing dict for no group
                            lines_dict[doc.id]['N/A']['N/A'] = {}  # initializing dict when no group and no section.
                            lines_dict[doc.id]['N/A']['N/A'] = product_list  # Filling up the data
                            floor_total_dict['N/A'] = floor_total
                            section_total_dict['N/A'] = section_total
                            id_map['N/A'] = 'N/A'
                        if group_id and section_id:
                            lines_dict[doc.id][group_id][section_id] = product_list
                            floor_total_dict[group_id] = floor_total
                            section_total_dict[section_id] = section_total
                group_lines_list.append(lines_dict)

            list_of_section_name = []
            floor_section_map = {}

            for dict in group_lines_list:
                # Gets all floor names
                list_of_floors = dict[doc.id].keys()
                for floor in list_of_floors:
                    for section in dict[doc.id][floor].keys():
                        list_of_section_name.append(section)
                    floor_section_map[floor] = list_of_section_name
                    list_of_section_name = []
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'company': self.env.company,
            'docs': docs,
            'group_lines_list': group_lines_list,
            'is_group': is_group,
            'floor_section_map': floor_section_map,
            'floor_total_dict': floor_total_dict,
            'section_total_dict': section_total_dict,
            'floor_section_ids_map': id_map,

        }


class SaleQuoteBurgtecReportV2(models.AbstractModel):
    _name = 'report.sale_custom_report.burgtec_sale_quote_v2'
    _description = "Sale Custom Report Quote V2"

    def _get_report_values(self, docids, data=None):
        # dictionary
        lines_data = []
        lines_dict = {}
        groups_total_dict = {}
        codes_total_dict = {}
        total_dict = {}

        # for validation strings
        validation_group_name = ""
        validation_section_name = ""
        is_group = False
        is_group_check = False
        is_section = False
        is_product_line = False
        # get the report action back as we will need its data
        report = self.env['ir.actions.report']._get_report_from_name('sale_custom_report.burgtec_sale_quote_v2')
        # get the records selected for this rendering of the report
        docs = self.env[report.model].browse(docids)

        # Setting up order lines according to sale order's project field.
        for doc in docs:  # Initialize nested dictionary for this document
            if doc.id not in lines_dict:
                lines_dict[doc.id] = {}

            if not doc.order_line:
                raise UserError(_("There are no Sale Order Lines."))

            if doc.opportunity_id.series_sequence_id.id == 9:
                raise ValidationError(_("You cannot Download, this Report is only for Series Sequence 9."))

            if doc.order_line:

                # VALIDATION
                # First Line check for section

                if len(doc.order_line) > 1:
                    # VALIDATION FOR FIRST LINESS
                    if doc.order_line[0].display_type == 'line_note':
                        raise UserError(f"Code {doc.order_line[0].name} must be inside a group.")
                    if doc.order_line[0].display_type == 'line_section':
                        if doc.order_line[1].display_type != 'line_note':
                            raise UserError(
                                f"Group {doc.order_line[0].name} must be followed by a code and its products.")

                    # VALIDATION FOR LAST LINESSS
                    if doc.order_line[-1].display_type == 'line_section':
                        raise UserError(f"Group {doc.order_line[-1].name} must be followed by a code and its products.")
                    if doc.order_line[-1].display_type == 'line_note':
                        if doc.order_line[-2].display_type == 'line_section':
                            raise UserError(f"Code {doc.order_line[-1].name} must have products.")
                        if doc.order_line[-2].display_type != 'line_section':
                            raise UserError(f"Code {doc.order_line[-1].name} must have products.")


                elif len(doc.order_line) == 1:
                    if doc.order_line[0].display_type == 'line_note':
                        raise UserError(f"Code {doc.order_line[0].name} must be inside a group.")
                    if doc.order_line[0].display_type == 'line_section':
                        raise UserError(f"Group {doc.order_line[0].name} must be followed by a code and its products.")

                for line in doc.order_line:
                    if not validation_group_name:
                        if line.display_type == 'line_note':
                            raise UserError(f"Code {line.name} must be in a group.")
                    if is_group_check:
                        if line.display_type == 'line_note':
                            is_group_check = False  # section found
                            is_section = True
                            validation_section_name = line.name
                            continue
                        else:
                            raise UserError(f"Group {validation_group_name} must be followed by a code.")
                    if is_section:
                        if line.display_type == 'line_note':
                            raise UserError(
                                f"Code {validation_section_name} and Code {line.name} are coming consecutive, without there respective products.")
                        elif line.display_type == 'line_section':
                            raise UserError(
                                f"Group {line.name} and Code {validation_section_name} are coming consecutive, without products!")
                        else:
                            is_section = False
                            is_group_check = False  # section found
                            continue
                    if line.display_type == 'line_section':
                        if is_group_check:
                            raise UserError(
                                f"Group {line.name} is coming right after Group {validation_group_name} without there respective codes and products.")
                        if is_section:
                            raise UserError(
                                f"Group {line.name} is coming right after code {validation_section_name} without any products!")
                        is_group_check = True
                        validation_group_name = line.name
                        continue
                    if line.display_type == 'line_note':
                        is_section = True
                        validation_section_name = line.name
                        continue

                # Filtering our Defected Groups, Codes, and Product Lines. 
                lines = doc.order_line.filtered(
                    lambda l: not l.display_type and l.id not in l.order_id.defected_line_ids.ids and int(
                        l.line_group_id_value) not in l.order_id.defected_line_ids.ids)
                groups = doc.order_line.filtered(
                    lambda l: l.display_type == 'line_section' and l.id not in l.order_id.defected_line_ids.ids and int(
                        l.line_group_id_value) not in l.order_id.defected_line_ids.ids)
                sections = doc.order_line.filtered(
                    lambda l: l.display_type == 'line_note' and l.id not in l.order_id.defected_line_ids.ids and int(
                        l.line_group_id_value) not in l.order_id.defected_line_ids.ids)

                total_dict['quantity'] = sum(lines.mapped('product_uom_qty'))
                total_dict['total_subtotal'] = sum(lines.mapped('price_subtotal'))

                # We also need to filter defect totals from gst and final total
                total_dict['gst'] = sum(lines.mapped('price_tax'))
                total_dict['final_total'] = sum(lines.mapped('price_total'))
                # total_dict['gst'] = doc.amount_tax
                # total_dict['final_total'] = doc.amount_total
                for group in groups:
                    total = sum(
                        lines.filtered(lambda l: int(l.line_group_id_value) == group.id).mapped('price_subtotal'))
                    total_qty = sum(
                        lines.filtered(lambda l: int(l.line_group_id_value) == group.id).mapped('product_uom_qty'))
                    groups_total_dict[group.id] = [total_qty, total]

                for code in sections:
                    total = sum(
                        lines.filtered(lambda l: int(l.line_section_id_value) == code.id).mapped('price_subtotal'))
                    codes_total_dict[code.id] = total

                lines_dict[doc.id] = lines
                lines_data.append(lines_dict)
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'company': self.env.company,
            'docs': docs,
            'order_lines': lines_data,
            'groups_total': groups_total_dict,
            'codes_total': codes_total_dict,
            'groups': groups,
            'total_dict': total_dict,

        }
