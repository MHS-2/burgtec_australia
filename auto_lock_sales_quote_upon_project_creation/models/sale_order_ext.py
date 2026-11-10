from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    is_frozen_due_to_project_creation = fields.Boolean('Is Freeze Sale Quotation Due to Creation of Revision/Project',
                                                       copy=False,
                                                       default=False, tracking=True)


    def compute_sales_planning_screen_line_item_status(self):
        for record in self:
            if record.quote_type == 'sales_quote' and record.sale_quote_planning_screen_id and not record.child_sale_order_ids:
                record.sale_quote_planning_screen_id._compute_line_item_status_quantity()



    def _make_sales_quote_freeze_check_true(self):
        sales_quotes = self.env['sale.order'].search(
            [('quote_type', '=', 'sales_quote'), ('is_frozen_due_to_project_creation', '=', False)])
        for record in sales_quotes:
            odoo_reference_on_sales_quote = record.name.split("-")[0].strip()
            if record.child_sale_order_ids:
                all_sale_quote_revisions = record.env['sale.order'].search([
                    ('quote_type', '=', 'sales_quote'),
                    ('name', 'ilike', odoo_reference_on_sales_quote),
                    ('is_frozen_due_to_project_creation', '=', False)
                ])
                if all_sale_quote_revisions:
                    all_sale_quote_revisions.write({
                        'is_frozen_due_to_project_creation': True,
                    })
                    sales_quotes = sales_quotes - all_sale_quote_revisions
            elif not record.child_sale_order_ids:
                all_previous_sale_quote_revisions = record.env['sale.order'].search([
                    ('quote_type', '=', 'sales_quote'),
                    ('name', 'ilike', odoo_reference_on_sales_quote),
                    ('id', '!=', record.id),
                    ('is_frozen_due_to_project_creation', '=', False)
                ])
                if all_previous_sale_quote_revisions:
                    all_previous_sale_quote_revisions.write({
                        'is_frozen_due_to_project_creation': True,
                    })
                    sales_quotes = sales_quotes - all_previous_sale_quote_revisions

    def _make_sales_quote_freeze_check_true_server_action(self):
        self.ensure_one()
        odoo_reference_on_sales_quote = self.name.split("-")[0].strip()
        if self.quote_type == 'sales_quote' and self.child_sale_order_ids:
            self.is_frozen_due_to_project_creation = True
            return
        next_revision_exists = self.env['sale.order'].search_count([
            ('quote_type', '=', 'sales_quote'),
            ('name', 'ilike', odoo_reference_on_sales_quote),
            ('id', '>', self.id),
        ]) > 0
        if next_revision_exists:
            self.is_frozen_due_to_project_creation = True



    def copy(self, default=None):
        default = default or {}
        new_order = super(SaleOrderExt, self).copy(default)
        base_name = new_order.name.split("-")[0].strip()
        all_previous_revision = self.env['sale.order'].search([
            ('quote_type', '=', 'sales_quote'),
            ('name', 'ilike', base_name),
            ('id', '!=', new_order.id),
        ])
        all_previous_revision.write({
            'is_frozen_due_to_project_creation': True,
        })
        old_screen = self.sale_quote_planning_screen_id
        old_screen.line_item_status_ids.write({
            'crm_lead_id':False
        })
        return new_order

    def create_new_delivery_stage(self):
        for record in self:
            if record.quote_type == 'project_quote':
                raise UserError(_('You are not allowed to create Project from Project!'))

            if record.state == 'draft':
                raise UserError(_('Project Can Only Be Created In Quotation Sent State.'))

            if self.quote_type == 'sales_quote':
                odoo_reference_on_sales_quote = self.name.split("-")[0].strip()
                project_quotes = self.env['sale.order'].search([
                    ('quote_type', '=', 'project_quote'),
                    ('name', 'ilike', odoo_reference_on_sales_quote)
                ])
                # projects_quotations = self.child_sale_order_ids.filtered(lambda so: so.quote_type == 'project_quote')
                if project_quotes:
                    raise ValidationError(
                        _("You Can Only Generate One Project From Sale Quote"))

            # Now set few things in this quotation to make it different from all others.
            # parent quote
            child_quote = False
            updated_count = record.reference_count + 1
            # stage_ref = f"{self.burgtec_quote_reference}-001"
            stage_ref = f"{self.burgtec_quote_reference[:6]}"
            sale_write_vals = {
                'is_sales_quote': True,
                'is_parent_sale_order': True,
                'quote_type': 'sales_quote',
                'reference_count': updated_count,
                'delivery_stage_reference_number': f"D{updated_count}",
                'state': 'sent',
                # 'new_sale_order_number': stage_ref,

            }
            res = record.write(sale_write_vals)
            child_sale_order_vals = {
                'burgtec_quote_reference': stage_ref,
                'name': f"{record.name}",
                'quote_type': 'project_quote',
                'is_project_quote': True,
                'source_sale_order_name': self.name,
                'source_sale_order_id': self.id,
                'is_child_sale_order': True,
                'state': 'quotation_confirmed',
                'is_old_data': False,
                'system_revision': record.system_revision,
                'location': record.location,
            }
            if res:
                child_quote = record.with_context(copied_from_new_delivery_stage=True).copy()
                child_quote.write(
                    child_sale_order_vals
                )

                if child_quote:
                    base_name = record.name.split("-")[0].strip()

                    all_sale_quotes = self.env['sale.order'].search([
                        ('quote_type', '=', 'sales_quote'),
                        ('name', 'ilike', base_name)
                    ])

                    all_sale_quotes.write({
                        'is_frozen_due_to_project_creation': True,
                        'state': 'sent',
                    })

                record.update(
                    {
                        'child_sale_order_ids': [(4, child_quote.id)],
                    }
                )
                return child_quote.id

    def action_show_wizard_to_add_group(self):
        if self.is_frozen_due_to_project_creation:
            return None
        return super().action_show_wizard_to_add_group()

    def freeze_previous_sales_quote_if_project_already_created(self):
        for record in self:
            if record.quote_type == 'sales_quote' and record.child_sale_order_ids:
                odoo_reference_on_sales_quote = record.name.split("-")[0].strip()
                all_sale_quote_revisions = record.env['sale.order'].search([
                    ('quote_type', '=', 'sales_quote'),
                    ('name', 'ilike', odoo_reference_on_sales_quote)
                ])
                all_sale_quote_revisions.write({
                    'is_frozen_due_to_project_creation': True,
                    'state': 'sent',
                })

    def unlink(self):
        for record in self:
            if record.quote_type == 'project_quote':
                parent_sale_order_name = record.source_sale_order_name
                base_name = parent_sale_order_name.split("-")[0].strip()
                related_sales = self.env['sale.order'].search([
                    ('quote_type', '=', 'sales_quote'),
                    ('name', 'ilike', base_name)
                ])
                related_sales.write({
                    'is_frozen_due_to_project_creation': False,
                })

        return super(SaleOrderExt, self).unlink()


class SaleOrderLineExt(models.Model):
    _inherit = 'sale.order.line'


    def action_show_wizard_to_add_code(self):
        if self.order_id.is_frozen_due_to_project_creation:
            return None
        return super().action_show_wizard_to_add_code()

    def action_show_wizard_to_add_product(self):
        if self.order_id.is_frozen_due_to_project_creation:
            return None
        return super().action_show_wizard_to_add_product()

    def action_show_wizard_to_swap_groups(self):
        if self.order_id.is_frozen_due_to_project_creation:
            return None
        return super().action_show_wizard_to_swap_groups()

    def action_show_wizard_to_swap_codes(self):
        if self.order_id.is_frozen_due_to_project_creation:
            return None
        return super().action_show_wizard_to_swap_codes()
