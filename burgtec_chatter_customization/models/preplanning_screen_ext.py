from odoo import api, fields, models, _
from markupsafe import Markup

approval_method_dict = {
    'shop_drawing': 'Shop Drawing',
    'approved_quote': 'Approved Quote',
    'spec_sheet': 'Spec Sheet'}

approval_status_dict = {
    'awaiting_approval': 'Awaiting Approval',
    'awaiting_revision': 'Awaiting Revision',
    'approved_with_comment': 'Approved with Comment',
    'fully_approved': 'Fully Approved By Customer',
}
line_item_status_dict = {

    'unschedule': 'Unscheduled',
    'sales_sales_court': 'Sales-Sales Court',
    'sales_customer_court': 'Sales-Customer Court',
    'technical_initial_check': 'Technical-Initial Check',
    'technical_final_check': 'Technical-Final Check',
    'technical_purchasing': 'Technical-Purchasing',
    'projects_awaiting_delivery': 'Projects-Awaiting Delivery',
    'projects_delivered': 'Projects-Delivered',
    'projects_installed': 'Projects-Installed',
}

class PreplanningScreenExt(models.Model):
    _name = 'sale.quote.planning.screen'
    _inherit = ['sale.quote.planning.screen', 'mail.thread', 'mail.activity.mixin']


    def write(self, vals):
        res = super().write(vals)
        commands = vals.get("sale_quote_line_ids")
        if not commands:
            return res
        sale_quote_planning_screen_line = self.env["sale.quote.planning.screen.line"]
        for rec in self:
            line_blocks = ""
            for cmd in commands:
                # cmd = (op, id, values); op 1 = update existing line
                if not isinstance(cmd, (list, tuple)) or len(cmd) < 3:
                    continue
                op, line_id, line_vals = cmd[0], cmd[1], cmd[2] or {}
                if op != 1:
                    continue

                line = sale_quote_planning_screen_line.browse(line_id)
                changes = ""
                if "lead_time" in line_vals:
                    changes += f"<li>Lead Time: {line.lead_time or '-'}</li>"

                if "sd_url" in line_vals:
                    changes += f"<li>SD URL: {line.sd_url or '-'}</li>"

                if "other_url" in line_vals:
                    changes += f"<li>Other URL: {line.other_url or '-'}</li>"

                if "is_fully_approved" in line_vals:
                    changes += f"<li>Fully Approved: {'Yes' if line.is_fully_approved else 'No'}</li>"

                if "approval_method" in line_vals:
                    changes += f"<li>Approval Method: {approval_method_dict.get(line.approval_method) or '-'}</li>"

                if "approval_status" in line_vals:
                    changes += f"<li>Approval Status: {approval_status_dict.get(line.approval_status) or '-'}</li>"

                if "line_item_status" in line_vals:
                    changes += f"<li>Line Item Status: {line_item_status_dict.get(line.line_item_status) or '-'}</li>"

                if "approval_required_by" in line_vals:
                    changes += f"<li>Approval Required By: {line.approval_required_by or '-'}</li>"

                if "requested_delivery_date" in line_vals:
                    changes += f"<li>Requested Delivery Date: {line.requested_delivery_date or '-'}</li>"

                if "approval_comments" in line_vals:
                    changes += f"<li>Approval Comments: {line.approval_comments or '-'}</li>"

                if "sales_comments" in line_vals:
                    changes += f"<li>Sales Comments: {line.sales_comments or '-'}</li>"

                if "technical_comments" in line_vals:
                    changes += f"<li>Technical Comments: {line.technical_comments or '-'}</li>"

                if "delivery_comments" in line_vals:
                    changes += f"<li>Delivery Comments: {line.delivery_comments or '-'}</li>"

                if not changes:
                    continue

                product = line.product_variant_id.display_name
                line_blocks += f"""
                      <div style="border-left: 3px solid #1565c0; padding: 6px 12px; margin: 8px 0; background: #f5f9ff;">
                          <p style="margin: 0 0 4px 0; font-weight: bold; color: #222;">
                              📦 Item #{line.item} — {product}
                          </p>
                          <ul style="margin: 0; padding-left: 20px;">{changes}</ul>
                      </div>
                  """

            if not line_blocks:
                continue

            message_body = Markup(f"""
                  <div style="background-color: #e3f2fd; border: 2px solid #1565c0; border-radius: 5px; padding: 6px; margin: 10px 0;">
                      <h4 style="color: #1565c0; margin: 0 0 10px 0;">
                          <span style="font-size: 18px;">✏️</span>Sales Quote Planning Screen Line(s) Updated
                      </h4>
                      {line_blocks}
                      <p style="margin: 10px 0 0 0; font-size: 12px; color: #000;">
                          Updated By: {self.env.user.name} on {fields.Datetime.now().strftime('%d-%m-%Y %H:%M:%S')}
                      </p>
                  </div>
              """)
            rec.message_post(
                body=message_body,
                subject='Sales Quote Planning Screen Line(s) Updated',
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        return res

