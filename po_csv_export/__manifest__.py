{
    "name": "PO Excel Export (for Quotation Import)",
    "version": "18.0.2.0.0",
    "summary": "Export a Purchase Order to Excel (.xlsx) for import as a Quotation in the Odoo 19 instance",
    "author": "Byte Legions",
    "license": "LGPL-3",
    "category": "Purchases",
    "depends": ["purchase",'purchase_back_order_report'],
    "data": ["views/purchase_order_views.xml"],
    "installable": True,
}
