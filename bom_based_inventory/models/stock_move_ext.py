from odoo import _, api, Command, fields, models


PROCUREMENT_PRIORITIES = [('0', 'Normal'), ('1', 'Urgent')]


class StockMoveExt(models.Model):
    _inherit = 'stock.move'


    def _action_confirm(self, merge=True, merge_into=False):
        if len(self) > 1:
            product_3_present = any(move.product_id.id == 3 for move in self)

            # Create a new move for product_id=3 if not present
            if not product_3_present:
                new_move_vals = {
                    'product_id': 13,
                    'product_uom_qty': 2.0,  # Example quantity
                    'product_uom': self.env.ref('uom.product_uom_unit').id,
                    'location_id': self.env.ref('stock.stock_location_stock').id,
                    'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                    'procure_method': 'make_to_order',  # To trigger procurement
                    'state': 'draft',
                    'name': 'imran',
                    'group_id':self[0].group_id.id,
                    'location_dest_id':self[0].location_dest_id.id,
                    'location_id':self[0].location_id.id,
                    'origin':self[0].origin,
                    'picking_type_id':self[0].picking_type_id.id,
                    'raw_material_production_id':self[0].raw_material_production_id.id,
                    'reference':self[0].reference,
                    'rule_id':self[0].rule_id.id,
                    # Add other required fields (e.g., picking_id, rule_id)
                }
                new_move = self.env['stock.move'].create(new_move_vals)
                self |= new_move  # Add new_move to the current recordset
        return  super(StockMoveExt,self)._action_confirm(merge=True, merge_into=False)


