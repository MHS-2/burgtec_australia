# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_custom_back_order_created = fields.Boolean()


    def action_custom_split_transfer(self):
        if all(float_is_zero(m.quantity, precision_rounding=m.product_uom.rounding) for m in self.move_ids):
            raise UserError(_("%s: Nothing to split. Fill the quantities you want in a new transfer in the done quantities", self.display_name))
        if all(float_compare(m.quantity, m.product_uom_qty, precision_rounding=m.product_uom.rounding) == 0 for m in self.move_ids):
            raise UserError(_("%s: Nothing to split, all demand is done. For split you need at least one line not fully fulfilled", self.display_name))
        if any(float_compare(m.quantity, m.product_uom_qty, precision_rounding=m.product_uom.rounding) > 0 for m in self.move_ids):
            raise UserError(_("%s: Can't split: quantities done can't be above demand", self.display_name))

        moves = self.move_ids.filtered(lambda m: m.state not in ('done', 'cancel') and m.quantity != 0)
        backorder_moves = moves._create_backorder()
        backorder_moves += self.move_ids.filtered(lambda m: m.quantity == 0)
        return self._create_backorder(backorder_moves=backorder_moves)

