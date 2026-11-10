from odoo import api, fields, models, _
from markupsafe import Markup


class SaleOrderBomComponentExt(models.Model):
    _name = 'sale.order.bom.component'
    _inherit = ['sale.order.bom.component', 'mail.thread', 'mail.activity.mixin']

    def write(self, vals):
        res = super().write(vals)
        commands = vals.get("component_line_ids")
        if not commands:
            return res
        bom_component_line = self.env["sale.order.bom.component.line"]
        for rec in self:
            changes_by_line = {}
            for cmd in commands:
                # cmd = (op, id, values); op 1 = update existing line
                if not isinstance(cmd, (list, tuple)) or len(cmd) < 3:
                    continue
                op, line_id, line_vals = cmd[0], cmd[1], cmd[2] or {}
                if op != 1:
                    continue
                line = bom_component_line.browse(line_id)
                changes = ""
                if "product_qty" in line_vals:
                    changes += f"<li>Product Quantity: {line.product_qty or '-'}</li>"
                if "unit_component_quantity" in line_vals:
                    changes += f"<li>Unit Component Quantity : {line.unit_component_quantity or '-'}</li>"
                if "unit_sale_price" in line_vals:
                    changes += f"<li>Unit Sale Price: {line.unit_sale_price or '-'}</li>"
                if "total_sale_price" in line_vals:
                    changes += f"<li>Total Sale Price: {line.total_sale_price or '-'}</li>"
                if "manual_live_unit_cost" in line_vals:
                    changes += f"<li>Live Unit Cost: {line.manual_live_unit_cost or '-'}</li>"
                if "note" in line_vals:
                    changes += f"<li>Note: {line.note or '-'}</li>"
                if "supplier_id" in line_vals:
                    changes += f"<li>Supplier: {line.supplier_id.name if line.supplier_id else '-'}</li>"
                if "is_icr_register" in line_vals:
                    changes += f"<li>ICR Register: {'Yes' if line.is_icr_register else 'No'}</li>"
                if changes:
                    changes_by_line[line_id] = changes
            if not changes_by_line:
                continue

            groups = {}
            current_parent = bom_component_line
            for line in rec.component_line_ids:
                if line.is_parent:
                    current_parent = line
                if line.id not in changes_by_line:
                    continue
                changes = changes_by_line[line.id]
                parent_line = line if line.is_parent else current_parent
                group = groups.setdefault(parent_line, {"own": "", "children": ""})
                if line.is_parent:
                    group["own"] += f'<ul style="margin: 0 0 6px 0; padding-left: 20px;">{changes}</ul>'
                else:
                    group["children"] += f"""
                          <div style="border-left: 3px solid #90caf9; padding: 4px 12px; margin: 6px 0 6px 16px; background: #ffffff;">
                              <p style="margin: 0 0 4px 0; font-weight: bold; color: #1565c0;">
                                  {line.product_id.display_name}
                              </p>
                              <ul style="margin: 0; padding-left: 20px;">{changes}</ul>
                          </div>
                      """
            if not groups:
                continue

            line_blocks = ""
            for parent_line, group in groups.items():
                header = parent_line.product_id.display_name if parent_line else "Unassigned Components"
                line_blocks += f"""
                      <div style="border-left: 3px solid #1565c0; padding: 6px 12px; margin: 8px 0; background: #f5f9ff;">
                          <p style="margin: 0 0 6px 0; font-weight: bold; color: #2e7d32;">
                              {header}
                          </p>
                          {group["own"]}
                          {group["children"]}
                      </div>
                  """

            message_body = Markup(f"""
                  <div style="background-color: #e3f2fd; border: 2px solid #1565c0; border-radius: 5px; padding: 6px; margin: 10px 0;">
                      <h4 style="color: #1565c0; margin: 0 0 10px 0;">
                          <span style="font-size: 18px;">✏️</span>Bom Component Line(s) Updated
                      </h4>
                      {line_blocks}
                      <p style="margin: 10px 0 0 0; font-size: 12px; color: #000;">
                          Updated By: {self.env.user.name} on {fields.Datetime.now().strftime('%d-%m-%Y %H:%M:%S')}
                      </p>
                  </div>
              """)
            rec.message_post(
                body=message_body,
                subject='Bom Component Line(s) Updated',
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        return res


class SaleOrderBomComponentLineExt(models.Model):
    _inherit = 'sale.order.bom.component.line'
