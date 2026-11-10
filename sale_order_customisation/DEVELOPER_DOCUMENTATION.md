# Sale Order Customisation Module - Developer Documentation

## Module Overview

| Property | Value |
|----------|-------|
| **Technical Name** | `sale_order_customisation` |
| **Version** | 0.1 |
| **Category** | Customizations |
| **License** | LGPL-3 |
| **Dependencies** | `sale_custom_report`, `bom_based_inventory` |

### Purpose

This module extends Odoo's Sale Order functionality to provide:

1. **Group/Section Management** - Add, swap, and organize groups (sections) on sale order lines
2. **Code Management** - Add and swap codes (notes) within groups
3. **Product Addition** - Add products directly via wizard with product configurator support
4. **Line Duplication** - Duplicate sale order lines within the same or different sale orders
5. **Sequence Control** - Prevent manual drag-and-drop reordering of lines

---

## Architecture

```
sale_order_customisation/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── sale_order_ext.py           # Sale order extensions
│   ├── sale_order_line_ext.py      # Sale order line extensions
│   ├── sale_order_bom_component_ext.py  # BOM component extensions
│   └── product_template.py         # Product template modifications
├── wizard/
│   ├── __init__.py
│   ├── sale_order_line_wizard.py   # Main wizard for adding codes/products/swapping
│   ├── sale_order_line_wizard_views.xml
│   ├── duplicate_sale_order_line_wizard.py  # Duplication wizard
│   └── duplicate_sale_order_line_wizard_view.xml
├── views/
│   └── sale_order_line_extend_view.xml
├── static/
│   └── src/
│       ├── css/
│       │   └── style.css
│       └── js/
│           ├── sale_order_line_field/
│           │   ├── sale_order_line_field.js
│           │   ├── sale_order_line_field.xml
│           │   └── sale_order_one2many_field.js
│           ├── wizard_product_field.js
│           ├── wizard_product_variant_field.js
│           ├── product_template_attributeline.js
│           └── pager/
│               └── pager.js
└── security/
    └── ir.model.access.csv
```

---

## Models

### 1. `sale.order.line` Extension

**File:** `models/sale_order_line_ext.py`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `product_identifier` | Integer (computed) | Unique identifier for groups, codes, and products |

#### Key Methods

##### `_set_unique_identifiers()`
Computes unique identifiers for each line type:
- Groups (sections): Sequential numbering starting from 1
- Codes (notes): Sequential numbering starting from 1
- Products: Sequential numbering starting from 1

```python
@api.depends('order_id')
def _set_unique_identifiers(self):
    # Separates lines by type and assigns sequential identifiers
```

##### Wizard Action Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `action_show_wizard_to_add_code()` | Opens wizard to add a code under a group | Action dict |
| `action_show_wizard_to_add_product()` | Opens wizard to add products under a code | Action dict |
| `action_show_wizard_to_swap_groups()` | Opens wizard to swap group positions | Action dict |
| `action_show_wizard_to_swap_codes()` | Opens wizard to swap code positions | Action dict |
| `action_open_copy_wizard()` | Opens the line duplication wizard | Action dict |

##### `_compute_display_name()`
Customizes display name based on context:
- `group_swap` context: Shows `{identifier} - {name}`
- `duplicate_line` context: Shows product template name or custom name

##### `_sequence_validation()`
**Important:** Prevents manual drag-and-drop reordering of group/code lines.
```python
@api.onchange('sequence')
def _sequence_validation(self):
    # Raises RedirectWarning if user tries to drag sections or notes
```

##### View ID Helper Methods
Used by JavaScript to get form view IDs:
- `get_add_code_form_view_id()`
- `get_swap_group_form_view_id()`
- `get_add_product_form_view_id()`
- `get_swap_code_form_view_id()`

---

### 2. `sale.order` Extension

**File:** `models/sale_order_ext.py`

#### Key Methods

##### `_compute_display_name()`
Shows `{name} - {burgtec_quote_reference}` when in `group_swap` context.

##### `name_search()`
Extended search that includes:
- Standard name search
- Search by `burgtec_quote_reference`
- Combined name parts search

---

### 3. `product.template` Extension

**File:** `models/product_template.py`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `product_variant_count` | Integer (computed, stored) | Count of product variants |

---

### 4. `sale.order.bom.component` Extension

**File:** `models/sale_order_bom_component_ext.py`

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `min_limit` | Integer | 1 | Minimum limit for component |
| `max_limit` | Integer | 50 | Maximum limit for component |

---

## Wizards

### 1. `sale.order.line.wizard`

**File:** `wizard/sale_order_line_wizard.py`

Main wizard for managing sale order line operations.

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `code_name` | Char | Name of the code to add |
| `type_of_addition` | Selection | 'code' or 'product' |
| `sale_order_product_line_wizard_ids` | One2many | Product lines to add |
| `sale_order_id` | Many2one | Related sale order |
| `active_group_id` | Many2one | Current group for swapping |
| `target_group_id` | Many2one | Target group for swapping |
| `active_code_id` | Many2one | Current code for swapping |
| `target_code_id` | Many2one | Target code for swapping |
| `position` | Selection | 'top', 'bottom', or 'replace' |
| `product_model_type` | Selection | 'product_template' or 'product_variant' |
| `is_main_product_added` | Boolean | Tracks if main product was added |

#### Key Methods

##### `action_add_code()`
Adds a new code (note line) under a group:
1. Gets the active group's sequence
2. Calculates new code sequence (after last line in group)
3. Shifts subsequent lines down
4. Creates new `line_note` type sale order line

##### `action_add_product()`
Adds products under a code:
1. Validates products exist in wizard lines
2. Calculates sequence after last product in code
3. Batch creates all product lines
4. Handles custom product names and sub-selections

##### `action_swap_groups()`
Swaps two groups based on position:
- **replace**: Exchanges positions of two groups with all their contents
- **top**: Moves active group above target group
- **bottom**: Moves active group below target group

Algorithm handles:
- Lines between groups
- Group contents (codes and products)
- Sequence recalculation
- BOM component updates

##### `action_swap_codes()`
Similar to `action_swap_groups()` but for codes within the same group.

---

### 2. `sale.order.product.line.wizard`

**File:** `wizard/sale_order_line_wizard.py` (same file)

Wizard line model for adding products.

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `product_id` | Many2one | Product variant (for single-variant products) |
| `product_template_id` | Many2one | Product template (for configurable products) |
| `product_uom_qty` | Float | Quantity (default: 1.0) |
| `sub_selection_json` | Text | JSON string of sub-attribute selections |
| `sub_selection_display` | Text | Human-readable sub-attribute description |
| `is_select_optional_product` | Boolean | Flags if this is an optional product |

#### Domain Logic
```python
# Product variants (single variant products only)
domain="[('sale_ok', '=', True),('product_bom_type', '!=', 'components'),('product_variant_count','=',1)]"

# Product templates (multi-variant products)
domain=[('is_old_data', '=', False),('sale_ok', '=', True),('product_bom_type', '!=', 'components'),("product_variant_count", ">", 1)]
```

---

### 3. `duplicate.quotation.line.wizard`

**File:** `wizard/duplicate_sale_order_line_wizard.py`

Wizard for duplicating sale order lines.

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | Many2one | Target sale order |
| `order_line_id` | Many2one | Line to duplicate |
| `group_id` | Many2one | Target group |
| `section_id` | Many2one | Target code |
| `quote_type` | Selection | 'sales_quote' or 'project_quote' |
| `is_admin` | Boolean | User has both sales and project admin rights |
| `is_no_admin_right` | Boolean | User has no admin rights |
| `show_warning` | Boolean | Shows warning when duplicating to different order |

#### Key Method: `action_duplicate()`
1. Validates BOM components exist on source and target orders
2. Copies sale order line data
3. Calculates sequence position under target code
4. Creates new sale order line
5. Copies and creates BOM component lines
6. Updates component lines

#### Access Control Logic
```python
# Both sales and project admin
if user.has_group('sales_team.group_sale_manager') and user.has_group('project.group_project_manager'):
    quote_type = 'sales_quote'
    is_admin = True

# Sales admin only
elif user.has_group('sales_team.group_sale_manager'):
    quote_type = 'sales_quote'

# Project admin only
elif user.has_group('project.group_project_manager'):
    quote_type = 'project_quote'

# No admin rights
else:
    is_no_admin_right = True
```

---

## JavaScript Components

### 1. ListRenderer Patch

**File:** `static/src/js/sale_order_line_field/sale_order_line_field.js`

Patches Odoo's `ListRenderer` to add custom buttons for sale order lines.

#### Setup
```javascript
setup() {
    // Detects if rendering sale.order.line inside sale.order
    const isSaleOrderLine = this.props.list?.resModel === 'sale.order.line';
    const isSaleOrder = this.props.list?._parent?.resModel === 'sale.order';

    if (isSaleOrderLine && isSaleOrder) {
        this.state.customButtons = true;
        this.bus.addEventListener("data-for-list-renderer", this.handleData.bind(this));
    }
}
```

#### Custom Button Methods
| Method | Description |
|--------|-------------|
| `addCode(record)` | Opens add code wizard for a group |
| `addProduct(record)` | Opens add product wizard for a code |
| `swapGroup(record)` | Opens swap group wizard |
| `swapCode(record)` | Opens swap code wizard |

#### Field Name Handling
Tracks which One2many field is being rendered:
- `filtered_order_line_ids`: Filtered lines view
- `down_payment_order_line_ids`: Down payment lines view
- `other`: Standard order lines

---

### 2. WizardLineProductField

**File:** `static/src/js/wizard_product_field.js`

Custom Many2one widget for product selection in wizards.

**Widget Name:** `wizard_product_many2one`

#### Features
- Extends `ProductLabelSectionAndNoteField`
- Integrates with `BurgtecProductConfiguratorDialog`
- Handles product template vs variant selection
- Stores sub-attribute selections as JSON

#### Key Method: `_openProductConfigurator()`
Opens the Burgtec product configurator with:
- Product template ID
- PTAV (Product Template Attribute Value) IDs
- Quantity and UOM
- Company and pricelist context
- Sub-attribute initial selection

```javascript
this.dialog.add(BurgtecProductConfiguratorDialog, {
    productTemplateId: line.product_template_id[0],
    ptavIds,
    quantity: line.product_uom_qty,
    use_burgtec: true,
    save: async (mainProduct, optionalProducts) => {
        await applyProductToWizardLine(this.props.record, mainProduct);
        for(const p of optionalProducts) {
            const newLine = await wizard.data.sale_order_product_line_wizard_ids.addNewRecord({...});
            await applyProductToWizardLine(newLine, p);
        }
    },
    discard: () => {
        wizard.data.sale_order_product_line_wizard_ids.delete(this.props.record);
    },
});
```

---

### 3. WizardLineProductVariantField

**File:** `static/src/js/wizard_product_variant_field.js`

Custom widget for selecting optional group products.

**Widget Name:** `wizard_product_variant_many2one`

#### Features
- Opens a custom dialog for optional group selection
- Fetches optional groups from `product.product.get_optional_groups()`
- Fetches product mapping from `product.product.get_optional_group_product_mapping()`
- Adds selected products as new wizard lines

#### ProductVariantDialog Component
Embedded OWL component with:
- Radio button selection per optional group
- Styled with gradient backgrounds
- Empty state handling
- Confirm/Cancel actions

---

### 4. List Renderer Template

**File:** `static/src/js/sale_order_line_field/sale_order_line_field.xml`

Extends `account.sectionAndNoteListRenderer` to add:
- Extra columns for custom buttons when `state.customButtons` is true
- Conditional button rendering based on line type
- Hidden buttons for filtered/down payment views

#### Button Placement
```xml
<!-- For Groups (line_section) -->
<button t-on-click="() => this.addCode(record)">+ Code</button>
<button t-on-click="() => this.swapGroup(record)">↻ Group</button>

<!-- For Codes (line_note) -->
<button t-on-click="() => this.addProduct(record)">+ Product</button>
<button t-on-click="() => this.swapCode(record)">↻ Code</button>
```

---

## Views

### Sale Order Form Extension

**File:** `views/sale_order_line_extend_view.xml`

| Modification | Description |
|--------------|-------------|
| Copy button | Adds copy button after `price_subtotal` on product lines |
| Sequence field | Adds optional sequence field after `product_id` |
| Product identifier | Adds `product_identifier` field after sequence |
| Control buttons | Replaces add controls with "Add a Group" only |

```xml
<control>
    <create name="add_section_control" string="Add a Group"
            context="{'default_display_type': 'line_section'}"/>
</control>
```

---

## Security

**File:** `security/ir.model.access.csv`

| Model | Group | Read | Write | Create | Delete |
|-------|-------|------|-------|--------|--------|
| `sale.order.line.wizard` | base.group_user | ✓ | ✓ | ✓ | ✓ |
| `sale.order.product.line.wizard` | base.group_user | ✓ | ✓ | ✓ | ✓ |
| `duplicate.quotation.line.wizard` | base.group_user | ✓ | ✓ | ✓ | ✓ |

---

## CSS Styling

**File:** `static/src/css/style.css`

Styles the product model type selection badges:

| Selector | Background | Hover |
|----------|------------|-------|
| `product_template` | #4a0a53 (purple) | #650472 |
| `product_variant` | #530e0e (red) | #970000 |

---

## Key Workflows

### 1. Adding a Code to a Group

```
User clicks "+ Code" on group row
    ↓
action_show_wizard_to_add_code() returns action
    ↓
JavaScript opens wizard dialog
    ↓
User enters code name and clicks "Add"
    ↓
action_add_code() creates line_note record
    ↓
Dialog closes, list reloads
```

### 2. Adding Products to a Code

```
User clicks "+ Product" on code row
    ↓
Wizard opens with product model type selection
    ↓
User selects "Product Template" or "Product Variant"
    ↓
For templates: Opens BurgtecProductConfiguratorDialog
For variants: Direct selection
    ↓
action_add_product() batch creates lines
    ↓
Optional: User selects from optional groups
```

### 3. Swapping Groups/Codes

```
User clicks "↻ Group" or "↻ Code"
    ↓
Wizard shows current and target selection
    ↓
User selects target and position (top/bottom/replace)
    ↓
action_swap_groups() or action_swap_codes() recalculates sequences
    ↓
BOM components updated via update_component_lines()
```

### 4. Duplicating a Line

```
User clicks copy icon on product line
    ↓
Wizard shows target order, group, and code selection
    ↓
Quote type determined by user permissions
    ↓
action_duplicate() copies line and BOM components
    ↓
Component lines updated
```

---

## Integration Points

### Dependencies on Other Modules

1. **sale_custom_report**: Provides `burgtec_quote_reference` field
2. **bom_based_inventory**: Provides `sale.order.bom.component` model
3. **burgtec_website_customization**: Provides `BurgtecProductConfiguratorDialog`

### Expected External Fields

| Model | Field | Used For |
|-------|-------|----------|
| `sale.order` | `burgtec_quote_reference` | Display name in search |
| `sale.order` | `bom_component_id` | BOM component reference |
| `sale.order.line` | `line_group_id_value` | Group association |
| `sale.order.line` | `line_section_id_value` | Code association |
| `sale.order.line` | `custom_product_name` | Custom product name |
| `product.template` | `is_old_data` | Filter old products |
| `product.template` | `product_bom_type` | Filter component products |

---

## Common Issues and Solutions

### Issue: Drag-and-drop not working
**Cause:** `_sequence_validation()` prevents manual reordering of groups and codes.
**Solution:** Use the swap wizards instead.

### Issue: Wizard not opening
**Cause:** JavaScript `customButtons` state not set.
**Solution:** Ensure the list is `sale.order.line` within `sale.order` context.

### Issue: Duplicate fails with BOM error
**Cause:** Source or target order doesn't have saved BOM components.
**Solution:** Save BOM components on both orders before duplicating.

### Issue: Products not appearing in wizard
**Cause:** Domain filters exclude products.
**Solution:** Check `sale_ok`, `product_bom_type`, and `product_variant_count` fields.

---

## Extending This Module

### Adding a New Wizard Action

1. Create method in `sale.order.line`:
```python
def action_show_wizard_to_new_action(self):
    return {
        'type': 'ir.actions.act_window',
        'target': 'new',
        'name': 'New Action',
        'view_id': self.env.ref('sale_order_customisation.new_wizard_view').id,
        'view_mode': 'form',
        'res_model': 'sale.order.line.wizard',
        'context': {'dialog_size': 'extra-large'}
    }
```

2. Add view ID helper:
```python
@api.model
def get_new_action_form_view_id(self):
    view = self.env.ref('sale_order_customisation.new_wizard_view', raise_if_not_found=False)
    return view.id if view else False
```

3. Add JavaScript method in `sale_order_line_field.js`:
```javascript
async newAction(record) {
    const view_id = await this.orm.call("sale.order.line", "get_new_action_form_view_id", []);
    const result = await this.orm.call("sale.order.line", "action_show_wizard_to_new_action", [record.resId]);
    // ... handle action
}
```

4. Add button in `sale_order_line_field.xml`:
```xml
<button class="btn btn-link p-0" t-on-click="() => this.newAction(record)">
    <i class="fa fa-plus"/> New Action
</button>
```

---

## Version History

| Version | Changes |
|---------|---------|
| 0.1 | Initial release with group/code management, product addition, and duplication features |