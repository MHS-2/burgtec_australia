# Purchase List Report Module - Developer Documentation

## Module Overview

| Property | Value |
|----------|-------|
| **Technical Name** | `purchase_list_report` |
| **Version** | 0.1 |
| **Category** | Customizations |
| **License** | LGPL-3 |
| **Odoo Version** | 18.0 |

### Purpose

This module provides customized list views and reporting dashboards for Sales, Purchase, and Accounting operations. It creates organized reporting interfaces filtered by business categories, enabling quick access to relevant data for different operational groups.

---

## File Structure

```
purchase_list_report/
├── __init__.py                 # Module initialization (empty)
├── __manifest__.py             # Module manifest/metadata
├── DEVELOPER_DOCUMENTATION.md  # This documentation file
└── views/
    └── purchase_list_report_view.xml  # All views, actions, and menus
```

---

## Dependencies

| Module | Type | Purpose |
|--------|------|---------|
| `base` | Core | Odoo core framework |
| `account` | Core | Accounting and invoicing functionality |
| `bom_based_inventory` | Custom | Custom inventory management with BOM |
| `sale_custom_report` | Custom | Custom sales reporting features |
| `burgtec_hubspot_customization` | Custom | HubSpot CRM integration fields |
| `quotation_type_customization` | Custom | Quote type categorization system |

> **Note:** This module is part of the Burgtec customization ecosystem. All custom dependencies must be installed for proper functionality.

---

## Menu Structure

The module creates a hierarchical menu under the existing `purchase.purchase_report_main` menu:

```
Reporting
└── Purchase Report Main
    ├── Sales (sequence: 100)
    │   ├── Sales Group Quotations (sequence: 101)
    │   ├── Project Group Quotations (sequence: 102)
    │   └── Delivery Group Quotations (sequence: 103)
    │
    ├── Purchase (sequence: 104)
    │   ├── Child Purchase Order (sequence: 105)
    │   └── Child Purchase Order Report 2 (sequence: 106)
    │
    └── Accounting (sequence: 107)
        ├── Bill Report (sequence: 108)
        └── Invoice Report (sequence: 109)
```

---

## Views Reference

### Sales Order Views

#### 1. `sales_group_quotation_view`

| Property | Value |
|----------|-------|
| **XML ID** | `purchase_list_report.sales_group_quotation_view` |
| **Model** | `sale.order` |
| **Type** | List (tree) |
| **Location** | `views/purchase_list_report_view.xml:4-63` |

**Purpose:** Display sales quotations categorized under "Sales Group" with quoted cost metrics.

**Key Features:**
- Read-only view (no create, duplicate, or delete)
- Displays GP (Gross Profit) based on quoted costs
- Shows markup/margin percentages with red highlighting
- Includes HubSpot reference integration

**Fields Displayed:**

| Field | Widget | Notes |
|-------|--------|-------|
| `name` | - | Odoo Reference (bold, read-only) |
| `burgtec_quote_reference` | - | Primary reference (330px width) |
| `hubspot_reference` | - | HubSpot Deal Reference |
| `is_old_data` | boolean_toggle | Legacy data indicator |
| `project_name` | - | Project identifier |
| `quote_type` | badge | Color-coded by type |
| `create_date` | - | Creation timestamp |
| `partner_id` | - | Customer |
| `user_id` | many2one_avatar_user | Salesperson |
| `amount_untaxed` | monetary | Subtotal (with sum) |
| `amount_tax` | monetary | Tax amount (with sum) |
| `amount_total` | monetary | Total (with sum) |
| `invoice_status` | badge | Color-coded status |
| `state` | badge | Order state |
| `gp_quoted_cost` | monetary | Gross profit (red, with sum) |
| `percentage_markup_quoted_cost` | percentage | Markup % (red) |
| `percentage_margin_quoted_cost` | percentage | Margin % (red) |

---

#### 2. `project_group_quotation_view`

| Property | Value |
|----------|-------|
| **XML ID** | `purchase_list_report.project_group_quotation_view` |
| **Model** | `sale.order` |
| **Type** | List (tree) |
| **Location** | `views/purchase_list_report_view.xml:65-125` |

**Purpose:** Display project quotations with live cost metrics and invoicing details.

**Key Differences from Sales Group View:**
- Shows `amount_invoiced` and `amount_to_invoice` fields
- Uses live cost fields instead of quoted cost (`gp_live_cost`, `percentage_markup_live_cost`, `percentage_margin_live_cost`)
- Warning color scheme (orange) instead of danger (red)

---

#### 3. `delivery_stage_quotation_view`

| Property | Value |
|----------|-------|
| **XML ID** | `purchase_list_report.delivery_stage_quotation_view` |
| **Model** | `sale.order` |
| **Type** | List (tree) |
| **Location** | `views/purchase_list_report_view.xml:127-188` |

**Purpose:** Display delivery-stage quotations with dispatch tracking.

**Key Features:**
- Includes `hubspot_dispatch_date` field
- Live cost metrics (same as project group)
- No invoicing amount fields

---

### Purchase Order Views

#### 4. `child_po_report_list_view`

| Property | Value |
|----------|-------|
| **XML ID** | `purchase_list_report.child_po_report_list_view` |
| **Model** | `purchase.order` |
| **Type** | List (tree) |
| **Location** | `views/purchase_list_report_view.xml:190-228` |

**Purpose:** Display child purchase orders with status and link tracking.

**Row Decorations:**
- `decoration-info`: Draft or Sent state
- `decoration-muted`: Cancelled state

**Fields Displayed:**

| Field | Widget | Notes |
|-------|--------|-------|
| `name` | - | Odoo PO Reference |
| `burgtec_purchase_reference` | - | Primary reference (330px) |
| `partner_id` | - | Vendor (300px) |
| `is_builder_trend` | boolean_toggle | BuilderTrend integration flag |
| `partner_ref` | - | Vendor reference |
| `burgtec_po_status` | badge | Custom PO status |
| `warehouse_rack_location` | - | Warehouse location |
| `delivery_stage_link` | - | Delivery tracking link |
| `onedrive_po_folder_link` | - | OneDrive folder link |
| `date_planned` | - | Planned date |
| `hubspot_dispatch_date` | - | HubSpot dispatch date |
| `date_order` | remaining_days | Order date with countdown |
| `user_id` | many2one_avatar_user | Buyer |
| `delivery_stage` | - | Delivery stage |
| `sale_quote_reference` | - | Linked sales quote |
| `amount_untaxed` | monetary | Subtotal (with sum) |
| `amount_tax` | monetary | Tax (with sum) |
| `amount_total` | monetary | Total (with sum) |
| `invoice_status` | badge | Color-coded status |
| `state` | badge | PO state |

---

#### 5. `child_po_report_list_view_2`

| Property | Value |
|----------|-------|
| **XML ID** | `purchase_list_report.child_po_report_list_view_2` |
| **Model** | `purchase.order` |
| **Type** | List (tree) |
| **Location** | `views/purchase_list_report_view.xml:230-276` |

**Purpose:** Extended child PO view with intelligent receipt status coloring.

**Additional Features:**
- `receipt_status` field with date-based conditional decorations
- Color coding logic:
  - **Green (success):** Date planned is in the future OR full receipt before date
  - **Red (danger):** Date has passed without full receipt
  - **Yellow (warning):** Date is today

**Decoration Logic:**
```xml
decoration-success="(date_planned and date_planned > current_date) or
                    (effective_date and date_planned and effective_date &lt;= date_planned
                    and receipt_status == 'full')"
decoration-danger="date_planned and date_planned &lt; current_date and receipt_status != 'full'"
decoration-warning="date_planned and date_planned == current_date"
```

---

### Accounting Views

#### 6. `bills_report_list_view`

| Property | Value |
|----------|-------|
| **XML ID** | `purchase_list_report.bills_report_list_view` |
| **Model** | `account.move` |
| **Type** | List (tree) |
| **Location** | `views/purchase_list_report_view.xml:279-320` |

**Purpose:** Display vendor bills with payment tracking.

**Row Decorations:**
- `decoration-warning`: Invoice date is set (highlights for attention)

**Key Fields:**

| Field | Widget | Notes |
|-------|--------|-------|
| `name` | - | Odoo Reference (optional) |
| `burgtec_bill_reference` | - | Primary reference (350px) |
| `invoice_partner_display_name` | - | Vendor name |
| `invoice_date` | - | Bill date |
| `date` | - | Accounting date |
| `invoice_date_due` | remaining_days | Due date with countdown |
| `invoice_origin` | - | Source document |
| `payment_reference` | - | Payment ref |
| `ref` | - | Reference |
| `purchase_order_name` | - | Linked PO (bold) |
| `amount_total_in_currency_signed` | - | Total amount (bold, warning) |
| `amount_residual_signed` | - | Amount due |
| `status_in_payment` | badge | Payment status (color-coded) |
| `move_type` | - | Document type |

---

#### 7. `invoices_report_list_view`

| Property | Value |
|----------|-------|
| **XML ID** | `purchase_list_report.invoices_report_list_view` |
| **Model** | `account.move` |
| **Type** | List (tree) |
| **Location** | `views/purchase_list_report_view.xml:322-363` |

**Purpose:** Display customer invoices with payment tracking.

**Structure:** Similar to bills view but configured for outgoing invoices (`out_invoice`, `out_refund`).

---

## Window Actions Reference

| XML ID | Name | Model | Domain Filter |
|--------|------|-------|---------------|
| `action_quotations_with_sales_group` | Sales Group Quotations | `sale.order` | `quote_type = 'sales_quote'`, `state != 'cancel'` |
| `action_quotations_with_project_group` | Project Group Quotations | `sale.order` | `quote_type = 'project_quote'`, `state != 'cancel'` |
| `action_quotations_with_delivery_stage` | Delivery Group Quotations | `sale.order` | `quote_type = 'delivery_stage'`, `state != 'cancel'` |
| `action_child_po_report` | Child Purchase Order | `purchase.order` | `tag = 'child'`, `state != 'cancel'` |
| `action_child_po_report_2` | Child Purchase Order Report 2 | `purchase.order` | `tag = 'child'`, `state != 'cancel'` |
| `action_bills_report_list_view` | Bill Report | `account.move` | `move_type in ['in_invoice', 'in_refund']` |
| `action_invoices_report_list_view` | Invoice Report | `account.move` | `move_type in ['out_invoice', 'out_refund']` |

---

## Custom Fields Reference

This module displays custom fields defined in dependent modules:

### Sale Order Fields (from dependencies)

| Field | Type | Source Module |
|-------|------|---------------|
| `burgtec_quote_reference` | Char | `sale_custom_report` |
| `hubspot_reference` | Char | `burgtec_hubspot_customization` |
| `hubspot_dispatch_date` | Date | `burgtec_hubspot_customization` |
| `is_old_data` | Boolean | `sale_custom_report` |
| `project_name` | Char | `sale_custom_report` |
| `quote_type` | Selection | `quotation_type_customization` |
| `gp_quoted_cost` | Monetary | `sale_custom_report` |
| `gp_live_cost` | Monetary | `sale_custom_report` |
| `percentage_markup_quoted_cost` | Float | `sale_custom_report` |
| `percentage_margin_quoted_cost` | Float | `sale_custom_report` |
| `percentage_markup_live_cost` | Float | `sale_custom_report` |
| `percentage_margin_live_cost` | Float | `sale_custom_report` |
| `amount_invoiced` | Monetary | `sale_custom_report` |
| `amount_to_invoice` | Monetary | `sale_custom_report` |

### Purchase Order Fields (from dependencies)

| Field | Type | Source Module |
|-------|------|---------------|
| `burgtec_purchase_reference` | Char | Custom |
| `is_builder_trend` | Boolean | Custom |
| `burgtec_po_status` | Selection | Custom |
| `warehouse_rack_location` | Char | `bom_based_inventory` |
| `delivery_stage_link` | Char | Custom |
| `onedrive_po_folder_link` | Char | Custom |
| `hubspot_dispatch_date` | Date | `burgtec_hubspot_customization` |
| `delivery_stage` | Selection | Custom |
| `sale_quote_reference` | Many2one | Custom |
| `tag` | Selection | Custom |

### Account Move Fields (from dependencies)

| Field | Type | Source Module |
|-------|------|---------------|
| `burgtec_bill_reference` | Char | Custom |
| `purchase_order_name` | Char | Custom |
| `status_in_payment` | Selection | Custom |

---

## Security

This module does not define its own access control rules. Security is implemented through:

1. **View-level restrictions:** All list views have `create="0" duplicate="0" delete="0"` attributes
2. **Inherited permissions:** Relies on access rules from `sale`, `purchase`, and `account` modules
3. **Column visibility:** Uses `column_invisible` and `groups` attributes for conditional field display

---

## Extending This Module

### Adding a New View

1. Create a new tree view in `views/purchase_list_report_view.xml`:

```xml
<record id="my_custom_view" model="ir.ui.view">
    <field name="name">my.custom.view</field>
    <field name="model">model.name</field>
    <field name="arch" type="xml">
        <tree string="My View" create="0" duplicate="0" delete="0">
            <!-- fields here -->
        </tree>
    </field>
</record>
```

2. Create a window action:

```xml
<record id="action_my_custom_view" model="ir.actions.act_window">
    <field name="name">My Custom Report</field>
    <field name="res_model">model.name</field>
    <field name="view_mode">tree</field>
    <field name="view_id" ref="my_custom_view"/>
    <field name="domain">[('field', '=', 'value')]</field>
</record>
```

3. Add a menu item:

```xml
<menuitem id="menu_my_custom"
    name="My Custom Report"
    parent="purchase_list_report.parent_menu_id"
    action="action_my_custom_view"
    sequence="110"/>
```

### Adding Fields to Existing Views

Use view inheritance:

```xml
<record id="sales_group_quotation_view_inherit" model="ir.ui.view">
    <field name="name">sales.group.quotation.view.inherit</field>
    <field name="model">sale.order</field>
    <field name="inherit_id" ref="purchase_list_report.sales_group_quotation_view"/>
    <field name="arch" type="xml">
        <field name="amount_total" position="after">
            <field name="my_custom_field"/>
        </field>
    </field>
</record>
```

---

## Common Patterns Used

### Badge Widget with Color Coding

```xml
<field name="state" widget="badge"
       decoration-success="state == 'sale'"
       decoration-info="state == 'draft'"
       decoration-warning="state == 'sent'"/>
```

### Monetary Fields with Sum

```xml
<field name="amount_total" widget="monetary" sum="Total"/>
```

### Conditional Column Visibility

```xml
<field name="field_name" column_invisible="context.get('hide_field')"/>
```

### Avatar Widget for Users

```xml
<field name="user_id" widget="many2one_avatar_user"/>
```

### Remaining Days Widget

```xml
<field name="date_order" widget="remaining_days"/>
```

---

## Troubleshooting

### Views Not Appearing

1. Check that all dependent modules are installed
2. Verify menu parent reference exists (`purchase.purchase_report_main`)
3. Clear browser cache and restart Odoo

### Fields Not Displaying

1. Ensure the field exists in the model (check dependent modules)
2. Verify user has access to the field's group (if restricted)
3. Check `column_invisible` conditions

### Domain Filters Not Working

1. Verify field values match domain conditions exactly
2. Check for correct quote type values: `'sales_quote'`, `'project_quote'`, `'delivery_stage'`
3. Verify `tag` field values for purchase orders

---

## Changelog

### Version 0.1 (Initial Release)
- Created sales quotation views (3 variants by quote type)
- Created purchase order views (2 variants)
- Created accounting views (bills and invoices)
- Implemented hierarchical menu structure
- Added color-coded badges and status indicators
- Integrated HubSpot reference fields
- Added gross profit and margin calculations display

---

## Support

For issues related to this module, check:

1. Dependent module documentation
2. Odoo 18 view reference documentation
3. Custom field definitions in source modules

---

*Last Updated: December 2024*
*Odoo Version: 18.0*