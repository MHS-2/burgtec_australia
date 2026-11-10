# New Delivery Stage Feature - Developer Documentation

## Overview

This Odoo 18 module extends the Sale Order functionality to create a hierarchical relationship between Sale Quotes (parent) and Project Quotes (child). It enables the creation of "Delivery Stages" from a parent Sale Quote, facilitating phased delivery management.

---

## Table of Contents

1. [Overview](#overview)
2. [Module Information](#module-information)
3. [Architecture](#architecture)
   - [Module Structure](#module-structure)
4. [Models](#models)
   - [SaleOrderExt (sale.order)](#1-saleorderext-saleorder)
   - [SaleOrderLineExt (sale.order.line)](#2-saleorderlineext-saleorderline)
   - [PlanningScreen (planning.screen)](#3-planningscreen-planningscreen)
   - [PlanningScreenLine (planning.screen.line)](#4-planningscreenline-planningscreenline)
5. [JavaScript Controllers](#javascript-controllers)
   - [SaleOrderFormController](#1-saleorderformcontroller)
   - [FormController Patch](#2-formcontroller-patch)
   - [ListController Patch](#3-listcontroller-patch)
6. [Views](#views)
   - [Sale Order Form Inheritance](#sale-order-form-inheritance)
   - [Planning Screen View](#planning-screen-view)
7. [Data](#data)
   - [Sequence Configuration](#sequence-configuration)
8. [Security](#security)
9. [Quote Type Workflow](#quote-type-workflow)
10. [Business Rules](#business-rules)
11. [Context Flags](#context-flags)
12. [Dependencies](#dependencies)
13. [Customization Points](#customization-points)
    - [Adding New Quote Types](#adding-new-quote-types)
    - [Modifying Duplicate Behavior](#modifying-duplicate-behavior)
    - [Planning Screen Customization](#planning-screen-customization)
14. [Troubleshooting](#troubleshooting)
    - [Common Issues](#common-issues)
    - [Debug Logging](#debug-logging)

---

## Module Information

| Property | Value |
|----------|-------|
| **Technical Name** | `new_delivery_stage_feature` |
| **Version** | 0.1 |
| **Category** | Customizations |
| **License** | LGPL-3 |
| **Dependencies** | `sale_custom_report`, `bom_based_inventory` |

---

## Architecture

### Module Structure

```
new_delivery_stage_feature/
├── __init__.py
├── __manifest__.py
├── data/
│   └── ir_sequence_data.xml
├── models/
│   ├── __init__.py
│   ├── sale_order_ext.py
│   └── planning_screen.py
├── security/
│   └── ir.model.access.csv
├── static/
│   └── src/
│       ├── js/
│       │   ├── patch_form_controller.js
│       │   └── patch_list_controller.js
│       └── views/
│           └── sale_order_form/
│               └── sale_order_form_controller.js
└── views/
    ├── planning_screen_view.xml
    └── sale_order_form_view_inherit.xml
```

---

## Models

### 1. SaleOrderExt (`sale.order`)

Extends the standard Sale Order model with delivery stage functionality.

#### New Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `planning_screen_id` | Many2one | Link to Planning Screen |
| `quote_type` | Selection | Type of quote: `sales_quote`, `project_quote`, `delivery_stage` |
| `delivery_stage_reference_number` | Char | Auto-generated reference (e.g., D1, D2) |
| `is_sales_quote` | Boolean | Indicates if record is a Sales Quote |
| `is_parent_sale_order` | Boolean | Indicates if record is a parent |
| `is_project_quote` | Boolean | Indicates if record is a Project Quote |
| `is_child_sale_order` | Boolean | Indicates if record is a child |
| `source_sale_order_name` | Char | Name of parent Sale Order |
| `source_sale_order_id` | Char | ID of parent Sale Order |
| `child_sale_order_ids` | Many2many | Related child Sale Orders |
| `reference_count` | Integer | Counter for delivery stages |
| `reference_count1` | Integer | Display counter (defaults to 1) |
| `child_quote_count` | Integer | Computed count of child quotes |

#### Key Methods

##### `create_new_delivery_stage()`
Creates a new Project Quote (child) from a Sales Quote (parent).

**Flow:**
1. Validates quote type (cannot create from `project_quote`)
2. Validates BOM components exist
3. Updates parent quote:
   - Sets `is_sales_quote = True`
   - Sets `is_parent_sale_order = True`
   - Sets `quote_type = 'sales_quote'`
   - Increments `reference_count`
   - Sets state to `quotation_confirmed`
4. Creates child quote via `copy()` with context `copied_from_new_delivery_stage=True`
5. Links child to parent via `child_sale_order_ids`

**Returns:** Child Sale Order ID

##### `action_confirm()`
Overrides standard confirmation with validation:
- Blocks confirmation for parent Sale Quotes
- Blocks confirmation for `sales_quote` type

##### `action_show_child_sale_orders()`
Returns action to display child quotations (single form or list view).

##### `action_show_parent_sale_order()`
Returns action to navigate to parent Sale Order.

##### `action_show_planning_screen()`
Opens the Planning Screen form view.

---

### 2. SaleOrderLineExt (`sale.order.line`)

Extends Sale Order Line with quantity tracking.

#### New Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `total_available_quantity` | Float | Computed unscheduled quantity |

#### Key Methods

##### `_compute_total_available_qty()`
Computes remaining quantity for child order lines by:
1. Getting original quantity from parent line (`old_order_line`)
2. Summing quantities from confirmed delivery stages
3. Calculating difference (available quantity)

---

### 3. PlanningScreen (`planning.screen`)

New model for planning delivery stages.

#### Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `order_id` | Many2one | Required link to Sale Order |
| `line_ids` | One2many | Planning screen lines |
| `state` | Selection | Related to order state |

---

### 4. PlanningScreenLine (`planning.screen.line`)

Line items for the Planning Screen.

#### Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `planning_screen_id` | Many2one | Parent planning screen |
| `is_child_sale_order` | Boolean | Related from order |
| `total_available_quantity` | Integer | Computed unscheduled qty |
| `product_reference` | Char | Product reference |
| `product_id` | Many2one | Link to product template |
| `available_quantity` | Float | Related from order line |
| `display_type` | Selection | `line_section`, `line_note`, `line_group` |
| `name` | Char | Computed product name |
| `order_line_id` | Many2one | Link to sale order line |
| `origin_order_line` | Char | Origin line reference |
| `sequence` | Integer | Related sequence |
| `quantity` | Float | Related quantity |

---

## JavaScript Controllers

### 1. SaleOrderFormController

**Location:** `static/src/views/sale_order_form/sale_order_form_controller.js`

Custom form controller registered as `new_delivery_stage_form`.

#### Features:
- Adds "Generate Project" action menu item
- Conditionally hides based on `quote_type`
- Calls `create_new_delivery_stage()` ORM method
- Navigates to newly created child quotation

#### Key Methods:

```javascript
// Check if "Generate Project" should be hidden
_shouldHideGenerateProject()
// Returns true for quote_type: 'delivery_stage' or 'project_quote'

// Creates delivery stage via ORM call
async createDeliveryQuotation()

// Navigates to child sale order
viewChildSaleOrder(res_id)
```

### 2. FormController Patch

**Location:** `static/src/js/patch_form_controller.js`

Patches standard `FormController` to control duplicate action visibility.

**Logic:**
- Hides duplicate for `delivery_stage` and `project_quote` types (unless `is_old_data` is true)
- Allows duplicate for old migrated data

### 3. ListController Patch

**Location:** `static/src/js/patch_list_controller.js`

Patches `ListController` to customize action menu:
- Changes "Duplicate" label to "Duplicate Sale Quote" for sale orders

---

## Views

### Sale Order Form Inheritance

**File:** `views/sale_order_form_view_inherit.xml`

#### Modifications:

1. **Custom JS Class:**
   ```xml
   <attribute name="js_class">new_delivery_stage_form</attribute>
   ```

2. **Stat Buttons:**
   - "Project Quotes" button (visible for parent orders)
   - "Parent Quote" button (visible for child orders)

3. **Planning Screen Button:**
   - Visible only for `project_quote` type
   - Hidden if `is_having_delivery_stage` is true

4. **Order Line Fields:**
   - Adds `total_available_quantity` field (visible when > 0)

### Planning Screen View

**File:** `views/planning_screen_view.xml`

Form view with section/group support using `section_and_note_one2many` widget.

---

## Data

### Sequence Configuration

**File:** `data/ir_sequence_data.xml`

| Property | Value |
|----------|-------|
| Name | Sale Order Delivery Stage |
| Code | `sale.order.delivery.stage` |
| Prefix | DO |
| Padding | 5 |

Generates: DO00001, DO00002, etc.

---

## Security

**File:** `security/ir.model.access.csv`

| Model | Read | Write | Create | Delete |
|-------|------|-------|--------|--------|
| planning.screen | Yes | Yes | Yes | Yes |
| planning.screen.line | Yes | Yes | Yes | Yes |

**Note:** No group restrictions - all users have full access.

---

## Quote Type Workflow

```
┌─────────────────┐
│  Sale Quote     │ (Normal SO)
│  quote_type=nil │
└────────┬────────┘
         │ create_new_delivery_stage()
         ▼
┌─────────────────┐    Creates    ┌─────────────────┐
│  Sales Quote    │──────────────>│ Project Quote   │
│  (Parent)       │               │ (Child)         │
│  quote_type=    │               │ quote_type=     │
│  'sales_quote'  │               │ 'project_quote' │
│  is_parent=True │               │ is_child=True   │
└─────────────────┘               └─────────────────┘
```

---

## Business Rules

1. **Parent Sale Quotes cannot be confirmed** - They serve only as templates for delivery stages

2. **Sales Quote type cannot be confirmed** - Must use child Project Quotes

3. **Project Quotes cannot create delivery stages** - Only Sales Quotes can

4. **BOM Components required** - Must be set before creating delivery stages

5. **Duplicate restrictions:**
   - Cannot duplicate `project_quote` (unless old data)
   - Cannot duplicate `delivery_stage`

6. **Quantity tracking:**
   - Parent line quantity tracked across all child delivery stages
   - `total_available_quantity` shows remaining unscheduled quantity

---

## Context Flags

| Flag | Purpose |
|------|---------|
| `copied_from_new_delivery_stage` | Indicates copy operation from delivery stage creation |
| `child_sale_order` | Passed to delivery order action for context awareness |

---

## Dependencies

This module requires:
- `sale_custom_report` - Provides `quote_type` field and custom report features
- `bom_based_inventory` - Provides `bom_component_id` field and BOM functionality

---

## Customization Points

### Adding New Quote Types

1. Extend the `quote_type` selection in `sale_order_ext.py`
2. Update `_shouldHideGenerateProject()` in JS if needed
3. Add visibility conditions in XML views

### Modifying Duplicate Behavior

Edit `patch_form_controller.js` to adjust the `isAvailable` logic for the duplicate action.

### Planning Screen Customization

Modify `planning_screen.py` and `planning_screen_view.xml` to add/remove fields from the planning interface.

---

## Troubleshooting

### Common Issues

1. **"Generate Project" not appearing**
   - Check `quote_type` is not `delivery_stage` or `project_quote`
   - Verify JS assets are loaded (check browser console)

2. **Cannot confirm Sale Order**
   - Check if it's a parent quote (`is_parent_sale_order`)
   - Verify `quote_type` is not `sales_quote`

3. **Duplicate action hidden**
   - Check `quote_type` and `is_old_data` fields
   - Review console logs for debugging output

### Debug Logging

JavaScript controllers include `console.log` statements for debugging:
- `'Setup;'` - Controller initialization
- `'Execuated!!!!'` - Form controller menu items
- `'Arrow Execuated!!!!'` - Duplicate availability check
- Quote type values logged during checks