# Quotation Type Customization - Developer Documentation

**Module:** `quotation_type_customization`
**Version:** 18.0.1.0.0
**License:** LGPL-3
**Category:** Customizations

---

## Table of Contents

1. [Overview](#overview)
2. [Module Structure](#module-structure)
3. [Dependencies](#dependencies)
4. [Security & Access Control](#security--access-control)
5. [Models Reference](#models-reference)
   - [SaleOrderExt](#saleorderext)
   - [SaleOrderLineExt](#saleorderlineext)
   - [SaleOrderSeries](#saleorderseries)
   - [PlanningScreenExt](#planningscreenext)
   - [PlanningScreenLineExt](#planningscreenlineext)
   - [PurchaseOrderExt](#purchaseorderext)
   - [AccountMoveExt](#accountmoveext)
   - [StockRuleExt](#stockruleext)
   - [BOM Component Extensions](#bom-component-extensions)
6. [Wizards](#wizards)
7. [Views & UI Components](#views--ui-components)
8. [Business Workflows](#business-workflows)
9. [Data Initialization](#data-initialization)
10. [API Reference](#api-reference)
11. [Extension Points](#extension-points)

---

## Overview

This module extends Odoo 18's sales functionality to support a hierarchical quotation system with three distinct quote types:

| Quote Type | Purpose | Parent | Children |
|------------|---------|--------|----------|
| **Sales Quote** | Initial customer quotation | None | Project Quote |
| **Project Quote** | Planning & approval stage | Sales Quote | Delivery Stages |
| **Delivery Stage** | Specific delivery phase | Project Quote | None |

### Key Features

- Hierarchical quote structure with parent-child relationships
- 9 configurable number series for reference generation (100,000 - 999,999)
- Planning screen with 50 delivery stage slots
- Product approval workflow with admin controls
- Automatic purchase order creation with parent-child PO structure
- Custom invoice reference generation
- Excel export for delivery stage planning
- HubSpot reference integration

---

## Module Structure

```
quotation_type_customization/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── sale_order_ext.py              # Core sale order extension (894 lines)
│   ├── sale_order_series.py           # Number series management
│   ├── planning_screen_ext.py         # Planning & delivery stages (1185 lines)
│   ├── stock_rule_ext.py              # Purchase order rules (422 lines)
│   ├── account_move_ext.py            # Invoice extensions
│   ├── purchase_order_ext.py          # Purchase order extensions
│   ├── sale_order_bom_component_ext.py # BOM component extensions
│   └── delivery_code_calculation_ext.py
├── views/
│   ├── sale_order_ext.xml             # Main sale order views
│   ├── sale_order_series.xml          # Series configuration views
│   ├── planning_screen_ext.xml        # Planning screen views
│   ├── account_move_ext.xml           # Invoice views
│   ├── purchase_order_view_ext.xml    # Purchase order views
│   ├── bom_based_inventory_ext.xml    # BOM inventory views
│   └── delivery_code_calculation_view_ext.xml
├── wizard/
│   ├── __init__.py
│   ├── sale_make_invoce_advance_ext.py
│   ├── purchase_bulk_data_wziard.py   # Bulk date update wizard
│   ├── purchase_bulk_data_wizard.xml
│   └── mass_cancel_orders_views_extend.xml
├── security/
│   ├── ir.model.access.csv
│   └── quote_type_customization_security.xml
└── data/
    ├── sequence_data.xml              # 9 sales order series
    └── ir_action_data.xml             # Server actions
```

---

## Dependencies

```python
'depends': [
    'base',
    'web',
    'sale',
    'account',
    'purchase',
    'stock',
    'mrp',
    'bom_based_inventory',
    'sale_custom_report',
    'new_delivery_stage_feature',
    'filter_one2many_fields'
]
```

| Dependency | Purpose |
|------------|---------|
| `sale` | Core sales order functionality |
| `account` | Invoice management |
| `purchase` | Purchase order management |
| `stock` | Inventory and picking operations |
| `mrp` | Manufacturing and BOM support |
| `bom_based_inventory` | Custom BOM inventory tracking |
| `new_delivery_stage_feature` | Base delivery stage functionality |
| `filter_one2many_fields` | One2many field filtering |

---

## Security & Access Control

### User Groups

#### Planning Screen Admin
**XML ID:** `quotation_type_customization.group_planning_screen_admin`

Permissions:
- Approve/unapprove products on planning screen
- Modify HubSpot references on old data
- Duplicate project quotes
- Change sale reference and series

#### Super Admin
**XML ID:** `quotation_type_customization.group_super_admin`

Permissions:
- Delete delivery stage quotations
- Full CRUD on purchase orders
- Full CRUD on sale orders
- Cancel purchase orders

### Model Access Rules

| Model | Group | Read | Write | Create | Unlink |
|-------|-------|------|-------|--------|--------|
| `sale.order.series` | All Users | ✓ | ✓ | ✓ | ✗ |
| `purchase.bulk.date.wizard` | All Users | ✓ | ✓ | ✓ | ✓ |
| `purchase.order` | Super Admin | ✓ | ✓ | ✓ | ✓ |
| `sale.order` | Super Admin | ✓ | ✓ | ✓ | ✓ |

---

## Models Reference

### SaleOrderExt

**File:** `models/sale_order_ext.py`
**Inherits:** `sale.order`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `quote_type` | Selection | Quote classification: `sales_quote`, `project_quote`, `delivery_stage` |
| `series_sequence_id` | Many2one | Link to `sale.order.series` for reference generation |
| `new_sale_order_number` | Char | Auto-generated sale order number from series |
| `series_from_hubspot_ref` | Char | First 6 characters of HubSpot reference |
| `user_is_planning_admin` | Boolean (computed) | True if user has Planning Admin group |
| `x_invoice_ids` | Many2many | Direct links to `account.move` records |
| `down_payment_order_line_ids` | One2many (computed) | Order lines filtered for down payments |

#### Key Methods

##### `action_generate_sale_order_number()`
Generates a unique reference number from the selected series.

```python
def action_generate_sale_order_number(self):
    """
    Generates sale order reference from series sequence.

    Behavior:
    - Validates series is selected
    - Checks for duplicate references (first 6 digits)
    - Increments series starting_value
    - Sets burgtec_quote_reference

    Raises:
        UserError: If series not selected or exhausted
        UserError: If duplicate reference exists
    """
```

##### `change_sale_ref_and_series()`
Modifies the sale reference and series (Planning Admin only).

```python
def change_sale_ref_and_series(self):
    """
    Updates reference and series based on HubSpot reference.

    Requirements:
    - User must be Planning Screen Admin
    - hubspot_reference must be set
    - First character must be digit 1-9

    Actions:
    - Updates burgtec_quote_reference
    - Sets series_sequence_id from first digit
    """
```

##### `create_new_delivery_stage()`
Creates a Project Quote from a Sales Quote.

```python
def create_new_delivery_stage(self):
    """
    Creates child sale order with quote_type='project_quote'.

    Validations:
    - Only one project quote per sales quote allowed
    - Sets parent-child relationship

    Returns:
        Action to open newly created project quote
    """
```

##### `unlink()`
Override with cascade deletion logic.

```python
def unlink(self):
    """
    Custom deletion with cascade handling.

    Behavior:
    - Prevents non-Super Admin deletion of delivery stages
    - Cancels and deletes related purchase orders
    - Deletes child quotes
    - Updates parent planning screen status to 'draft'

    Raises:
        UserError: If non-admin attempts delivery stage deletion
    """
```

##### `_prepare_invoice()`
Override to generate custom invoice reference.

```python
def _prepare_invoice(self):
    """
    Generates burgtec_invoice_reference.

    Format: INV-{quote_ref[:6]}-{count:02d}
    Example: INV-123456-01, INV-123456-02
    """
```

---

### SaleOrderLineExt

**File:** `models/sale_order_ext.py`
**Inherits:** `sale.order.line`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `product_uom` | Many2one | Unit of measure (readonly) |
| `is_product_fully_approved` | Boolean | Read-only when approved on Planning Screen |
| `origin_planning_screen_line` | Char | Reference to source planning screen line |

#### Key Methods

##### `create()`
Override to auto-create planning screen lines.

```python
@api.model_create_multi
def create(self, vals_list):
    """
    Auto-creates planning_screen_line records for new sale lines.

    Behavior:
    - Creates corresponding planning screen line
    - Handles is_old_data flag
    - Supports split_do_id integration
    """
```

##### `unlink()`
Override to prevent deletion of approved products.

```python
def unlink(self):
    """
    Raises:
        UserError: If product is fully approved
    """
```

---

### SaleOrderSeries

**File:** `models/sale_order_series.py`
**Model:** `sale.order.series`

Manages number series for sale order reference generation.

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `sequence` | Integer | Series number (1-9) |
| `starting_value` | Integer | Current/next available number |
| `ending_value` | Integer | Maximum number in range |

#### Default Series Configuration

| Series | Start | End | Capacity |
|--------|-------|-----|----------|
| 1 | 100,000 | 199,999 | 100,000 |
| 2 | 205,000 | 299,999 | 95,000 |
| 3 | 300,000 | 399,999 | 100,000 |
| 4 | 407,000 | 499,999 | 93,000 |
| 5 | 501,000 | 599,999 | 99,000 |
| 6 | 602,400 | 699,999 | 97,600 |
| 7 | 700,500 | 799,999 | 99,500 |
| 8 | 800,400 | 899,999 | 99,600 |
| 9 | 900,100 | 999,999 | 99,900 |

**Total Capacity:** ~883,600 unique references

---

### PlanningScreenExt

**File:** `models/planning_screen_ext.py`
**Inherits:** `planning.screen`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `do_1_status` to `do_50_status` | Selection | Status per delivery stage: `draft`, `planned`, `confirmed` |
| `stage_count` | Integer | Number of active delivery stages |
| `item` | Integer | Item sequence number |
| `lead_time` | Text | Product lead time information |
| `requested_delivery_date` | Date | Customer requested delivery date |
| `approval_required_by` | Date | Approval deadline |
| `approval_method` | Selection | `shop_drawing`, `approved_quote`, `spec_sheet` |
| `approval_status` | Selection | `awaiting_approval`, `awaiting_revision`, `approved_with_comment`, `fully_approved_by_customer` |
| `approval_comments` | Text | Approval notes |
| `do_stage_1` to `do_stage_50` | Integer | Quantity per delivery stage |
| `is_fully_approved` | Boolean | Full approval status |

#### Key Methods

##### `_create_single_delivery_stage(stage_number)`
Creates a delivery stage sale order.

```python
def _create_single_delivery_stage(self, stage_number):
    """
    Creates delivery stage when status changes to 'planned'.

    Validations:
    - All products must have vendors
    - All vendors must be the same

    Actions:
    - Creates organized order lines with group/code hierarchy
    - Creates BOM components with proportional quantities
    - Calculates live_unit_cost from child components

    Args:
        stage_number: Integer (1-50)

    Raises:
        ValidationError: If vendor requirements not met
    """
```

##### `action_handle_do_stage(selectedValue, fieldName)`
Handles delivery stage status changes.

```python
def action_handle_do_stage(self, selectedValue, fieldName):
    """
    Processes delivery stage status updates.

    Args:
        selectedValue: New status value
        fieldName: Field name (do_1_status to do_50_status)

    Triggers:
        _create_single_delivery_stage() when status='planned'
    """
```

##### `action_split_delivery_excel_report()`
Exports planning data to Excel.

```python
def action_split_delivery_excel_report(self):
    """
    Generates XLSX report with:
    - Product information
    - Delivery stage allocations
    - Lead times and dates

    Returns:
        Action to download Excel file
    """
```

##### `fetch_do_stages()`
Returns delivery stage status data for UI.

```python
def fetch_do_stages(self):
    """
    Returns:
        dict: Status data with disabled flags for planned/confirmed stages
    """
```

---

### PlanningScreenLineExt

**File:** `models/planning_screen_ext.py`
**Inherits:** `planning.screen.line`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `line_group_name` | Char (related) | From order_line |
| `line_section_name` | Char (related) | From order_line |
| `code` | Char (related) | From order_line.line_section_name |
| `is_fully_approved` | Boolean | Product approval status |
| `do_stage_1` to `do_stage_50` | Integer | Quantity allocations |
| `available_quantity` | Integer (computed) | Remaining unallocated quantity |
| `total_available_quantity` | Integer (computed) | Total available |

#### Key Methods

##### `onchange_is_fully_approved()`
Handles approval status changes.

```python
@api.onchange('is_fully_approved')
def onchange_is_fully_approved(self):
    """
    Security: Only Planning Admin can modify.

    Actions:
    - Updates sale order line is_product_fully_approved
    - Updates BOM component lines approval status

    Raises:
        UserError: If non-admin attempts modification
    """
```

---

### PurchaseOrderExt

**File:** `models/purchase_order_ext.py`
**Inherits:** `purchase.order`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `sale_quote_reference` | Char | Reference to parent sales order |
| `parent_po_id` | Many2one (computed) | Parent purchase order |
| `child_purchase_order_ids` | Many2many (computed) | Child purchase orders |
| `child_pos_count` | Integer (computed) | Number of child POs |
| `parent_po_count` | Integer (computed) | Parent PO count (0 or 1) |
| `burgtec_purchase_reference` | Char (computed) | Custom PO reference |

#### Reference Format

| PO Type | Format | Example |
|---------|--------|---------|
| Parent | `PO-{sale_quote_reference}` | PO-123456 |
| Child | `PO-{sale_quote_reference}-{count:02d}` | PO-123456-01 |

#### Key Methods

##### `action_open_bulk_date_wizard()`
Opens wizard for bulk date updates.

```python
def action_open_bulk_date_wizard(self):
    """
    Returns:
        Action to open purchase.bulk.date.wizard
        with selected POs pre-loaded
    """
```

---

### AccountMoveExt

**File:** `models/account_move_ext.py`
**Inherits:** `account.move`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `burgtec_invoice_reference` | Char | Custom invoice reference |
| `x_sale_order_ids` | Many2many | Direct links to sale orders |
| `sale_order_count` | Integer (computed) | Number of linked sale orders |

#### Reference Format

```
INV-{quote_ref[:6]}-{sequential:02d}
Example: INV-123456-01, INV-123456-02
```

---

### StockRuleExt

**File:** `models/stock_rule_ext.py`
**Inherits:** `stock.rule`

#### `_make_purchase_order()` Override

Complex logic for handling parent/child PO creation:

```python
def _make_purchase_order(self, purchase_orders):
    """
    Three processing modes:

    1. Child PO Creation (when sale has BOM):
       - Validates single vendor
       - Groups component lines by supplier
       - Calculates proportional quantities and costs
       - Creates child POs per vendor

    2. Parent PO Creation (new data flow):
       - Uses sale.order_line directly
       - Creates single PO with all products

    3. Old Data with split_do_id:
       - Creates separate POs per delivery stage
       - Groups products by stage quantities
    """
```

---

### BOM Component Extensions

**File:** `models/sale_order_bom_component_ext.py`

#### sale.order.bom.component

| Field | Type | Description |
|-------|------|-------------|
| `quote_type` | Selection (related, stored) | From order_id.quote_type |
| `is_old_data` | Boolean (related, stored) | From order_id.is_old_data |

#### sale.order.bom.component.line

| Field | Type | Description |
|-------|------|-------------|
| `is_product_fully_approved` | Boolean | Approval status |

**Behavior:** Methods return `None` for delivery_stage quotes to disable editing.

---

## Wizards

### PurchaseBulkDateWizard

**File:** `wizard/purchase_bulk_data_wziard.py`
**Model:** `purchase.bulk.date.wizard` (TransientModel)

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `planned_date` | Datetime | Expected arrival date (required) |
| `purchase_order_ids` | Many2many | POs to update |

#### Usage

```python
# From PO list view action
wizard = self.env['purchase.bulk.date.wizard'].create({
    'planned_date': fields.Datetime.now(),
    'purchase_order_ids': [(6, 0, po_ids)]
})
wizard.action_assign_date()
```

---

## Views & UI Components

### Sale Order Form View

**Key Conditional Elements:**

```xml
<!-- HubSpot Reference (Old Data + Sales Quote only) -->
<div invisible="not(is_old_data) or quote_type != 'sales_quote'">
    <field name="hubspot_reference" readonly="not user_is_planning_admin"/>
    <button name="change_sale_ref_and_series"/>
</div>

<!-- Series Selection (hidden after reference generated) -->
<field name="series_sequence_id"
       readonly="burgtec_quote_reference"
       options="{'no_open':True,'no_create':True}"/>

<!-- Generate Button (hidden after reference exists) -->
<button name="action_generate_sale_order_number"
        invisible="burgtec_quote_reference"
        confirm="Are you sure"/>
```

### Quote Type-Specific Status Bars

```xml
<!-- Sales Quote: draft → sent -->
<field name="state" widget="statusbar"
       statusbar_visible="draft,sent"
       invisible="quote_type != 'sales_quote'"/>

<!-- Delivery Stage: sale only -->
<field name="state" widget="statusbar"
       statusbar_visible="sale"
       invisible="quote_type != 'delivery_stage'"/>
```

### Planning Screen View

- 50 delivery stage status fields
- 50 delivery stage quantity fields per line
- Product approval workflow
- Excel export button

### Purchase Order View

- Parent/Child PO navigation buttons
- Custom reference display
- Cancel button restricted to Super Admin

---

## Business Workflows

### 1. Sales Quote to Project Quote

```
┌─────────────────┐
│  Sales Quote    │
│  (draft/sent)   │
└────────┬────────┘
         │ create_new_delivery_stage()
         ▼
┌─────────────────┐
│  Project Quote  │
│  (quotation_    │
│   confirmed)    │
└─────────────────┘
```

### 2. Project Quote to Delivery Stages

```
┌─────────────────┐
│  Project Quote  │
│  with Planning  │
│  Screen         │
└────────┬────────┘
         │ _create_single_delivery_stage()
         │ (triggered by status='planned')
         ▼
┌─────────────────┐
│  Delivery Stage │
│  1, 2, 3...50   │
│  (draft → sale) │
└─────────────────┘
```

### 3. Purchase Order Creation Flow

```
┌─────────────────┐
│  Delivery Stage │
│  Confirmed      │
└────────┬────────┘
         │ Stock rules trigger
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Parent PO      │────▶│  Child PO(s)    │
│  (all products) │     │  (per vendor)   │
└─────────────────┘     └─────────────────┘
```

### 4. Product Approval Flow

```
┌─────────────────┐
│  Planning Line  │
│  (unapproved)   │
└────────┬────────┘
         │ Planning Admin sets
         │ is_fully_approved = True
         ▼
┌─────────────────┐
│  Line Locked    │
│  - No deletion  │
│  - No editing   │
│  - Stage ready  │
└─────────────────┘
```

---

## Data Initialization

### Sales Order Series (`data/sequence_data.xml`)

```xml
<record id="sale_order_series_1" model="sale.order.series">
    <field name="sequence">1</field>
    <field name="starting_value">100000</field>
    <field name="ending_value">199999</field>
</record>
<!-- Series 2-9 follow similar pattern -->
```

### Server Actions (`data/ir_action_data.xml`)

```xml
<record id="action_purchase_bulk_set_date" model="ir.actions.server">
    <field name="name">Set Expected Arrival on Bulk Purchase Orders</field>
    <field name="model_id" ref="purchase.model_purchase_order"/>
    <field name="binding_model_id" ref="purchase.model_purchase_order"/>
    <field name="binding_view_types">list</field>
    <field name="state">code</field>
    <field name="code">records.action_open_bulk_date_wizard()</field>
</record>
```

---

## API Reference

### Sale Order Methods

```python
# Generate reference number
sale_order.action_generate_sale_order_number()

# Create project quote from sales quote
sale_order.create_new_delivery_stage()

# Modify reference (Planning Admin only)
sale_order.change_sale_ref_and_series()

# Set series from HubSpot reference
sale_order.action_set_the_sequence_as_hubspot_initial()
```

### Planning Screen Methods

```python
# Create delivery stage
planning_screen._create_single_delivery_stage(stage_number)

# Handle status change
planning_screen.action_handle_do_stage(selectedValue, fieldName)

# Export to Excel
planning_screen.action_split_delivery_excel_report()

# Get stage data for UI
planning_screen.fetch_do_stages()
```

### Purchase Order Methods

```python
# Open bulk date wizard
purchase_orders.action_open_bulk_date_wizard()

# Navigation actions
purchase_order.action_show_parent_purchase_order()
purchase_order.action_show_child_purchase_orders()
```

---

## Extension Points

### Adding New Quote Types

1. Extend the `quote_type` selection field:
```python
quote_type = fields.Selection(
    selection_add=[('custom_type', 'Custom Type')]
)
```

2. Add conditional logic in views and methods.

### Adding Delivery Stages Beyond 50

1. Add new `do_XX_status` and `do_stage_XX` fields
2. Update `stage_count` constraints
3. Extend `fetch_do_stages()` method
4. Update XML views

### Custom Approval Workflows

Override `onchange_is_fully_approved()` in `planning.screen.line`:
```python
@api.onchange('is_fully_approved')
def onchange_is_fully_approved(self):
    super().onchange_is_fully_approved()
    # Add custom logic
```

### Custom PO Reference Format

Override `_compute_po_ref()` in `purchase.order`:
```python
def _compute_po_ref(self):
    for record in self:
        # Custom reference logic
        record.burgtec_purchase_reference = f"CUSTOM-{record.name}"
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Cannot generate reference | Series exhausted | Check `sale.order.series` starting/ending values |
| Cannot delete delivery stage | Not Super Admin | Assign user to `group_super_admin` |
| Cannot approve product | Not Planning Admin | Assign user to `group_planning_screen_admin` |
| Delivery stage creation fails | Multiple vendors | Ensure all products have same vendor |
| Missing planning screen lines | Auto-creation failed | Check `sale.order.line.create()` override |

### Debug Logging

Add to `odoo.conf`:
```ini
log_handler = :INFO,odoo.addons.quotation_type_customization:DEBUG
```

---

## Changelog

### Version 18.0.1.0.0
- Initial release for Odoo 18
- Three quote types: Sales Quote, Project Quote, Delivery Stage
- 9 number series with configurable ranges
- 50 delivery stage slots per planning screen
- Product approval workflow
- Parent-child purchase order structure
- Custom invoice references
- Excel export functionality
- HubSpot reference integration

---

## Authors & Maintainers

**Category:** Customizations
**License:** LGPL-3

For support and contributions, contact the module maintainers.