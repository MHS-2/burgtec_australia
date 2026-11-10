import re
from odoo import fields, models, _, api


class PurchaseOrderExt(models.Model):
    _inherit = 'purchase.order'

    sale_quote_reference = fields.Char('Project Quote Reference', copy=False)

    parent_po_id = fields.Many2one(
        'purchase.order',
        string='Parent PO',
    )
    child_purchase_order_ids = fields.Many2many(
        'purchase.order',
        'purchase_order_parent_child_rel',
        'parent_id',
        'child_id',
        string='Child POs',
    )
    child_pos_count = fields.Integer(compute='_compute_child_pos_count', store=True)
    parent_po_count = fields.Integer(compute='_compute_parent_po_count', store=True)
    deal_project_name = fields.Char(compute="_compute_deal_project_name", store=True)

    @api.depends('order_line.sale_order_id', 'order_line.sale_order_id.project_name', )
    def _compute_deal_project_name(self):
        for record in self:
            sales_order = False
            parent_purchase_order = False
            if record.tag == 'parent':
                sales_order = record._get_sale_orders()
                if not sales_order:
                    record.deal_project_name = False
                if sales_order:
                    record.deal_project_name = sales_order.project_name
            elif record.tag == 'child':
                parent_purchase_order = record.parent_po_id
                if not parent_purchase_order:
                    record.deal_project_name = False
                if parent_purchase_order:
                    record.deal_project_name = parent_purchase_order.deal_project_name
            else:
                record.deal_project_name = False

    @api.depends('child_purchase_order_ids')
    def _compute_child_pos_count(self):
        for order in self:
            child_purchase_order_ids = order.child_purchase_order_ids
            if order.tag == 'parent' and child_purchase_order_ids:
                order.child_pos_count = len(child_purchase_order_ids)
            else:
                order.child_pos_count = 0


    @api.depends('tag','parent_po_id')
    def _compute_parent_po_count(self):
        for order in self:
            parent_po_id = order.parent_po_id
            if order.tag == 'child' and parent_po_id:
                order.parent_po_count = 1
            else:
                order.parent_po_count = 0

    def action_open_bulk_date_wizard(self):
        """Open wizard to bulk update planned date"""
        return {
            'name': 'Set Expected Arrival Date',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.bulk.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'dialog_size': 'medium',
                'default_purchase_order_ids': self.ids,
            }
        }

    def action_show_parent_purchase_order(self):
        self.ensure_one()
        return {
            'name': _('Parent Purchase Order'),
            'res_id': self.parent_po_id.id,
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'context': {'create': False},
        }

    def action_show_child_purchase_orders(self):
        self.ensure_one()
        return {
            'name': _('Child Purchase Orders'),
            'domain': [('id', 'in', self.child_purchase_order_ids.ids)],
            'view_mode': 'list,form',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'context': {'create': False},
        }

    @api.depends('sale_quote_reference', 'child_po_count', 'delivery_stage')
    def _compute_po_ref(self):
        for record in self:
            ref = record.delivery_stage if record.is_old_data else record.sale_quote_reference

            if ref and record.tag == 'parent':
                record.burgtec_purchase_reference = f"PO-{ref}"
            elif ref and record.tag == 'child':
                record.burgtec_purchase_reference = f"PO-{ref}-{str(record.child_po_count).zfill(2)}"
            else:
                record.burgtec_purchase_reference = False

    def fix_parent_po_child_po_group_code(self):
        for record in self:
            group = ''
            code = ''
            order = False
            component = False
            component_lines = False
            order_lines = record.order_line
            child_po = False
            if order_lines:
                sale_lines = order_lines.mapped('sale_line_id')
                for line in sale_lines:
                    order = line.order_id
                    group = line.line_group_name
                    code = line.line_section_name
                    component = order.bom_component_id
                    child_po_line = False
                    if component:
                        # fetch componenets.
                        component_lines = component.component_line_ids.filtered(
                            lambda c: c.order_line_id.id == line.id and not c.is_parent)

                        # Child PO'S for each component according to their vendor.
                        for comp in component_lines:
                            child_po = record.child_purchase_order_ids.filtered(
                                lambda cpo: cpo.partner_id.id == comp.supplier_id.id)
                            # Now fetch the Purchase Order Line to set the line group and line section
                            child_po_line = child_po.order_line.filtered(
                                lambda ch: ch.product_id.id == comp.product_id.id and ch.note == comp.note)
                            # print(child_po_line)
                            child_po_line.sudo().write({
                                'line_group_name_child': group,
                                'line_section_name_child': code
                            })
    
    def remove_revision_string_from_project_quote_reference(self):
        for record in self:
            if record.sale_quote_reference:
                new_val = re.sub(r'\s*-?\s*Revision\s+\w+$', '', record.sale_quote_reference)
                record.sale_quote_reference = new_val.rstrip(' -')

    # Methods For Server Actions ------- 
    def remove_revision_string_from_project_quote_reference(self):
        for record in self:
            if record.sale_quote_reference:
                new_val = re.sub(r'\s*-?\s*Revision\s+\w+$', '', record.sale_quote_reference)
                record.sale_quote_reference = new_val.rstrip(' -')
    
    def _set_parent_po_count(self):
        for order in self:
            if order.tag == 'child' and order.origin:
                source_picking = self.env['stock.picking'].search([
                    ('name', '=', order.origin)
                ], limit=1)
                if source_picking and source_picking.origin:
                    parent_po = self.env['purchase.order'].search([
                        ('name', '=', source_picking.origin)
                    ], limit=1)
                    order.parent_po_id = parent_po
                    order.parent_po_count = 1 if parent_po else 0
                else:
                    order.parent_po_id = False
                    order.parent_po_count = 0
            parent_po_id = order.parent_po_id
            if order.tag == 'child' and parent_po_id:
                order.parent_po_count = 1
            else:
                order.parent_po_id = False
                order.parent_po_count = 0
    
    def _set_child_pos_count(self):
        for order in self:
            if order.tag == 'parent' and order.picking_ids:
                picking_names = order.picking_ids.mapped('name')
                child_pos = self.env['purchase.order'].search([
                    ('origin', 'in', picking_names)
                ])
                order.child_purchase_order_ids = child_pos
                order.child_pos_count = len(child_pos)
            child_purchase_order_ids = order.child_purchase_order_ids
            if order.tag == 'parent' and child_purchase_order_ids:
                order.child_pos_count = len(child_purchase_order_ids)
            else:
                order.child_purchase_order_ids = False
                order.child_pos_count = 0

