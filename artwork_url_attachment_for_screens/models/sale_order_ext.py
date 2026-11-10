from odoo import fields, models, api

class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(SaleOrderExt, self).create(vals_list)
        for record in res:
            preplanning_screen = False
            if not self.env.context.get('duplicating'):
                preplanning_screen = self.env['sale.quote.planning.screen'].sudo().create({
                    'order_id': record.id,
                    'stage_count': 0,
                })
                # attach it
                record.write({
                    'sale_quote_planning_screen_id': preplanning_screen.id,
                })
        return res

    def copy(self, default=None):
        default = dict(default or {})
        self.ensure_one()
        new_order = super(SaleOrderExt, self.with_context(duplicating=True)).copy(default)

        if self.sale_quote_planning_screen_id:
            old_lines = self.order_line.sorted(key=lambda l: (l.sequence, l.id))
            new_lines = new_order.order_line.sorted(key=lambda l: (l.sequence, l.id))
            line_map = {old.id: new.id for old, new in zip(old_lines, new_lines)}

            old_screen = self.sale_quote_planning_screen_id
            from_delivery_stage = bool(self.env.context.get('copied_from_new_delivery_stage'))  # added
            new_screen_lines = []
            for line in old_screen.sale_quote_line_ids:
                vals = {
                    # 'sale_quote_planning_screen_line_id': line.id,
                    'item': line.item,
                    'display_type': line.display_type,
                    'product_id': line.product_id.id,
                    'order_line_id': line_map.get(line.order_line_id.id) if line.order_line_id else False,
                    'lead_time': line.lead_time,
                    'requested_delivery_date': line.requested_delivery_date,
                    'approval_required_by': line.approval_required_by,
                    'approval_method': line.approval_method,
                    'approval_status': line.approval_status,
                    'line_item_status': line.line_item_status,
                    'approval_comments': line.approval_comments,
                    'sales_comments': line.sales_comments,
                    'technical_comments': line.technical_comments,
                    'delivery_comments': line.delivery_comments,
                    'sd_url': line.sd_url,
                    'internal_sd_url': line.internal_sd_url,
                    'other_url': line.other_url,
                    'artwork_image_url': line.artwork_image_url,
                    'attachment_id': line.attachment_id.id,
                }
                for i in range(1, 51):
                    field = f'do_stage_{i}'
                    vals[field] = getattr(line, field, 0)
                if from_delivery_stage:
                    vals['sale_quote_planning_screen_line_id'] = line.id
                new_screen_lines.append((0, 0, vals))
            if not self.env.context.get('copied_from_new_delivery_stage'):
                new_screen = self.env['sale.quote.planning.screen'].with_context(auto_create=True,
                                                                                 new_so=new_order.id).create({
                    'order_id': new_order.id,
                    'stage_count': old_screen.stage_count,
                    'sale_quote_line_ids': new_screen_lines,
                })
                new_order.sale_quote_planning_screen_id = new_screen.id
            else:
                new_planning_screen = self.env['planning.screen'].create({
                    'order_id': new_order.id,
                    'stage_count': old_screen.stage_count,
                    'line_ids': new_screen_lines,
                })
                new_order.planning_screen_id = new_planning_screen.id

        return new_order


