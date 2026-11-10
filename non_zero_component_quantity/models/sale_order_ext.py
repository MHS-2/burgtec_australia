from numpy.random.mtrand import pareto
import logging
from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)


class SaleOrderExt(models.Model):
    _inherit = 'sale.order'


    system_cost_per_unit = fields.Float(compute='_compute_multi_costs', store=True)
    live_unit_cost = fields.Float(compute='_compute_multi_costs', store=True)
    quoted_cost_per_unit = fields.Float(compute='_compute_multi_costs', store=True)
    pre_project_cost_per_unit = fields.Float(compute='_compute_multi_costs', store=True)

    percentage_margin_system_cost = fields.Float(compute='_compute_multi_costs', store=True)
    percentage_margin_live_cost = fields.Float(compute='_compute_multi_costs', store=True)
    percentage_margin_quoted_cost = fields.Float(compute='_compute_multi_costs', store=True)
    percentage_margin_pre_project_cost = fields.Float(compute='_compute_multi_costs', store=True)

    percentage_markup_system_cost = fields.Float(compute='_compute_multi_costs', store=True)
    percentage_markup_live_cost = fields.Float(compute='_compute_multi_costs', store=True)
    percentage_markup_quoted_cost = fields.Float(compute='_compute_multi_costs', store=True)
    percentage_markup_pre_project_cost = fields.Float(compute='_compute_multi_costs', store=True)

    defected_amount_untaxed = fields.Monetary(compute="compute_defected_amounts",store=True)
    defected_total_live_cost = fields.Monetary(compute="compute_defected_amounts",store=True)
    

    total_amount_untaxed_exl_defect = fields.Monetary(compute="compute_total_defected_amounts",store=True)
    total_gp_exl_defect = fields.Monetary(compute="compute_total_defected_amounts",store=True)

    percentage_margin_live_cost_exl_defect = fields.Float(compute='compute_defect_excl_percentage', store=True)
    percentage_markup_live_cost_exl_defect = fields.Float(compute='compute_defect_excl_percentage', store=True)



    def _non_zero_previous_bom_handling(self):
        for record in self:
            if record.bom_component_id:
                all_lines = record.bom_component_id.component_line_ids
                parent_lines = all_lines.filtered(lambda line: line.is_parent)

                for line in parent_lines:
                    parent_quantity = line.product_qty
                    tmpl_id = line.product_id.product_tmpl_id

                    child_lines = all_lines.filtered(
                        lambda l: not l.is_parent
                                  and not l.display_type
                                  and l.order_line_id == line.order_line_id
                    )
                    for child_line in child_lines:
                        child_quantity = child_line.product_qty
                        if parent_quantity > 0 and child_quantity > 0:
                            unit_qty = child_quantity / parent_quantity
                        elif parent_quantity == 0 and child_quantity > 0:
                            unit_qty = child_quantity
                        elif parent_quantity > 0 and child_quantity == 0:
                            unit_qty = 1
                        else:
                            unit_qty = 1
                        child_line.write({
                            'unit_component_quantity': unit_qty
                        })
    
    @api.depends('order_line','bom_component_id','bom_component_id.total_parent_live_unit_cost','bom_component_id.total_parent_pre_project_cost_per_unit','bom_component_id.total_parent_product_sale_price','bom_component_id.total_parent_quoted_cost_per_unit','bom_component_id.total_parent_system_cost_per_unit')
    def _compute_multi_costs(self):
        for record in self:
            product_lines = False
            bom_lines = False
            sale_price = False
            bom_component = False
            bom_component = record.bom_component_id
            sale_price = 0.0
            total_margin_system_cost = 0.0
            total_margin_live_cost = 0.0
            total_margin_quoted_cost = 0.0
            total_margin_pre_project_cost = 0.0
            sum_bom = 0.0
            other_cost = 0.0
            total_sum_bom = 0.0

            if not bom_component:
                product_lines = record.order_line.filtered(lambda l: l.product_id)
                if product_lines:
                    # sum_bom = 0.0
                    # other_cost = 0.0

                    # line = product_lines[0]
                    for line in product_lines:
                        bom_dict = record.env['mrp.bom']._bom_find(line.product_id)
                        bom = bom_dict.get(line.product_id)
                        if bom:
                            bom_lines = bom.bom_line_ids
                            for bom_line in bom_lines:
                                sum_bom += bom_line.product_id.standard_price * bom_line.product_qty
                            # print('------->>>',sum_bom)
                            # print('------->>>',line.product_uom_qty)
                            total_sum_bom = sum_bom * line.product_uom_qty
                            sum_bom = 0.0
                            # print('------->>>',total_sum_bom)

                    record.system_cost_per_unit = record.amount_untaxed - total_sum_bom
                    record.live_unit_cost = record.amount_untaxed - total_sum_bom
                    record.quoted_cost_per_unit = 0
                    record.pre_project_cost_per_unit = 0

                    record.percentage_margin_system_cost = (
                        ((record.amount_untaxed - total_sum_bom) / record.amount_untaxed) if record.amount_untaxed else 0.0
                    )
                    record.percentage_margin_live_cost = record.percentage_margin_system_cost
                    record.percentage_margin_quoted_cost = (
                        ((record.amount_untaxed - other_cost) / record.amount_untaxed) if record.amount_untaxed else 0.0
                    )
                    record.percentage_margin_pre_project_cost = record.percentage_margin_quoted_cost

                    record.percentage_markup_system_cost = (
                        (record.amount_untaxed - total_sum_bom) / total_sum_bom if total_sum_bom else 0.0
                    )
                    record.percentage_markup_live_cost = record.percentage_markup_system_cost
                    record.percentage_markup_quoted_cost = (
                        (record.amount_untaxed - other_cost) / other_cost if other_cost else 0.0
                    )
                    record.percentage_markup_pre_project_cost = record.percentage_markup_quoted_cost


                    # print('Total Qty: ', total_qty)

                    record.live_cost_bom_total = total_sum_bom 
                    record.system_cost_bom_total = total_sum_bom 
                    record.pre_project_cost_bom_total = 0
                    record.quoted_cost_bom_total = 0

                else:
                    record.system_cost_per_unit = 0
                    record.live_unit_cost = 0
                    record.quoted_cost_per_unit = 0
                    record.pre_project_cost_per_unit = 0
                    record.percentage_margin_system_cost = 0
                    record.percentage_margin_live_cost = 0
                    record.percentage_margin_quoted_cost = 0
                    record.percentage_margin_pre_project_cost = 0
                    record.percentage_markup_system_cost = 0
                    record.percentage_markup_live_cost = 0
                    record.percentage_markup_quoted_cost = 0
                    record.percentage_markup_pre_project_cost = 0
                    record.live_cost_bom_total = 0
                    record.system_cost_bom_total = 0
                    record.pre_project_cost_bom_total = 0
                    record.quoted_cost_bom_total = 0

            if bom_component:
                sale_price = bom_component.total_parent_product_sale_price
                total_margin_system_cost = bom_component.total_parent_system_cost_per_unit
                total_margin_live_cost = bom_component.total_parent_live_unit_cost
                total_margin_quoted_cost = bom_component.total_parent_quoted_cost_per_unit 
                total_margin_pre_project_cost = bom_component.total_parent_pre_project_cost_per_unit

                # Margin %
                record.percentage_margin_system_cost = (sale_price - total_margin_system_cost) / sale_price if sale_price else 0.0
                record.percentage_margin_live_cost = (sale_price - total_margin_live_cost) / sale_price if sale_price else 0.0
                record.percentage_margin_quoted_cost = (sale_price - total_margin_quoted_cost) / sale_price if sale_price else 0.0
                record.percentage_margin_pre_project_cost = (sale_price - total_margin_pre_project_cost) / sale_price if sale_price else 0.0

                # Markup %
                record.percentage_markup_system_cost = (
                    (sale_price - total_margin_system_cost) / total_margin_system_cost
                    if total_margin_system_cost else 0.0
                )
                record.percentage_markup_live_cost = (
                    (sale_price - total_margin_live_cost) / total_margin_live_cost
                    if total_margin_live_cost else 0.0
                )
                record.percentage_markup_quoted_cost = (
                    (sale_price - total_margin_quoted_cost) / total_margin_quoted_cost
                    if total_margin_quoted_cost else 0.0
                )
                record.percentage_markup_pre_project_cost = (
                    (sale_price - total_margin_pre_project_cost) / total_margin_pre_project_cost
                    if total_margin_pre_project_cost else 0.0
                )
                record.system_cost_per_unit = record.amount_untaxed - total_margin_system_cost
                record.live_unit_cost = record.amount_untaxed - total_margin_live_cost
                record.quoted_cost_per_unit = record.amount_untaxed - total_margin_quoted_cost 
                record.pre_project_cost_per_unit = record.amount_untaxed - total_margin_pre_project_cost
    
    @api.depends('bom_component_id','order_line','order_line.price_subtotal','bom_component_id.component_line_ids.live_unit_cost')
    def compute_defected_amounts(self):
        for order in self:
            defected_order_product_lines = False
            defected_parent_lines =  False
            defect_groups = order.defected_line_ids
            bom_component = order.bom_component_id
            if not defect_groups:
                order.defected_amount_untaxed = 0
                order.defected_total_live_cost = 0
                continue
            if defect_groups:
                defected_order_product_lines = order.order_line.filtered(lambda o:not o.display_type and int(o.line_group_id_value) in defect_groups.ids)
                if not defected_order_product_lines:
                    order.defected_amount_untaxed = 0
                    order.defected_total_live_cost = 0
                    continue
                if defected_order_product_lines:
                    defected_parent_lines = bom_component.component_line_ids.filtered(lambda b:b.order_line_id.id in defected_order_product_lines.ids and b.is_parent)
                    order.defected_amount_untaxed = sum(defected_order_product_lines.mapped('price_subtotal'))
                    order.defected_total_live_cost = sum(defected_parent_lines.mapped('live_unit_cost'))
    
    @api.depends('defected_amount_untaxed','defected_total_live_cost')
    def compute_total_defected_amounts(self):
        for order in self:
            excl_amount = 0
            bom = order.bom_component_id
            total_parent_live_unit_cost = 0
            if not bom:
                order.total_gp_exl_defect = 0
            if order.defected_amount_untaxed == 0:
                excl_amount = order.amount_untaxed
                order.total_amount_untaxed_exl_defect = excl_amount
            if order.defected_amount_untaxed > 0:
                excl_amount = order.amount_untaxed - order.defected_amount_untaxed
                order.total_amount_untaxed_exl_defect = excl_amount
            if bom:
                if order.defected_total_live_cost > 0:
                    total_parent_live_unit_cost = bom.total_parent_live_unit_cost
                    order.total_gp_exl_defect = excl_amount - (total_parent_live_unit_cost - order.defected_total_live_cost)
                else:
                    order.total_gp_exl_defect = 0

    @api.depends('total_gp_exl_defect','total_amount_untaxed_exl_defect')
    def compute_defect_excl_percentage(self):
        for order in self:
            bom = order.bom_component_id
            total_parent_live_unit_cost = bom.total_parent_live_unit_cost
            total_live_cost = total_parent_live_unit_cost - order.defected_total_live_cost
            
            amount_cost_diff_excl = order.total_gp_exl_defect
            # Margin %
            order.percentage_margin_live_cost_exl_defect = (amount_cost_diff_excl) / order.total_amount_untaxed_exl_defect if order.total_amount_untaxed_exl_defect else 0.0

            # Markup %
            order.percentage_markup_live_cost_exl_defect = (
                    (amount_cost_diff_excl) / total_live_cost
                    if total_live_cost else 0.0
                )
            

class SaleOrderLineExt(models.Model):
    _inherit = 'sale.order.line'

    def unlink(self):
        bom = False
        delete = False
        for record in self:
            if not delete and not record.display_type:
                delete = True
                bom = record.order_id.bom_component_id
        res = super(SaleOrderLineExt, self).unlink()
        if bom:
            bom._compute_multi_total_from_bom_lines()
        return res