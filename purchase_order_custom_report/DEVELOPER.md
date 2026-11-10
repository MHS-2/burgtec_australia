# Purchase Order Custom Report - Developer Documentation

## Module Overview

| Property | Value |
|----------|-------|
| **Technical Name** | `purchase_order_custom_report` |
| **Version** | 0.1 |
| **Category** | Customizations |
| **License** | LGPL-3 |
| **Dependencies** | `base`, `purchase`, `bom_based_inventory`, `sale_custom_report` |

### Purpose

This module provides a custom Burgtec-branded PDF report for purchase orders. It replaces the standard Odoo purchase order report with a professionally formatted document that includes Burgtec company branding, contact information, and displays order lines with group codes and section subtotals.

---

## Directory Structure

```
purchase_order_custom_report/
├── __init__.py
├── __manifest__.py
├── DEVELOPER.md
└── report/
    ├── __init__.py
    ├── purchase_burgtec_report.py
    └── purchase_burgtec_report.xml
```

---

## Reports

### Report Class

**File:** `report/purchase_burgtec_report.py`

**Model Name:** `report.purchase_order_custom_report.burgtec_purchase_report`

```python
class PurchaseBurgtecReport(models.AbstractModel):
    _name = 'report.purchase_order_custom_report.burgtec_purchase_report'
```

#### `_get_report_values` Method

A simple report values method that provides the basic context for the QWeb template.

**Return Values:**

| Key | Type | Description |
|-----|------|-------------|
| `doc_ids` | list | Document IDs |
| `doc_model` | str | `'sale.order'` (note: should be `'purchase.order'`) |
| `company` | record | Current company |
| `docs` | recordset | Purchase order records |

---

### Report Template

**File:** `report/purchase_burgtec_report.xml`

**Template ID:** `burgtec_purchase_report`

#### Template Structure

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER                                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ burgtec.                                                 │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ 10A Corella Close, Berkeley Vale NSW 2261                   │
│ estimating@burgtec.com                                      │
│ 1800 287 483                                                │
│ ABN: 95 639 808 754                                         │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────┐  ┌─────────────────────┐           │
│ │ Shipping address    │  │ Vendor              │           │
│ │ [dest_address_id]   │  │ [partner_id]        │           │
│ └─────────────────────┘  └─────────────────────┘           │
├─────────────────────────────────────────────────────────────┤
│ Request for Quotation # / Purchase Order # / Cancelled PO # │
│ [burgtec_purchase_reference]                                │
├─────────────────────────────────────────────────────────────┤
│ Buyer: [user_id]    Your Order Ref: [partner_ref]          │
│ Creation Date: [create_date]    Expected Arrival: [date_planned] │
├─────────────────────────────────────────────────────────────┤
│ ORDER LINES TABLE                                           │
│ ┌───────┬──────┬─────────────┬──────┬─────┬──────┬───────┐ │
│ │G.Code │ Code │Product Name │ Note │ Qty │U.Cost│ Amount│ │
│ ├───────┼──────┼─────────────┼──────┼─────┼──────┼───────┤ │
│ │ SECTION HEADER (colspan)                               │ │
│ ├───────┼──────┼─────────────┼──────┼─────┼──────┼───────┤ │
│ │[sect] │[code]│[name]       │[note]│[qty]│[price]│[sub] │ │
│ ├───────┴──────┴─────────────┴──────┴─────┴──────┴───────┤ │
│ │                               Subtotal: [section_total]│ │
│ └────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ TOTALS                                                      │
│                              Untaxed Amount: [amount]       │
│                              Taxes: [tax]                   │
│                              Total: [total]                 │
└─────────────────────────────────────────────────────────────┘
```

#### Company Information (Hardcoded)

| Field | Value |
|-------|-------|
| Address | 10A Corella Close, Berkeley Vale NSW 2261 |
| Email | estimating@burgtec.com |
| Phone | 1800 287 483 |
| ABN | 95 639 808 754 |

#### Dynamic Title Based on State

| PO State | Title |
|----------|-------|
| `draft`, `sent`, `to approve` | Request for Quotation # |
| `purchase`, `done` | Purchase Order # |
| `cancel` | Cancelled Purchase Order # |

#### Table Columns

| Column | Field | Alignment |
|--------|-------|-----------|
| G.Code | `line.line_section_name` or `line.line_section_name_child` | Left |
| Code | `line.product_id.default_code` | Left |
| Product Name | `line.product_id.name` | Left |
| Note | `line.note` | Left |
| Qty | `line.product_qty` + `line.product_uom.name` | Right |
| Unit Cost | `line.price_unit` | Right |
| Taxes | Tax names joined by comma | Right |
| Amount | `line.price_subtotal` | Right |

#### Section and Note Handling

- **Sections (`line_section`):** Displayed as bold, full-width row spanning all columns
- **Notes (`line_note`):** Displayed as italic, full-width row
- **Section Subtotals:** Automatically calculated and displayed after each section

#### Paper Format

**Record ID:** `paperformat_burgtec_purchase_report`

| Property | Value |
|----------|-------|
| Format | A4 |
| Orientation | Portrait |
| Margin Top | 10mm |
| Margin Bottom | 0mm |
| Margin Left | 5mm |
| Margin Right | 5mm |
| DPI | 90 |
| Header Line | False |
| Header Spacing | 0 |

#### Report Action

**Record ID:** `action_burgtec_purchase_report`

| Property | Value |
|----------|-------|
| Name | Purchase Order Report |
| Model | `purchase.order` |
| Report Type | qweb-pdf |
| Binding Model | `purchase.model_purchase_order` |
| Binding Type | report |

**Dynamic PDF Filename:**
```python
(object.state in ('draft', 'sent') and 'Request for Quotation - %s' % (object.burgtec_purchase_reference) or 'Purchase Order - %s' % (object.burgtec_purchase_reference))
```

---

## Dependencies on Other Modules

### From `bom_based_inventory`

- PO line fields used in report

### From `sale_custom_report`

- `line_section_name` field on `purchase.order.line` (related from sale order line)
- `line_section_name_child` field on `purchase.order.line`

### From `quotation_type_customization` (indirect)

- `burgtec_purchase_reference` field on `purchase.order`

---

## Usage

### Generating the Report

1. Navigate to **Purchase > Orders > Purchase Orders**
2. Open any purchase order
3. Click **Print** menu
4. Select **Purchase Order Report**
5. PDF will download with:
   - Burgtec branding and contact info
   - Shipping address and vendor details
   - Dynamic title based on PO state
   - Order lines with group codes
   - Section subtotals
   - Tax breakdown and totals

### Report Visibility

The report appears in the Print menu for all purchase orders regardless of state.

---

## Template Features

### Language Support

The template sets the partner's language for proper localization:

```xml
<t t-set="o" t-value="o.with_context(lang=o.partner_id.lang)"/>
```

### Address Formatting

Uses Odoo's contact widget for consistent address display:

```xml
<span t-field="o.partner_id"
      t-options='{"widget": "contact", "fields": ["address", "name", "phone", "vat"], "no_marker": True, "phone_icons": True}'/>
```

### Date Formatting

Dates are formatted using context timestamp:

```xml
<p t-out="context_timestamp(o.create_date).strftime('%d %b %Y')"/>
```

### Currency Display

Monetary values use currency widget:

```xml
<span t-field="line.price_subtotal"
      t-options='{"widget": "monetary", "display_currency": o.currency_id}'/>
```

### Tax Totals

Uses standard Odoo purchase tax totals template:

```xml
<t t-call="purchase.document_tax_totals">
    <t t-set="tax_totals" t-value="o.tax_totals"/>
    <t t-set="currency" t-value="o.currency_id"/>
</t>
```

---

## Extending the Module

### Adding New Columns

1. Edit `report/purchase_burgtec_report.xml`
2. Add new `<th>` in table header
3. Add new `<td>` in the product line row (inside `<t t-if="not line.display_type">`)

Example:
```xml
<th name="th_new_column" class="text-start">
    <strong>New Column</strong>
</th>

<!-- In tbody -->
<td class="text-start">
    <span t-field="line.new_field"/>
</td>
```

### Modifying Company Information

The company details are currently hardcoded in the template. To make them dynamic:

1. Replace hardcoded values with company fields:
```xml
<span t-field="company.street"/>
<span t-field="company.email"/>
<span t-field="company.phone"/>
<span t-field="company.vat"/>
```

### Changing Paper Format

Edit the `paperformat_burgtec_purchase_report` record in the XML file to adjust margins, orientation, or page size.

---

## Technical Notes

### Section Subtotal Logic

The template tracks a running subtotal for each section:

```xml
<t t-set="current_subtotal" t-value="0"/>
<!-- For each line -->
<t t-set="current_subtotal" t-value="current_subtotal + line.price_subtotal"/>

<!-- When section ends (next line is section or last line) -->
<t t-if="current_section and (line_last or o.order_line[line_index+1].display_type == 'line_section')">
    <!-- Display subtotal -->
</t>

<!-- Reset on new section -->
<t t-set="current_subtotal" t-value="0"/>
```

### Display Type Classes

| Display Type | CSS Classes |
|--------------|-------------|
| `line_section` | `fw-bold o_line_section` |
| `line_note` | `fst-italic o_line_note` |
| (product) | (none) |

---

## Known Issues

1. **Doc Model Mismatch:** In `purchase_burgtec_report.py`, the `doc_model` is set to `'sale.order'` but should be `'purchase.order'`. This doesn't affect functionality as the docs recordset is correctly populated, but it's semantically incorrect.

---

## File Reference

| File | Purpose |
|------|---------|
| `__init__.py` | Module initialization, imports report package |
| `__manifest__.py` | Module metadata and dependencies |
| `report/__init__.py` | Report package initialization |
| `report/purchase_burgtec_report.py` | Report abstract model class |
| `report/purchase_burgtec_report.xml` | QWeb template, paper format, report action |