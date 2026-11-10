import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class ProductProductExt(models.Model):
    _inherit = 'product.product'

    is_freight_or_assembly = fields.Boolean(string='Freight or Assembly')