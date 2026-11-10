# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bom Component Cost Sync',
    'version': '18.1',
    'summary': 'Bom Component Cost Sync/Bulk Update Live Unit Cost of Bom Component Lines',
    'sequence': 10,
    'description': """ """,
    'category': 'Customizations',
    'website': '',
    'depends': ['base', 'bom_based_inventory','sale_custom_report','quotation_type_customization'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_bom_component_view_ext.xml',
        'wizard/component_bulk_cost_update_wizard.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
