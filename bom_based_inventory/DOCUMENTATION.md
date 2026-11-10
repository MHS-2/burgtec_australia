# Complete Code Documentation: `bom_based_inventory` Module

## Module Overview

**Name:** BOM Based Inventory
**Version:** 18.1
**Category:** Customizations
**License:** LGPL-3
**Location:** `addons/odoo-customization/bom_based_inventory/`

### Purpose
This module provides comprehensive Bill of Materials (BOM) based inventory management for Burgtec, enabling:
- Component-level cost tracking with 4 cost types (System, Live, Quoted, Pre-Project)
- Automated purchase order creation grouped by supplier
- Multi-stage delivery order management
- Margin and markup calculations
- Excel reporting with product images

### Dependencies
`web`, `base`, `project`, `product`, `sale_project`, `sale_management`, `mrp`, `sale`, `purchase`, `stock`, `account`, `web_progress`

---

## Directory Structure

```
bom_based_inventory/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── sale_order_ext.py           # Sale order & line extensions
│   ├── sale_order_bom_component.py # BOM component management
│   ├── mrp_bom_ext.py              # MRP BOM cost calculations
│   ├── product_template_ext.py     # Product template extensions
│   ├── product_product_ext.py      # Product variant extensions
│   ├── purchase_order_ext.py       # Purchase order extensions
│   ├── split_delivery_order.py     # Multi-stage delivery
│   ├── stock_rule_ext.py           # Purchase order creation logic
│   ├── account_move_ext.py         # Invoice extensions
│   ├── project_project_ext.py      # Project report integration
│   ├── product_pricelist_item_ext.py
│   ├── components_on_sales_report.py
│   └── bom_component_state.py      # JSON state storage
├── wizard/
│   ├── __init__.py
│   ├── bom_component_wizard.py     # Component addition wizard
│   └── bom_component_wizard.xml
├── report/
│   ├── __init__.py
│   ├── sale_report_bom.py          # SQL-based sales report
│   └── sale_report_views.xml
├── security/
│   ├── products_security.xml       # Product Manager group
│   └── ir.model.access.csv         # Model access rights
├── views/                          # 11 XML view files
├── data/
│   └── ir_action_data.xml
└── static/
    ├── src/css/style.css
    └── src/js/disable_list_view_sort.js
```

---

## Models Documentation

### 1. SaleOrderExt (`sale_order_ext.py:22`)

**Inherits:** `sale.order`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `custom_project_id` | Many2one(project.project) | Project reference |
| `bom_component_id` | Many2one(sale.order.bom.component) | Links to BOM components |
| `split_do_id` | Many2one(split.do) | Split delivery order reference |
| `is_old_data` | Boolean | Legacy data flag |
| `is_having_delivery_stage` | Boolean | Has delivery stage |
| `is_having_project_stage` | Boolean | Has project quote |
| `system_cost_per_unit` | Monetary | Margin on system cost |
| `live_unit_cost` | Monetary | Margin on live cost |
| `quoted_cost_per_unit` | Monetary | Margin on quoted cost |
| `pre_project_cost_per_unit` | Monetary | Margin on pre-project cost |
| `system_cost_bom_total` | Monetary | Total BOM system cost |
| `live_cost_bom_total` | Monetary | Total BOM live cost |
| `quoted_cost_bom_total` | Monetary | Total BOM quoted cost |
| `pre_project_cost_bom_total` | Monetary | Total BOM pre-project cost |
| `percentage_margin_*` | Float | Margin % for each cost type |
| `percentage_markup_*` | Float | Markup % for each cost type |
| `state` | Selection | Adds 'quotation_confirmed' state |
| `hubspot_reference` | Char | External Hubspot reference |
| `burgtec_quote_reference` | Char(computed) | Computed reference |

#### Key Methods

```python
def action_quotation_confirm(self):
    """Confirms quotation and updates BOM components.
    Raises UserError if bom_component_id is not set."""

def action_confirm(self):
    """Override - confirms order, sets PO line prices to zero,
    removes 'Exception' activities."""

def action_cancel(self):
    """Cancels order and all related parent/child purchase orders."""

def action_show_component(self):
    """Opens BOM Components form view in current window.
    Updates component HTML for each order line."""

def action_show_delivery_orders(self):
    """Opens Split Delivery Orders in modal dialog."""

@api.onchange('order_line')
def _compute_multi_cost_per_unit(self):
    """Recalculates all cost margins and markups when order lines change.
    Aggregates costs from BOM component lines."""

def copy(self, default=None):
    """Duplicates order with revision naming (A, B, C...).
    Also duplicates BOM components and remaps order line IDs."""

def web_save(self, vals, specification, next_id=None):
    """Restricts editing non-draft orders to Sales Administrators only."""
```

---

### 2. SaleOrderLine (`sale_order_ext.py:597`)

**Inherits:** `sale.order.line`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `old_order_line` | Char | Original line ID during duplication |
| `component_html` | Html | Rendered component table |
| `component_visible` | Boolean | Toggle component display |
| `excel_file` | Binary | Downloadable Excel report |
| `system_cost_per_unit` | Monetary | Line-level margin on system cost |
| `live_unit_cost` | Monetary | Line-level margin on live cost |
| `quoted_cost_per_unit` | Monetary | Line-level margin on quoted cost |
| `pre_project_cost_per_unit` | Monetary | Line-level margin on pre-project cost |
| `*_bom_total` | Monetary | BOM totals for each cost type |

#### Key Methods

```python
def fill_component_html(self):
    """Generates HTML table showing:
    - Product reference & name
    - Quantity, all 4 cost types
    - Supplier, delivery date
    - Purchase order link & status
    Matches components by parent_product_id and order_line_id."""

def unlink(self):
    """Override - resets sequences, recalculates order costs after deletion."""

@api.onchange('product_uom_qty')
def _update_split_delivery_order_vals(self):
    """Updates split delivery order quantities when line qty changes."""
```

---

### 3. SaleOrderBOMComponent (`sale_order_bom_component.py:21`)

**Model:** `sale.order.bom.component`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | Many2one(sale.order) | Parent sale order (required) |
| `state` | Selection(related) | Related to order state |
| `component_line_ids` | One2many | Child component lines |
| `show_warning` | Boolean(computed) | Warning for manual components |
| `show_live_percentage_warning` | Boolean(computed) | Warning for margin issues |
| `component_state_id` | Many2one(bom.component.state) | JSON state storage |
| `force_compute_trigger` | Integer | Triggers recomputation |
| `view_team` | Selection | Team view filter |

#### Key Methods

```python
def _read_component_state(self) -> dict:
    """Returns deep copy of stored JSON state.
    Creates state record if not exists."""

def _write_component_state(self, state: dict):
    """Persists state dictionary to database."""

def _get_product_state(self, order_line_id, product_id, state_dict=None) -> dict:
    """Gets product-specific state from nested dictionary.
    Structure: {order_line_id: {product_id: {...state...}}}"""

def _batch_update_state(self, updates: list):
    """Batch updates state with list of (order_line_id, product_id, updater) tuples.
    Single database write for all updates."""

def _update_product_state(self, order_line_id, product_id, updater, create=True):
    """Updates single product state using updater callback function."""

def _compute_component_quantities(self, parent):
    """Recalculates child component quantities based on parent qty.
    Uses stored proportion_factor or BOM defaults."""

@api.onchange('component_line_ids')
def onchange_component_line_ids(self):
    """Updates sequences, parent/child relationships.
    Recalculates parent costs from children.
    Stores proportion factors in state."""

def _compute_cost_margin(self):
    """Aggregates all costs and writes to sale order.
    Calculates margin/markup percentages."""

def update_component_lines(self):
    """Creates/updates component lines from sale order lines.
    - Creates section headers
    - Creates parent lines for each product
    - Creates child lines from BOM
    - Batch updates state with proportion factors"""

def action_fetch_live_cost(self):
    """Updates live_unit_cost from product.standard_price for all components."""

def action_quoted_cost(self):
    """Copies live_unit_cost to quoted_cost_per_unit."""

def action_fetch_pre_project_cost(self):
    """Copies live_unit_cost to pre_project_cost_per_unit."""

@api.model
def default_get(self, fields):
    """Creates initial component structure from sale order lines and BOMs.
    Builds initial state dictionary."""
```

---

### 4. SaleOrderBOMComponentLine (`sale_order_bom_component.py:996`)

**Model:** `sale.order.bom.component.line`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `component_id` | Many2one | Parent BOM component |
| `product_id` | Many2one(product.product) | Component product (domain: components type) |
| `order_line_id` | Many2one(sale.order.line) | Parent sale line |
| `parent_product_id` | Many2one(product.template) | Parent product template |
| `parent_number` | Integer | Parent serial number |
| `product_qty` | Float | Component quantity |
| `unit_sale_price` | Float | Sale price per unit |
| `total_sale_price` | Float(computed) | qty x unit_sale_price |
| `product_reference` | Char(related) | Product default_code |
| `live_unit_cost` | Float | Total live cost |
| `manual_live_unit_cost` | Float | Per-unit live cost |
| `system_cost_per_unit` | Float | System cost |
| `quoted_cost_per_unit` | Float | Quoted cost |
| `pre_project_cost_per_unit` | Float | Pre-project cost |
| `supplier_id` | Many2one(res.partner) | Component supplier |
| `is_parent` | Boolean | Is parent product line |
| `is_auto_generated` | Boolean | Generated from BOM |
| `display_type` | Selection | 'line_section' for headers |
| `sequence` | Integer | Line sequence |
| `note` | Text | Notes for component |
| `margin_*_per_parent` | Float(computed) | Margin % per cost type |
| `markup_*_per_parent` | Float(computed) | Markup % per cost type |

#### Key Methods

```python
@api.depends('product_qty', 'unit_sale_price', ...)
def _compute_margins_and_markups(self):
    """Calculates margin and markup percentages for each cost type.
    Margin = (sale_price - cost) / sale_price
    Markup = (sale_price - cost) / cost"""

@api.onchange('manual_live_unit_cost', 'product_qty')
def onchange_manual_unit_cost(self):
    """Syncs manual_live_unit_cost to live_unit_cost."""

@api.onchange('product_id')
def onchange_product_id(self):
    """Updates costs and supplier when product changes.
    Stores initial state values."""

@api.onchange('product_qty')
def onchange_product_qty(self):
    """Recalculates costs when quantity changes.
    Updates proportion_factor in state.
    Handles parent quantity changes cascading to children."""

def action_open_add_components_wizard(self):
    """Opens wizard to add additional components to this parent line.
    Restricted by state and user permissions."""
```

---

### 5. StockRuleExt (`stock_rule_ext.py:18`)

**Inherits:** `stock.rule`

#### Key Methods

```python
def _make_purchase_order(self, purchase_orders):
    """Custom PO creation logic based on BOM components.

    For Child POs (from dropship):
    - Groups components by supplier
    - Calculates proportional quantities from BOM
    - Creates separate PO per supplier with aggregated lines

    For Parent POs (from sale order):
    - Creates POs based on split delivery stages (1-5)
    - Each stage becomes a separate PO

    Manages PO sequence numbering to avoid gaps."""

def _create_po_for_multiple_order_lines(self, lines, po_ref_list, po_origin, po_date_order):
    """Helper to create POs grouped by supplier from component lines."""

@api.model
def _run_buy(self, procurements):
    """Override of standard procurement processing.
    Calls _make_purchase_order after standard PO creation."""
```

---

### 6. PurchaseOrderExt (`purchase_order_ext.py:7`)

**Inherits:** `purchase.order`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `builder_trend_po` | Char | Buildertrend PO # |
| `delivery_stage` | Char | Delivery stage number |
| `tag` | Selection | 'child' or 'parent' PO |
| `burgtec_purchase_reference` | Char(computed) | Format: P{stage}-{count} |
| `is_builder_trend` | Boolean | Buildertrend flag |
| `child_po_count` | Integer | Child PO sequence number |
| `burgtec_po_status` | Selection | Custom status tracking (8 states) |
| `hubspot_reference` | Char | External reference |

#### Key Methods

```python
@api.depends('delivery_stage', 'child_po_count')
def _compute_po_ref(self):
    """Computes burgtec_purchase_reference:
    Parent: P{delivery_stage}
    Child: PO-{delivery_stage}-{child_po_count:02d}"""

def action_create_invoice(self):
    """Override - prevents bill creation for parent POs.
    Sets burgtec_bill_reference on created bills."""

def button_confirm(self):
    """Override - passes purchase_order_id in context for stock rule."""

def write(self, vals):
    """Override - updates component HTML when date_planned or state changes."""
```

---

### 7. SplitDO (`split_delivery_order.py:14`)

**Model:** `split.do`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | Many2one(sale.order) | Parent sale order |
| `state` | Selection(related) | Order state |
| `line_ids` | One2many(split.do.line) | Delivery stage lines |

#### Key Methods

```python
@api.onchange('line_ids')
def onchange_line_ids(self):
    """Validates total stage quantities don't exceed line quantity.
    Calculates available_quantity for each line."""

@api.model
def default_get(self, fields_list):
    """Creates lines from sale order lines with initial stage 1 quantities."""
```

---

### 8. SplitDOLine (`split_delivery_order.py:82`)

**Model:** `split.do.line`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `split_id` | Many2one(split.do) | Parent split DO |
| `product_id` | Many2one(product.template) | Product |
| `quantity` | Float(related) | Total quantity from order line |
| `available_quantity` | Float | Unscheduled quantity |
| `do_stage_1` through `do_stage_5` | Integer | 5 delivery stage quantities |
| `order_line_id` | Many2one(sale.order.line) | Source order line |

#### Constraints

```python
@api.constrains('quantity', 'do_stage_1', ..., 'do_stage_5')
def _check_do_stage_total(self):
    """Ensures sum of all stages equals line quantity."""
```

---

### 9. ProductTemplateExt (`product_template_ext.py:7`)

**Inherits:** `product.template`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `product_bom_type` | Selection | 'product' or 'components' (required) |
| `is_delivery_and_installation` | Boolean | Service flag |
| `external_id_computed` | Char(computed) | XML ID |
| `product_pricing_category` | Text | Pricing category |

#### Key Methods

```python
@api.onchange('product_bom_type')
def _set_routes(self):
    """Sets routes based on type:
    - 'product': Dropship route
    - 'components': Subcontracting dropship route"""

def web_save(self, vals, specification, next_id=None):
    """Only Product Managers can edit products."""

def create(self, vals_list):
    """Only Product Managers can create products."""

def unlink(self):
    """Only Product Managers can delete products."""

def action_update_product_template_cost(self):
    """Updates standard_price from BOM costs."""
```

---

### 10. MrpBomExt (`mrp_bom_ext.py:5`)

**Inherits:** `mrp.bom`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `bom_cost` | Float(computed) | Total BOM cost |

#### Key Methods

```python
@api.depends('bom_line_ids.product_id.standard_price', 'bom_line_ids.product_qty')
def _compute_bom_cost(self):
    """Sums (standard_price x product_qty) for all BOM lines."""

def create(self, vals_list):
    """Triggers product template cost update after creation."""

def write(self, vals):
    """Triggers product template cost update after modification."""
```

---

### 11. BomComponentState (`bom_component_state.py:3`)

**Model:** `bom.component.state`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `component_state` | Json | State dictionary (default: {}) |
| `order_id` | Many2one(sale.order) | Parent sale order |
| `bom_component_id` | Many2one(related) | Related BOM component |

#### State Structure
```json
{
  "order_line_id": {
    "product_id": {
      "proportion_factor": 0.5,
      "custom_proportion": true,
      "live_unit_cost": 100.0,
      "quoted_cost_per_unit": 100.0,
      "pre_project_cost_per_unit": 100.0,
      "product_qty": 2,
      "skip_live_unit_cost": false,
      "skip_quoted_cost_per_unit": false,
      "skip_pre_project_cost_per_unit": false
    }
  }
}
```

---

### 12. AccountMoveExt (`account_move_ext.py:4`)

**Inherits:** `account.move`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `burgtec_bill_reference` | Char | Manual reference |
| `burgtec_bill_reference_computed` | Char(computed) | Combined ref |
| `is_old_data` | Boolean | Legacy flag |

---

### 13. ProjectProjectExt (`project_project_ext.py:4`)

**Inherits:** `project.project`

#### Methods

```python
def action_open_bom_report_for_project(self):
    """Opens Sales BOM Report filtered by this project."""
```

---

### 14. ProductProductExt (`product_product_ext.py:7`)

**Inherits:** `product.product`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `variant_bom_type` | Selection(computed) | Inherits from product_tmpl_id.product_bom_type |
| `fabric_meterage` | Float | Fabric meterage |
| `external_id_computed` | Char(computed) | XML ID |

#### Key Methods

```python
@api.depends('product_tmpl_id.product_bom_type')
def _compute_variant_bom_type(self):
    """Inherits product_bom_type from product template."""

def action_update_product_product_cost(self):
    """Updates standard_price from matching BOM cost."""
```

---

### 15. ComponentsOnReport (`components_on_sales_report.py:5`)

**Model:** `components.on.report`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `component_line_ids` | One2many | Report component lines |

#### Key Methods

```python
@api.model
def default_get(self, fields):
    """Populates component lines from sale order BOM components.
    Matches child purchase orders by origin and supplier."""
```

---

### 16. ComponentsOnReportLine (`components_on_sales_report.py:50`)

**Model:** `components.on.report.line`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `report_id` | Many2one | Parent report |
| `product_id` | Many2one | Component product |
| `product_qty` | Float | Quantity |
| `live_unit_cost` | Float | Live cost |
| `system_cost_per_unit` | Float | System cost |
| `quoted_cost_per_unit` | Float | Quoted cost |
| `pre_project_cost_per_unit` | Float | Pre-project cost |
| `supplier_id` | Many2one | Supplier |
| `delivery_date` | Datetime | Delivery date |
| `purchase_order_id` | Many2one | Related PO |

---

### 17. ProductPricelistItemExt (`product_pricelist_item_ext.py:3`)

**Inherits:** `product.pricelist.item`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `manual_cost` | Float | Manual cost override |

---

## Wizard Documentation

### BOMComponentWizard (`bom_component_wizard.py:6`)

**Model:** `bom.component.wizard` (TransientModel)

**Purpose:** Add additional components to a parent product line

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `component_id` | Many2one | Parent BOM component |
| `parent_line_id` | Many2one | Parent component line |
| `parent_product_id` | Many2one | Parent product template |
| `component_line_ids` | One2many(wizard.line) | Components to add |

#### Key Methods

```python
@api.model
def default_get(self, fields_list):
    """Initializes wizard from active component line.
    Creates section header with parent product name."""

def action_add_components(self):
    """Creates component lines:
    1. Shifts existing sequences to make room
    2. Creates lines with calculated quantities (wizard_qty x parent_qty)
    3. Sets costs from product standard_price
    4. Calls onchange_component_line_ids to update state"""

def get_product_suppiler(self, product_id):
    """Returns first supplier partner_id from product.seller_ids."""
```

### BOMComponentWizardLine (`bom_component_wizard.py:108`)

**Model:** `bom.component.wizard.line` (TransientModel)

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `wizard_id` | Many2one | Parent wizard |
| `product_id` | Many2one | Component product (domain: components type) |
| `display_type` | Selection | 'line_section' or 'line_note' |
| `product_qty` | Float | Quantity (default: 1.0) |
| `unit_sale_price` | Float | Unit price |

#### Key Methods

```python
@api.onchange('product_id')
def _onchange_product_id(self):
    """Updates unit_sale_price from product.standard_price."""
```

---

## Report Documentation

### SaleReportBom (`sale_report_bom.py:18`)

**Model:** `sale.report.bom` (SQL View)
**Auto:** False (manual table query)

**Purpose:** Sales analysis report with BOM component data

#### Key Fields (from SQL)
- Sale order: `name`, `date`, `partner_id`, `user_id`, `state`
- Order line: `product_id`, `product_uom_qty`, `price_subtotal`, `price_total`
- Component costs: `system_cost_per_unit`, `live_unit_cost`, `quoted_cost_per_unit`, `pre_project_cost_per_unit`
- Margins: `system_cost_total`, `live_cost_total`, `quoted_cost_total`, `pre_project_total`
- Related: `component_html`, `component_visible`, `po_id`, `delivery_date`

#### Key Methods

```python
def _query(self):
    """Returns SQL query joining sale_order_line, sale_order,
    product, partner, purchase_order, and currency tables."""

def action_open_order(self):
    """Opens linked sale order form."""

def action_open_order_components(self):
    """Opens components in modal dialog."""

def show_bom_components_in_list(self):
    """Toggles component_visible and updates component_html."""

def action_xlwt_report(self):
    """Generates Excel report using xlwt library.
    Includes order details and component breakdown."""

def action_xlswriter_report(self):
    """Generates Excel report using xlsxwriter.
    Includes product images with resize/conversion handling."""
```

---

## Security Configuration

### Security Group (`products_security.xml`)

```xml
<record id="group_product_manager" model="res.groups">
    <field name="name">Product Manager</field>
    <field name="users" eval="[(4, ref('base.user_admin'))]"/>
</record>
```

### Model Access (`ir.model.access.csv`)

| Model | Read | Write | Create | Delete |
|-------|------|-------|--------|--------|
| sale.order.bom.component | Yes | Yes | Yes | Yes |
| sale.order.bom.component.line | Yes | Yes | Yes | Yes |
| sale.report.bom | Yes | Yes | Yes | Yes |
| components.on.report | Yes | Yes | Yes | Yes |
| components.on.report.line | Yes | Yes | Yes | Yes |
| split.do | Yes | Yes | Yes | Yes |
| split.do.line | Yes | Yes | Yes | Yes |
| bom.component.wizard | Yes | Yes | Yes | Yes |
| bom.component.wizard.line | Yes | Yes | Yes | Yes |
| bom.component.state | Yes | Yes | Yes | Yes |

### Additional Access Rules
- `res.partner` read access for Purchase Manager, Sale Manager, MRP Manager, Stock Manager groups

---

## Key Workflows

### 1. Sale Order to BOM Components

```
1. User creates Sale Order with product lines
2. User clicks "Show Components" button
3. System creates SaleOrderBOMComponent with:
   - Section header per product
   - Parent line per product
   - Child lines from MRP BOM
4. System stores proportion_factors in BomComponentState
5. User can modify quantities, costs, add components via wizard
6. System recalculates margins/markups on changes
```

### 2. Sale Order Confirmation to Purchase Orders

```
1. User confirms quotation (action_quotation_confirm)
2. User confirms sale order (action_confirm)
3. Stock rules trigger _run_buy -> _make_purchase_order
4. For Parent POs:
   - Created per delivery stage from split.do
   - One PO per active stage
5. For Child POs:
   - Components grouped by supplier
   - Quantities calculated from BOM proportions
   - One PO per supplier
```

### 3. Cost Calculation Flow

```
Component Level:
  system_cost = product_qty x product.standard_price
  live_unit_cost = product_qty x manual_live_unit_cost
  quoted_cost = manually set or copied from live
  pre_project_cost = manually set or copied from live

Parent Level:
  Sum of all child component costs per type

Order Level:
  Total sale price - Sum of parent costs = Margin
  Margin / Sale price = Margin %
  Margin / Cost = Markup %
```

### 4. Duplication Workflow

```
1. User duplicates sale order
2. System creates revision name (S00001 -> S00001 - Revision A)
3. BOM component record is copied
4. Order line mappings are preserved via old_order_line field
5. Component lines are remapped to new order lines
6. State is preserved in new BomComponentState record
```

---

## Static Assets

### CSS (`static/src/css/style.css`)
Custom styling for BOM component views

### JavaScript (`static/src/js/disable_list_view_sort.js`)
Prevents manual drag-and-drop reordering of component lines (triggers reload warning via RedirectWarning)

---

## View Files

| File | Purpose |
|------|---------|
| `sale_order_ext.xml` | Sale order form modifications, buttons, cost fields |
| `sale_order_bom_componenet.xml` | BOM component form and tree views |
| `productc_template_ext.xml` | Product template form with BOM type field |
| `project_project_ext.xml` | Project form with BOM report button |
| `components_on_sale_report.xml` | Components report dialog views |
| `purchase_order_line_.xml` | Purchase order line modifications |
| `split_delivery_order.xml` | Split delivery order form |
| `account_move_ext.xml` | Invoice/bill reference fields |
| `product_price_list_view_ext.xml` | Pricelist item modifications |
| `mrp_bom_form_view_ext.xml` | BOM form with cost field |

---

## Data Files

### `data/ir_action_data.xml`
Contains server actions and automated actions for the module.

---

## Error Handling

The module uses the following exceptions:
- `UserError` - For user-facing validation errors
- `AccessError` - For permission-related restrictions
- `ValidationError` - For data validation constraints
- `RedirectWarning` - For sequence drag-drop prevention (reloads page)

### Common Error Scenarios
1. **"Kindly Set and Save Bom Components!"** - Attempting to confirm without BOM
2. **"Only Sales Administrator can edit..."** - Non-admin editing confirmed order
3. **"Only Product Managers Can..."** - Non-manager product operations
4. **"Revision limit reached (Z)"** - 26 revisions exhausted
5. **"Total of DO Stage quantities must equal..."** - Split DO validation failure

---

## Performance Considerations

1. **Batch State Updates** - `_batch_update_state()` minimizes database writes
2. **Progress Indicators** - Long operations use `with_progress()` for user feedback
3. **SQL Report View** - `sale.report.bom` uses raw SQL for performance
4. **Lazy Component Loading** - Component HTML generated on-demand via `fill_component_html()`

---

## Integration Points

### Hubspot
- `hubspot_reference` field on sale.order and purchase.order
- Used for external system synchronization

### Buildertrend
- `builder_trend_po` field on purchase.order
- `is_builder_trend` flag for identification

### Projects
- `custom_project_id` links sales to projects
- Project-based BOM report filtering

---

*Documentation generated for bom_based_inventory module v18.1*
