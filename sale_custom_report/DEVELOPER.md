# Sale Custom Report - Developer Documentation

## Module Overview

| Property | Value |
|----------|-------|
| **Technical Name** | `sale_custom_report` |
| **Version** | 0.1 |
| **Category** | Customizations |
| **License** | LGPL-3 |
| **Dependencies** | `base`, `project`, `sale`, `bom_based_inventory`, `web` |

### Purpose

This module provides custom Burgtec-specific sale quotation reports with advanced delivery cost calculation, zone-based pricing, and hierarchical product grouping (Groups and Codes). It extends standard Odoo sale orders with additional fields for project management, delivery tracking, and specialized PDF report generation.

---

## Directory Structure

```
sale_custom_report/
├── __init__.py
├── __manifest__.py
├── DEVELOPER.md
├── data/
│   ├── ir_action_data.xml          # Server actions for reports
│   └── sequence_data.xml           # Project reference sequence
├── models/
│   ├── __init__.py
│   ├── delivery_code_calculation.py
│   ├── product_delivery_cost_group_code.py
│   ├── product_template_ext.py
│   ├── project_project_ext.py
│   ├── purchase_order_ext.py
│   ├── sale_order_bom_component_line_ext.py
│   └── sale_order_ext.py
├── report/
│   ├── __init__.py
│   ├── sale_quote_burgtec_report.py
│   └── sale_quote_burgtec_report.xml
├── security/
│   └── ir.model.access.csv
├── static/
│   ├── img/                        # Report certification images
│   └── src/
│       ├── css/
│       ├── fonts/                  # Graphik font family
│       ├── js/
│       ├── less/
│       └── xml/
└── views/
    ├── delivery_code_calculation_view.xml
    ├── product_delivery_cost_group_code.xml
    ├── product_template_extended.xml
    ├── project_project_extended.xml
    ├── purchase_order_ext_view.xml
    ├── sale_order_bom_component_line_ext.xml
    └── sale_order_extended.xml
```

---

## Models

### 1. Sale Order Extension (`sale.order`)

**File:** `models/sale_order_ext.py`

Extends the standard sale order with Burgtec-specific fields and functionality.

#### New Fields

| Field | Type | Description |
|-------|------|-------------|
| `hubspot_reference` | Char | External Hubspot CRM reference |
| `project_name` | Char | Project name for the quotation |
| `delivery_code_calculation_id` | Many2one | Link to delivery cost calculation |
| `is_show_total_breakdown` | Boolean | Toggle total breakdown in reports (default: True) |
| `quote_type` | Selection | Type: `sales_quote`, `project_quote`, `delivery_stage` |
| `buildertrend_po` | Char | Buildertrend PO reference |
| `is_in_builder_trend` | Boolean | Builder Trend integration flag |
| `delivery_stage` | Char | Delivery stage identifier |
| `zone_type` | Selection | Delivery zone: `zone1`, `zone2`, `zone3` |
| `location` | Selection | Australian state/territory |

#### Key Methods

```python
def action_confirm(self)
    # Sets default quote_type to 'project_quote' on confirmation

def create(self, vals_list)
def write(self, values)
    # Automatically assigns line_group_name, line_section_name to order lines
    # based on section/note hierarchy

def action_show_delivery_code_calculation(self)
    # Opens delivery code calculation wizard

def action_preview_burgtec_pdf_report(self)
    # Generates Burgtec custom PDF report

def force_calculate_summary(self)
    # Forces recalculation of delivery code summary
```

### 2. Sale Order Line Extension (`sale.order.line`)

**File:** `models/sale_order_ext.py`

#### New Fields

| Field | Type | Description |
|-------|------|-------------|
| `custom_product_code` | Char | Custom product code |
| `custom_product_name` | Char | Computed from product template |
| `image_128` | Image | Line-specific product image |
| `line_group_id_value` | Char | Parent group line ID |
| `line_section_id_value` | Char | Parent section line ID |
| `line_group_name` | Char | Parent group name |
| `line_section_name` | Char | Parent section/code name |
| `is_image_available` | Boolean | Computed: checks if product has image |

#### Key Methods

```python
def _compute_custom_product_name(self)
    # Gets name from product_template_id or product_id

def create(self, vals_list)
    # Syncs new lines to delivery_code_calculation if exists

def format_product_description(self, text)
    # Wraps headings (Dimensions:, Features:, etc.) in <strong> tags
```

---

### 3. Product Delivery Cost Group Code (`product.delivery.cost.group.code`)

**File:** `models/product_delivery_cost_group_code.py`

New model for managing delivery cost codes with zone-based pricing.

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `delivery_code` | Char | Unique delivery code identifier |
| `cbm_flatpacked` | Float | Cubic meters when flatpacked |
| `cbm_assembled` | Float | Cubic meters when assembled |
| `description` | Text | Code description |
| **Zone 1 (Eastcoast Metro)** | | |
| `delivery_code_cost` | Monetary | Zone 1 delivery cost |
| `installation_cost` | Monetary | Zone 1 installation cost |
| `zone1_website_minimum` | Float | Minimum for website |
| `zone1_website_sale_price` | Monetary | Website sale price |
| **Zone 2 (SYD)** | | |
| `zone2_delivery_cost` | Monetary | Zone 2 delivery cost |
| `zone2_installation_cost` | Monetary | Zone 2 installation cost |
| `zone2_website_minimum` | Float | Minimum for website |
| `zone2_website_sale_price` | Monetary | Website sale price |
| **Zone 3 (BNE/MEL)** | | |
| `zone3_delivery_cost` | Monetary | Zone 3 delivery cost |
| `zone3_installation_cost` | Monetary | Zone 3 installation cost |
| `zone3_website_minimum` | Float | Minimum for website |
| `zone3_website_sale_price` | Monetary | Website sale price |

---

### 4. Delivery Code Calculation (`delivery.code.calculation`)

**File:** `models/delivery_code_calculation.py`

Main model for calculating delivery and installation costs based on sale order lines.

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | Many2one | Related sale order |
| `delivery_code_calculation_line_ids` | One2many | Calculation detail lines |
| `delivery_code_calculation_summary_line_ids` | One2many | Summary by delivery code |
| `zone_type` | Selection | Inherited from sale order |
| `final_total_cost` | Monetary | Computed total cost |
| `final_cbm_flatpacked` | Float | Total CBM flatpacked |
| `final_cbm_assembled` | Float | Total CBM assembled |
| `final_total_installation_cost` | Monetary | Total installation cost |
| `final_total_delivery_cost` | Monetary | Total delivery cost |
| `manual_percentage` | Float | Markup percentage |
| `final_total_cost_with_markup` | Monetary | Total with markup applied |
| `excel_file` | Binary | Generated Excel export |
| `file_name` | Char | Excel file name |

#### Key Methods

```python
def _compute_total_cost(self)
    # Calculates totals by group/section hierarchy
    # Handles individual products without group/section

def _compute_summary_lines(self)
    # Aggregates quantities by delivery code

def default_get(self, fields_list)
    # Populates lines from active sale order context

def action_xlswriter_report(self)
    # Exports summary to Excel file
```

---

### 5. Delivery Code Calculation Line (`delivery.code.calculation.line`)

**File:** `models/delivery_code_calculation.py`

Detail lines for delivery cost calculation.

#### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `product_id` | Many2one | Product template |
| `product_group_delivery_code_id` | Many2one | Related delivery code |
| `quantity` | Float | Related from sale order line |
| `cbm_flatpacked` / `cbm_assembled` | Float | CBM values |
| `product_delivery_cost` | Monetary | Zone 1 delivery cost |
| `zone2_delivery_cost` / `zone3_delivery_cost` | Monetary | Other zone costs |
| `installation_cost` | Monetary | Zone 1 installation |
| `zone2_installation_cost` / `zone3_installation_cost` | Monetary | Other zones |
| `total_delivery_cost` | Monetary | Computed based on zone |
| `total_installation_cost` | Monetary | Computed based on zone |
| `display_type` | Selection | `line_section`, `line_note`, `line_group` |
| `is_manual_edit` | Boolean | Tracks manual edits |

---

### 6. Product Template Extension (`product.template`)

**File:** `models/product_template_ext.py`

Extends products with quotation-specific description fields.

#### New Fields

| Field | Type | Description |
|-------|------|-------------|
| `custom_product_description` | Text | Custom description for reports |
| `quotation_dimensions` | Text | Product dimensions |
| `quotation_features` | Text | Product features |
| `quotation_finishes` | Text | Available finishes |
| `quotation_warranty` | Text | Warranty information |
| `quotation_lead_time` | Text | Lead time information |
| `quotation_other_details` | Text | Additional details |
| `delivery_code_selection_id` | Many2one | Link to delivery cost code |
| `cbm_flatpacked` | Float | Related from delivery code |
| `cbm_assembled` | Float | Related from delivery code |

#### Computed Field

```python
@api.depends("quotation_dimensions", "quotation_features", ...)
def _compute_description_sale(self)
    # Auto-generates description_sale from quotation fields
    # Format: "Dimensions:\n{value}\nFeatures:\n{value}\n..."
```

---

### 7. Project Extension (`project.project`)

**File:** `models/project_project_ext.py`

#### New Fields

| Field | Type | Description |
|-------|------|-------------|
| `project_reference` | Char | Auto-generated sequence |
| `delivery_installation_cost` | Monetary | Project-level delivery cost |

#### Key Method

```python
def create(self, vals_list)
    # Auto-assigns project_reference from sequence 'project.reference'
```

---

### 8. Purchase Order Line Extension (`purchase.order.line`)

**File:** `models/purchase_order_ext.py`

#### New Fields

| Field | Type | Description |
|-------|------|-------------|
| `line_group_name` | Char | Related from sale line |
| `line_section_name` | Char | Related from sale line |
| `line_group_name_child` | Char | For child PO lines |
| `line_section_name_child` | Char | For child PO lines |

---

### 9. Sale Order BOM Component Line Extension

**File:** `models/sale_order_bom_component_line_ext.py`

#### Key Method

```python
def action_open_update_parent_line(self)
    # Opens popup to edit parent sale order line (image, description)
```

---

## Reports

### Report Classes

**File:** `report/sale_quote_burgtec_report.py`

#### `SaleQuoteBurgtecReport` (V1)

- **Name:** `report.sale_custom_report.burgtec_sale_quote`
- Organizes lines by Group > Code > Products hierarchy
- Validates line structure (Group must have Code, Code must have products)
- Returns nested dictionary structure for template rendering

#### `SaleQuoteBurgtecReportV2` (Current)

- **Name:** `report.sale_custom_report.burgtec_sale_quote_v2`
- Simplified structure using `line_group_id_value` and `line_section_id_value`
- Returns:
  - `order_lines`: Product lines data
  - `groups_total`: Dictionary of group totals `{group_id: [qty, subtotal]}`
  - `codes_total`: Dictionary of code totals `{code_id: subtotal}`
  - `total_dict`: Overall totals including GST

### Validation Rules

Both report classes enforce these validation rules:
1. A Code (`line_note`) must be inside a Group (`line_section`)
2. A Group must be followed by a Code
3. A Code must have products
4. No consecutive Groups or Codes without products

---

## Views

### Sale Order Views

**File:** `views/sale_order_extended.xml`

- Extended tree view with `hubspot_reference`, `project_name`, `delivery_stage`, `quote_type`
- Extended form view with:
  - Type Selections group (`quote_type`, `zone_type`, `delivery_stage`)
  - Report Configuration tab (`is_show_total_breakdown`)
  - "Delivery Costs" button to open calculation wizard
  - Custom product name and image fields on order lines
  - Renamed "Add a Section" to "Add a Group"
  - Renamed "Add a Note" to "Add a Code"
- Search filters for quote types
- Menu items for Sales Quote, Project Quote, Delivery Stages

### Delivery Code Calculation View

**File:** `views/delivery_code_calculation_view.xml`

Form view with:
- Zone type selector
- Lines tab with editable cost fields (zone-specific visibility)
- Summary tab with Excel export button
- Footer totals with markup calculation

### Product Template Views

**File:** `views/product_template_extended.xml`

- Delivery code selection dropdown
- Quotation Description Details group with all quotation fields

---

## Data Files

### Sequences

**File:** `data/sequence_data.xml`

```xml
<record id="project_reference_sequence" model="ir.sequence">
    <field name="name">Project Reference Sale Report</field>
    <field name="code">project.reference</field>
    <field name="padding">4</field>
</record>
```

### Server Actions

**File:** `data/ir_action_data.xml`

- `preview_burgtec_pdf_report`: Bound to sale.order form, triggers PDF preview

---

## Security

**File:** `security/ir.model.access.csv`

| Model | Access |
|-------|--------|
| `product.delivery.cost.group.code` | Full (CRUD) |
| `delivery.code.calculation` | Full (CRUD) |
| `delivery.code.calculation.line` | Full (CRUD) |
| `delivery.code.calculations.summary.line` | Full (CRUD) |

---

## Static Assets

### Web Assets (Backend)

```python
"web.assets_backend": [
    "/sale_custom_report/static/src/js/web_widget_image_paste_upload.js",
    "/sale_custom_report/static/src/xml/web_widget_image_paste_upload.xml",
],
```

### Report Assets

```python
"web.report_assets_common": [
    "/sale_custom_report/static/src/less/fonts.less",
],
```

### Fonts

Custom Graphik font family (Light, Regular, Medium, Semibold, Bold, Black, etc.) for report styling.

### Images

Certification badges:
- `231207_GreenRate_C_CertTag_Black.jpg`
- `australian-made.png`
- `supply-certified.png`
- `supply-nation-member.jpg`

---

## Zone Definitions

| Zone | Description | Locations |
|------|-------------|-----------|
| Zone 1 | EASTCOAST METRO | BNE, SYD, CBR, MEL |
| Zone 2 | Sydney Extended | SYD |
| Zone 3 | Brisbane/Melbourne Extended | BNE/MEL |

---

## Usage Flow

### Creating a Quotation with Delivery Calculation

1. Create a Sale Order
2. Select `quote_type` (Sales Quote, Project Quote, Delivery Stage)
3. Select `zone_type` for pricing
4. Add order lines using Groups and Codes:
   - Add a Group (Section)
   - Add a Code (Note) under the Group
   - Add Products under the Code
5. Click "Delivery Costs" button to open calculation wizard
6. Review/adjust costs per line
7. Export summary to Excel if needed
8. Generate Burgtec PDF report using server action

### Report Generation

```python
# URL Pattern for PDF Report
/report/pdf/sale_custom_report.burgtec_sale_quote_v2/{sale_order_id}
```

---

## Extending the Module

### Adding a New Zone

1. Add zone selection in `SaleOrderExt.zone_type` field
2. Add zone fields in `ProductDeliveryCostGroupCode` model
3. Add computed fields in `DeliveryCodeCalculationLine` model
4. Update `_compute_total_delivery_cost` and `_compute_total_installation_cost` methods
5. Update views to show/hide zone-specific fields

### Adding New Quotation Fields

1. Add field to `ProductTemplateExt` model
2. Update `_compute_description_sale` method
3. Add field to product template views
4. Update report template to display new field

---

## API Reference

### Key Actions

| Action | Model | Type | Description |
|--------|-------|------|-------------|
| `action_preview_burgtec_pdf_report` | sale.order | object | Generate PDF |
| `action_show_delivery_code_calculation` | sale.order | object | Open calculator |
| `action_xlswriter_report` | delivery.code.calculation | object | Export Excel |
| `action_open_update_parent_line` | sale.order.bom.component.line | object | Edit parent line |

### Context Keys

| Key | Used In | Description |
|-----|---------|-------------|
| `active_id` | delivery.code.calculation | Sale order ID for default_get |
| `active_model` | delivery.code.calculation | Model name for linking |

---

## Troubleshooting

### Common Errors

1. **"No Group Found"** - Ensure products are under a Group (Section) and Code (Note)
2. **"No Code Found"** - Add a Code line before products
3. **"Code must be inside a group"** - Reorder lines so Code follows Group
4. **"must have products"** - Add product lines under each Code

### Debug Tips

- Check `line_group_name` and `line_section_name` on order lines
- Verify `delivery_code_selection_id` is set on products
- Review delivery code costs in Configuration > Product Delivery Codes