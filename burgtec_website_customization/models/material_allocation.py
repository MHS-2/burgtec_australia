from odoo import models, fields, api, _

class MaterialAllocation(models.Model):
    _name="material.allocation"
    _description = "Model For Material Allocation, inside product attribute values."

    name=fields.Char()
    