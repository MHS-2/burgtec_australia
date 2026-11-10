# Burgtec Delivery Report - Developer Documentation

## Module Overview

| Property | Value |
|----------|-------|
| **Technical Name** | `burgtec_delivery_report` |
| **Version** | 0.1 |
| **Category** | Customizations |
| **License** | LGPL-3 |
| **Dependencies** | `base`, `sale`, `web`, `purchase`, `sale_custom_report`, `quotation_type_customization`, `bom_based_inventory` |

### Purpose

This module generates delivery stage reports for Burgtec business operations. It creates a printable PDF report showing child purchase order details with product tracking checkboxes (Received, Staged, Dispatched, Delivered). The module also includes a QR code generation feature for HubSpot delivery stage ticket URLs and a UI enhancement for toggling the chatter panel.

---

## Directory Structure

```
burgtec_delivery_report/
├── __init__.py
├── __manifest__.py
├── DEVELOPER.md
├── models/
│   ├── __init__.py
│   └── sale_order_ext.py
├── report/
│   ├── __init__.py
│   ├── burgtec_delivery_report.py
│   └── burgtec_delivery_report.xml
├── static/
│   └── src/
│       ├── js/
│       │   └── chatter_toggle.js
│       └── scss/
│           └── chatter_toggle.scss
└── views/
    └── sale_order_ext.xml
```

---

## Models

### Sale Order Extension (`sale.order`)

**File:** `models/sale_order_ext.py`

Extends the standard sale order with QR code generation capabilities.

#### New Fields

| Field | Type | Description |
|-------|------|-------------|
| `qr_url` | Char | HubSpot Delivery Stage ticket URL |
| `qr_code` | Binary | Computed QR code image (stored, readonly) |

#### Key Methods

```python
@api.depends('qr_url')
def _compute_qr_code(self)
```

**Description:** Generates a QR code image from the `qr_url` field.

**Implementation Details:**
- Uses the `qrcode` Python library
- QR Code settings:
  - Version: 1
  - Error correction: `ERROR_CORRECT_L`
  - Box size: 3
  - Border: 4
- Embeds "Sale Order URL: {url}" in the QR code
- Outputs PNG format encoded as base64

**Dependencies:**
```python
import qrcode
from io import BytesIO
import base64
```

---

## Reports

### Burgtec Delivery Report

**File:** `report/burgtec_delivery_report.py`

**Model Name:** `report.burgtec_delivery_report.burgtec_delivery_report`

#### Report Class

```python
class BurgtecDeliveryReport(models.AbstractModel):
    _name = 'report.burgtec_delivery_report.burgtec_delivery_report'
```

#### `_get_report_values` Method

Prepares data for the delivery report template.

**Validation Rules:**
1. `location` field must be set on the sale order
2. `qr_url` field must be set to generate QR code
3. Sale order must have confirmed purchase orders
4. Parent PO must be in `purchase` or `done` state

**Data Flow:**
1. Gets sale order (doc) from docids
2. Retrieves parent purchase orders via `doc._get_purchase_orders()`
3. Finds child POs by searching for POs where `origin` matches picking names
4. Filters out POs where ALL lines are delivery/installation products
5. Sorts child POs by ID

**Return Values:**

| Key | Type | Description |
|-----|------|-------------|
| `doc_ids` | list | Document IDs |
| `doc_model` | str | `'sale.order'` |
| `company` | record | Current company |
| `docs` | recordset | Sale order records |
| `parent_po` | recordset | Parent purchase orders |
| `child_pos` | recordset | Filtered child purchase orders |

---

### Report Template

**File:** `report/burgtec_delivery_report.xml`

**Template ID:** `burgtec_delivery_report`

#### Template Structure

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER                                                       │
│ ┌─────────────────┐  ┌──────────────┐ ┌──────────────────┐  │
│ │ burgtec.        │  │   QR Code    │ │ Location Badge   │  │
│ │                 │  │   [image]    │ │ (Color-coded)    │  │
│ └─────────────────┘  └──────────────┘ └──────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│ Delivery Stage Number: [burgtec_quote_reference]            │
│ Client Name: [partner_id.name]                              │
│ Project Name: [project_name]                                │
├─────────────────────────────────────────────────────────────┤
│ FOR EACH CHILD PO:                                          │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ PO Number: [burgtec_purchase_reference]                 │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ Product Code │ Description │ Qty │ Rcvd │ Stgd │ Disp │ │
│ │──────────────│─────────────│─────│──────│──────│──────│ │
│ │ [code]       │ [name]      │ [x] │ [ ]  │ [ ]  │ [ ]  │ │
│ │              │ Note: [...]  │     │      │      │      │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ FOOTER                                                       │
│ [Location Badge]  Quote: [ref] | [date] | [time]            │
└─────────────────────────────────────────────────────────────┘
```

#### Location Color Coding

| Location | Color | Hex Code |
|----------|-------|----------|
| NSW (New South Wales) | Indigo | `#6366F1` |
| ACT (Australian Capital Territory) | Yellow | `#EAB308` |
| VIC (Victoria) | Green | `#22C55E` |
| QLD (Queensland) | Red | `#DC2626` |
| Other | Purple | `#9333EA` |

#### Table Columns

| Column | Width | Description |
|--------|-------|-------------|
| Product Code | 20% | `product_id.default_code` |
| Description | 35% | `product_id.name` + optional note |
| Qty | 10% | Formatted quantity |
| Received | 18% | Empty checkbox |
| Staged | 18% | Empty checkbox |
| Dispatched | 18% | Empty checkbox |
| Delivered | 18% | Empty checkbox |

#### Paper Format

**Record ID:** `paperformat_burgtec_delivery_report`

| Property | Value |
|----------|-------|
| Format | A4 |
| Orientation | Portrait |
| Margin Top | 5mm |
| Margin Bottom | 10mm |
| Margin Left | 5mm |
| Margin Right | 5mm |
| DPI | 90 |
| Header Line | False |
| Header Spacing | 0 |

#### Report Action

**Record ID:** `action_burgtec_delivery_report`

| Property | Value |
|----------|-------|
| Report Type | qweb-pdf |
| Binding Model | `sale.order` |
| Domain | `[('quote_type','=','delivery_stage')]` |

**Note:** The report only appears in the Print menu for sale orders with `quote_type = 'delivery_stage'`.

---

## Views

### Sale Order Form Extension

**File:** `views/sale_order_ext.xml`

**View ID:** `burgtec_delivery_report_customization_sale_order_extend`

Adds the `qr_url` field to the sale order form inside the `project_rev_details` group.

**Visibility:** Only visible when `quote_type == 'delivery_stage'`

```xml
<field name="qr_url" invisible="quote_type != 'delivery_stage'"/>
```

---

## Static Assets

### Chatter Toggle Feature

This module includes a UI enhancement that adds a toggle button to collapse/expand the chatter panel on form views.

#### JavaScript (`static/src/js/chatter_toggle.js`)

**Purpose:** Patches the `FormCompiler` to inject a toggle button for the chatter panel.

**How It Works:**

1. Patches `FormCompiler.prototype.compile()` method
2. Checks if the form has a chatter container (`.o-mail-Form-chatter`)
3. Creates or finds the status bar element
4. Injects a toggle button with chevron icon
5. Manages collapsed state via `localStorage` key: `odoo_chatter_collapsed`

**Key Features:**
- Persists collapsed state across page reloads
- Only shows toggle button when chatter is in side layout (`SIDE_CHATTER`, `EXTERNAL_COMBO_XXL`)
- Adds `max-width-unset` class to form sheet when collapsed

#### SCSS (`static/src/scss/chatter_toggle.scss`)

**Styles:**

```scss
.max-width-unset {
    max-width: unset !important;  // Allows form to expand when chatter hidden
}

.o_chatter_toggle_btn {
    // Rotates button based on collapsed state
    // Contains animated chevron icon
}
```

**Animation:** Chevron icon animates with a scroll effect using `@keyframes scrollanimate`.

### Asset Registration

```python
"assets": {
    "web.assets_backend": [
        "burgtec_delivery_report/static/src/js/chatter_toggle.js",
        "burgtec_delivery_report/static/src/scss/chatter_toggle.scss",
    ],
},
```

---

## Usage

### Prerequisites

Before generating the report:

1. **Set Quote Type:** Sale order must have `quote_type = 'delivery_stage'`
2. **Set Location:** Select Australian state/territory in `location` field
3. **Set QR URL:** Enter HubSpot delivery stage ticket URL in `qr_url` field
4. **Confirm Orders:**
   - Sale order must be confirmed
   - Parent purchase order must be confirmed (`purchase` or `done` state)
   - Child purchase orders must exist

### Generating the Report

1. Navigate to a Delivery Stage sale order
2. Click **Print** menu
3. Select **Burgtec Delivery Report**
4. PDF will generate with:
   - QR code linking to HubSpot
   - Location badge (color-coded by state)
   - Child PO product tables with tracking checkboxes

### Report Flow Diagram

```
Sale Order (Delivery Stage)
    │
    ├── Validate: location set?
    ├── Validate: qr_url set?
    │
    └── Get Parent Purchase Orders
            │
            └── For each Parent PO:
                    │
                    └── Get Child POs (via picking.name -> origin)
                            │
                            └── Filter: Exclude delivery/installation only POs
                                    │
                                    └── Generate Report with product lines
```

---

## Error Handling

### Validation Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "Please Set the Location First!" | `location` field is empty | Set location on sale order |
| "Please Enter HubSpot Del.Stage ticket URL to Generate Qrcode!" | `qr_url` field is empty | Enter HubSpot URL |
| "NO Purchase Order found, Kindly Confirm this Delivery Stage" | No parent PO linked | Confirm the delivery stage sale order |
| "NO Child Purchase Order found, Kindly Confirm Parent PO" | Parent PO not confirmed | Confirm the parent purchase order |

---

## Dependencies on Other Modules

### From `sale_custom_report`

- `quote_type` field (Selection: sales_quote, project_quote, delivery_stage)
- `location` field (Selection: nsw, act, vic, qld, other)
- `project_name` field

### From `quotation_type_customization`

- `burgtec_quote_reference` field on sale.order
- `burgtec_purchase_reference` field on purchase.order

### From `bom_based_inventory`

- `is_delivery_and_installation` field on product.product (used to filter PO lines)

---

## Extending the Module

### Adding New Location Colors

1. Edit `report/burgtec_delivery_report.xml`
2. Find the location indicator style blocks
3. Add new condition:

```xml
<t t-elif="'new_state' in (o.location or '').lower()">NEW_STATE</t>
```

And in style:
```xml
'new_state' in (o.location or '').lower() and '#HEXCODE' or
```

### Adding New Tracking Columns

1. Edit `report/burgtec_delivery_report.xml`
2. Add new `<th>` in table header
3. Add new `<td>` with checkbox in table body:

```xml
<td class="col-status">
    <div class="status-checkbox"></div>
</td>
```

---

## Technical Notes

### QR Code Library

The module uses the `qrcode` Python library. Ensure it's installed:

```bash
pip install qrcode[pil]
```

### Page Break Handling

The report template includes CSS to prevent awkward page breaks:

```css
.product-table tr {
    page-break-inside: avoid;
    break-inside: avoid;
}
```

Each PO block is wrapped in a div with `page-break-inside: avoid` to keep PO header and table together.

### LocalStorage Usage

The chatter toggle state is persisted using:
- Key: `odoo_chatter_collapsed`
- Values: `"true"` or `"false"` (string)