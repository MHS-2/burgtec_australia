from odoo import api, fields, models


class ColorPicker(models.Model):
    """We can store the fields on this model temporarily and used to save"""
    _name = 'color.picker'
    _description = "Color Picker"

    record_id = fields.Integer(string="Record Id", help='Record id of color')
    res_model = fields.Char(string="Model", help='Corresponding model')
    color = fields.Char(string="Color", help='Color code')

