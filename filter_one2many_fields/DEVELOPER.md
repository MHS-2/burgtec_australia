# Filter One2Many Fields - Developer Documentation

## Module Overview

| Property | Value |
|----------|-------|
| **Technical Name** | `filter_one2many_fields` |
| **Version** | 0.1 |
| **Category** | Uncategorized |
| **License** | LGPL-3 |
| **Dependencies** | `sale_custom_report`, `sale_order_customisation` |

### Purpose

This module provides dynamic filtering capabilities for One2Many fields on sale orders and BOM components. It allows users to filter order lines and BOM component lines by selecting a specific Group (section), showing only the lines that belong to that group. Additionally, it handles complex margin and markup calculations for cost tracking across multiple cost types.

---

## Directory Structure

```
filter_one2many_fields/
├── __init__.py
├── __manifest__.py
├── DEVELOPER.md
├── models/
│   ├── __init__.py
│   ├── sale_order_ext.py
│   └── sale_order_bom_component_ext.py
├── security/
│   └── ir.model.access.csv
└── views/
    ├── sale_order_extended_view.xml
    └── sale_order_bom_component_ext_view.xml
```

---

## Models

### 1. Sale Order Extension (`sale.order`)

**File:** `models/sale_order_ext.py`

Extends the sale order to add group-based filtering and comprehensive cost calculations.

#### New Fields

| Field | Type | Description |
|-------|------|-------------|
| `group_sale_order_line_id` | Many2one | Selected group (section) line for filtering |
| `group_id_value` | Char | Computed string ID of selected group |
| `filtered_order_line_ids` | One2many | Dynamically filtered order lines |

#### Key Methods

##### `_compute_group_domain()`

Generates a domain filter for the filtered One2many field based on the selected group.

```python
@api.depends('group_sale_order_line_id')
def _compute_group_domain(self):
    for record in self:
        if record.group_sale_order_line_id:
            return [
                '|',
                ('line_group_id_value', '=', record.group_id_value),
                ('id', '=', record.group_sale_order_line_id.id)
            ]
        else:
            return []
```

**Logic:** Returns lines where `line_group_id_value` matches the selected group, OR the line is the group header itself.

##### `_compute_group_id_value()`

Converts the Many2one ID to a string for domain comparison.

```python
@api.depends('group_sale_order_line_id')
def _compute_group_id_value(self):
    for record in self:
        if record.group_sale_order_line_id:
            record.group_id_value = str(record.group_sale_order_line_id.id)
        else:
            record.group_id_value = False
```

##### `_compute_multi_cost_per_unit()`

Comprehensive cost calculation method triggered on order line changes.

**Triggers:** `@api.onchange('order_line', 'filtered_order_line_ids')`

**Functionality:**

1. **With BOM Component (`bom_component_id` exists):**
   - Syncs parent line quantities and prices from order lines
   - Calculates totals from component lines:
     - `live_cost_bom_total`
     - `system_cost_bom_total`
     - `pre_project_cost_bom_total`
     - `quoted_cost_bom_total`
   - Computes margin percentages:
     - `percentage_margin_system_cost`
     - `percentage_margin_live_cost`
     - `percentage_margin_quoted_cost`
     - `percentage_margin_pre_project_cost`
   - Computes markup percentages:
     - `percentage_markup_system_cost`
     - `percentage_markup_live_cost`
     - `percentage_markup_quoted_cost`
     - `percentage_markup_pre_project_cost`
   - Calculates profit amounts:
     - `system_cost_per_unit`
     - `live_unit_cost`
     - `quoted_cost_per_unit`
     - `pre_project_cost_per_unit`

2. **Without BOM Component (uses MRP BOM):**
   - Fetches BOM via `mrp.bom._bom_find()`
   - Calculates costs from BOM line standard prices
   - Sets system/live costs based on BOM totals
   - Zeros out quoted/pre-project costs

**Formulas:**

```python
# Margin %
margin = (sale_price - cost) / sale_price

# Markup %
markup = (sale_price - cost) / cost

# Profit
profit = amount_untaxed - total_cost
```

---

### 2. Sale Order BOM Component Extension (`sale.order.bom.component`)

**File:** `models/sale_order_bom_component_ext.py`

Extends BOM component model for group-based filtering.

#### New Fields

| Field | Type | Description |
|-------|------|-------------|
| `group_sale_order_line_id` | Many2one | Computed from parent sale order |
| `group_id_value` | Char | Computed string ID of selected group |
| `filtered_component_line_ids` | One2many | Dynamically filtered component lines |

#### Key Methods

##### `_compute_group_sale_order_line_id()`

Syncs the group selection from the parent sale order.

```python
@api.depends('order_id.group_sale_order_line_id')
def _compute_group_sale_order_line_id(self):
    for record in self:
        if record.order_id and record.order_id.group_sale_order_line_id:
            record.group_sale_order_line_id = record.order_id.group_sale_order_line_id.id
        else:
            record.group_sale_order_line_id = False
```

##### `_compute_group_domain()`

Generates domain filter for filtered component lines.

```python
@api.depends('group_sale_order_line_id')
def _compute_group_domain(self):
    for record in self:
        if record.group_sale_order_line_id:
            return [('line_group_id_value', '=', record.group_id_value)]
        else:
            return []
```

##### `onchange_component_line_ids()`

Complex method handling sequence management and cost aggregation.

**Triggers:** `@api.onchange('component_line_ids', 'filtered_component_line_ids')`

**Functionality:**

1. **Sequence Management:**
   - Iterates through lines sorted by sequence
   - Maintains section hierarchy
   - Assigns sequences and parent product references

2. **Parent Line Cost Aggregation:**
   - Sums child line costs to parent:
     - `pre_project_cost_per_unit`
     - `system_cost_per_unit`
     - `quoted_cost_per_unit`
     - `live_unit_cost`
   - Calculates `manual_live_unit_cost` as `live_unit_cost / product_qty`

3. **Proportion Factor Updates:**
   - Calculates proportion based on child/parent quantity ratio
   - Batches updates using `_batch_update_state()`

---

### 3. Sale Order BOM Component Line Extension (`sale.order.bom.component.line`)

**File:** `models/sale_order_bom_component_ext.py`

Extends component lines with group reference fields.

#### New Fields

| Field | Type | Description |
|-------|------|-------------|
| `line_group_id_value` | Char | Related from `order_line_id.line_group_id_value` |
| `line_section_id_value` | Char | Related from `order_line_id.line_section_id_value` |

These related fields enable domain filtering on component lines based on their parent order line's group membership.

---

## Views

### Sale Order Form Extension

**File:** `views/sale_order_extended_view.xml`

**View ID:** `filter_one2many_field_original_sale_order_form_view`

#### New Tab: "Filter Order Lines"

Adds a new tab after "Order Lines" with:

1. **Group Selector:**
   ```xml
   <field name="group_sale_order_line_id"
          domain="[('order_id','=',id), ('display_type','=','line_section')]"
          options="{'no_open':1,'no_create':1}"/>
   ```
   - Filters to show only section (Group) lines
   - Context: `{'group_swap':1}`

2. **Filtered Order Lines:**
   ```xml
   <field name="filtered_order_line_ids"
          widget="sol_o2m"
          mode="list,kanban"
          readonly="state == 'cancel' or locked"
          invisible="not group_sale_order_line_id"/>
   ```
   - Only visible when a group is selected
   - Includes full list and kanban views
   - Create functionality disabled (`create="0"`)

#### List View Features

- Row decorations:
  - `decoration-danger` for sections
  - `decoration-info` for notes
- Copy wizard button per line
- All standard sale order line fields
- Custom product name field

---

### BOM Component Form Extension

**File:** `views/sale_order_bom_component_ext_view.xml`

**View ID:** `filter_one2many_field_original_bom_components_form_view`

Completely replaces the sheet content with a notebook structure.

#### Tab 1: "BOM Lines"

Displays component lines with view type toggle:

- **Default View** (`view_team` not set)
- **Sales Team View** (`view_team == 'sales_team'`)
- **Pre-Project Team View** (`view_team == 'preproject_team'`)
- **Purchasing Team View** (`view_team == 'purchasing_team'`)

Each view shows/hides different cost columns based on team needs.

#### Tab 2: "Filter BOM Lines"

Shows filtered component lines based on selected group:

1. **Warning Messages:**
   - "Select Group From Sale Order First" (if no group selected)
   - "Save The BOM Component To See Filtered Lines" (if no filtered lines)

2. **Filtered Lines Display:**
   - Same column structure as main BOM Lines
   - Additional "Product" edit button per parent line
   - Lines filtered by `line_group_id_value`

#### List View Decorations

| Condition | Decoration |
|-----------|------------|
| `is_parent == True` | `decoration-success` (green) |
| `is_other_than_bom == True` | `decoration-warning` (orange) |
| `is_parent == False` | `decoration-info` (blue) |

#### Cost Field Color Coding

| Cost Type | Decoration |
|-----------|------------|
| System Cost | `decoration-muted` (gray) |
| Quoted Cost | `decoration-danger` (red) |
| Pre-Project Cost | `decoration-primary` (blue, bold) |
| Live Cost | `decoration-warning` (orange) |

---

## Cost Types Explained

| Cost Type | Description |
|-----------|-------------|
| **System Cost** | Standard cost from product's `standard_price` |
| **Quoted Cost** | Cost quoted to customer (editable) |
| **Pre-Project Cost** | Estimated cost before project starts (editable) |
| **Live Cost** | Current/actual cost (computed from components) |
| **Manual Live Cost** | User-overridable live cost |

---

## Usage Flow

### Filtering Sale Order Lines

1. Open a Sale Order with Groups (sections) defined
2. Go to "Filter Order Lines" tab
3. Select a Group from the dropdown
4. Save the record
5. View shows only lines belonging to that group

### Filtering BOM Component Lines

1. Open a Sale Order with BOM Components
2. Select a Group in the Sale Order's "Filter Order Lines" tab
3. Save the Sale Order
4. Open BOM Components
5. Go to "Filter BOM Lines" tab
6. Lines are automatically filtered by the selected group

---

## Technical Notes

### Domain Filtering Pattern

The module uses a lambda domain on One2many fields:

```python
filtered_order_line_ids = fields.One2many(
    comodel_name='sale.order.line',
    inverse_name='order_id',
    domain=lambda self: self._compute_group_domain(),
)
```

This pattern allows dynamic domain computation based on record state.

### ID String Conversion

Group IDs are stored as strings for domain comparison:

```python
record.group_id_value = str(record.group_sale_order_line_id.id)
```

This is necessary because `line_group_id_value` on order lines is stored as a Char field.

### Sequence Management

The `onchange_component_line_ids` method maintains proper sequencing:

```python
for line in component_lines.sorted(lambda o: o.sequence):
    if line.display_type == 'line_section':
        sequence_val = line.sequence
    if line.is_parent:
        sequence_val += 1
        line.sequence = sequence_val
    if not line.display_type and not line.is_parent:
        sequence_val += 1
        line.sequence = sequence_val
```

---

## Dependencies on Other Modules

### From `sale_custom_report`

- `line_group_id_value` field on `sale.order.line`
- `line_section_id_value` field on `sale.order.line`
- `line_group_name` field on `sale.order.line`

### From `sale_order_customisation`

- `bom_component_id` field on `sale.order`
- Cost-related fields on `sale.order`:
  - `system_cost_per_unit`, `live_unit_cost`
  - `quoted_cost_per_unit`, `pre_project_cost_per_unit`
  - `percentage_margin_*`, `percentage_markup_*`
  - `*_cost_bom_total` fields

### From `bom_based_inventory`

- `sale.order.bom.component` model
- `sale.order.bom.component.line` model
- `component_line_ids` field
- Cost fields on component lines

---

## Extending the Module

### Adding New Filter Criteria

1. Add new selection field to `sale.order`
2. Create computed domain method
3. Add new One2many field with lambda domain
4. Update view to show selector and filtered field

### Adding New Cost Types

1. Add cost field to component line model
2. Update `_compute_multi_cost_per_unit()` to include new cost
3. Update `onchange_component_line_ids()` for aggregation
4. Add field to view with appropriate decoration

---

## File Reference

| File | Purpose |
|------|---------|
| `__init__.py` | Module initialization |
| `__manifest__.py` | Module metadata and dependencies |
| `models/__init__.py` | Model imports |
| `models/sale_order_ext.py` | Sale order filtering and cost calculations |
| `models/sale_order_bom_component_ext.py` | BOM component filtering and line extensions |
| `security/ir.model.access.csv` | Access control (currently commented out in manifest) |
| `views/sale_order_extended_view.xml` | Sale order form extension with filter tab |
| `views/sale_order_bom_component_ext_view.xml` | BOM component form with filter tab |