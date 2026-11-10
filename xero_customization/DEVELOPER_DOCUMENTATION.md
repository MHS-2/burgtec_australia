
# Xero Customization Module - Developer Documentation

## Overview

The **xero_customization** module extends Odoo's integration with Xero accounting software, providing bidirectional synchronization for purchase orders, invoices, and contacts.

**Version:** 0.1
**License:** LGPL-3
**Dependencies:** `base`, `sync_xero_connector`, `bom_based_inventory`

---

## Module Structure

```
xero_customization/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── purchase_order_ext.py      # PO export to Xero
│   ├── account_move_ext.py        # Invoice export to Xero
│   ├── xero_account_ext.py        # Scheduled imports
│   └── res_partner.py             # Contact import with overwrite
├── views/
│   └── product_view_ext.xml       # Makes SKU field optional
└── data/
    └── data.xml                   # Cron job for contact import
```

---

## Models

### 1. PurchaseOrderExt (`purchase.order`)

**File:** `models/purchase_order_ext.py`

#### Method: `export_purchase_order()`

Exports purchase orders from Odoo to Xero.

| Parameter | Type | Description |
|-----------|------|-------------|
| `po_list` | recordset | Purchase orders to export |
| `xero` | object | Xero API connection |
| `last_export_date` | datetime | Filter for updated records |
| `xero_account_id` | int | Xero account ID |
| `company` | recordset | Company record |
| `disable_export` | bool | Skip export if True |

**Key Features:**
- Batches requests (50 per batch)
- Rate limiting (sleeps after 30 API calls)
- Maps PO states: `draft` → DRAFT, `purchase/done` → AUTHORISED, `cancel` → DELETED
- Exports line items with taxes, discounts, quantities
- Tracks `xero_po_id` and `xero_po_number` on records

**Status Mapping:**

| Odoo State | Xero Status |
|------------|-------------|
| draft | DRAFT |
| purchase, done | AUTHORISED |
| (fully invoiced) | BILLED |
| cancel | DELETED |

---

### 2. AccountMoveExt (`account.move`)

**File:** `models/account_move_ext.py`

#### Method: `export_invoice()`

Exports customer invoices and vendor bills to Xero.

| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_list` | recordset | Invoices to export |
| `xero` | object | Xero API connection |
| `last_export_date` | datetime | Filter for updated records |
| `xero_account_id` | int | Xero account ID |
| `company` | recordset | Company record |
| `disable_export` | bool | Skip export if True |

**Key Features:**
- Handles both `ACCREC` (customer invoices) and `ACCPAY` (vendor bills)
- Multi-currency support with exchange rate calculation
- Exports discounts for customer invoices
- Tracks `xero_invoice_id` and `xero_invoice_number`

**Invoice Type Mapping:**

| Odoo Type | Xero Type |
|-----------|-----------|
| out_invoice, out_refund | ACCREC |
| in_invoice, in_refund | ACCPAY |

---

### 3. XeroAccountExt (`xero.account`)

**File:** `models/xero_account_ext.py`

#### Method: `automatic_import()` (scheduled)

Runs scheduled imports for invoices and contacts from all active Xero accounts.

#### Method: `automatic_import_contacts()` (scheduled)

Runs scheduled contact-only imports from Xero.

#### Method: `import_contact_overwrite()`

Imports contacts with pagination support.

**Import Options:**

| Option | Behavior |
|--------|----------|
| `create` | Import only new contacts |
| `update` | Import only updates to existing |
| `both` | Import new and updates |

---

### 4. ResPartner (`res.partner`)

**File:** `models/res_partner.py`

#### Method: `import_contact_overwrite()`

Creates or updates partner records from Xero contacts.

| Parameter | Type | Description |
|-----------|------|-------------|
| `contact_list` | list | Xero contact data |
| `xero` | object | Xero API connection |
| `xero_account_id` | int | Xero account ID |
| `company` | recordset | Company record |
| `import_option` | str | 'create', 'update', or 'both' |

**Field Mapping:**

| Xero Field | Odoo Field |
|------------|------------|
| ContactID | xero_contact_id (via M2M) |
| Name | name |
| FirstName | first_name |
| LastName | last_name |
| EmailAddress | email |
| Phones[DEFAULT] | phone |
| Phones[MOBILE] | mobile |
| Phones[DDI] | direct_dial |
| TaxNumber | vat |
| Website | website |
| Addresses | street, street2, city, zip, state_id, country_id |
| ContactPersons | child contact records |
| ContactGroups | category_id |

---

## Key Fields Added

### Purchase Order

| Field | Type | Description |
|-------|------|-------------|
| `xero_po_id` | Char | Xero Purchase Order ID |
| `xero_po_number` | Char | Xero PO Reference |
| `burgtec_purchase_reference` | Char | Custom reference |

### Account Move (Invoice)

| Field | Type | Description |
|-------|------|-------------|
| `xero_invoice_id` | Char | Xero Invoice ID |
| `xero_invoice_number` | Char | Xero Invoice Number |
| `able_to_xero_export` | Boolean | Export eligibility flag |

### Partner

| Field | Type | Description |
|-------|------|-------------|
| `contact_xero_company_ids` | M2M | Company-specific Xero mappings |
| `first_name` | Char | First name |
| `last_name` | Char | Last name |
| `direct_dial` | Char | DDI phone number |
| `attention_to` | Char | Attention field |

---

## Scheduled Jobs

### Automatic Import Contacts

**XML ID:** `ir_cron_automatic_import_data_contacts`
**Model:** `xero.account`
**Method:** `automatic_import_contacts()`
**Interval:** Daily
**Status:** Inactive by default

To enable:
```python
self.env.ref('xero_customization.ir_cron_automatic_import_data_contacts').active = True
```

---

## Data Flow

### Export Flow (Odoo → Xero)

```
Record Updated
    ↓
Validation (partner required)
    ↓
Auto-export dependencies (products/contacts)
    ↓
Map to Xero format
    ↓
Batch (50 items) + Rate limit (30 calls)
    ↓
Update Odoo with Xero IDs
    ↓
Log errors to mismatch.log
```

### Import Flow (Xero → Odoo)

```
Cron Trigger
    ↓
Paginate Xero contacts
    ↓
Filter by import_option
    ↓
Create/Update partners
    ↓
Create child contacts & addresses
    ↓
Log errors to mismatch.log
```

---

## Error Handling

All sync errors are logged to `mismatch.log` model with details about:
- Missing partners
- Missing countries/states
- Xero API validation errors
- Tax configuration issues

---

## Multi-Company Support

Contact and product mappings are company-specific via M2M relations:
- `contact_xero_company_ids` - stores `xero_contact_id` per company
- `product_xero_company_ids` - stores `xero_item_id` per company

---

## View Customizations

The module makes the `default_code` (SKU) field optional on product forms, allowing products to sync without requiring a product code.

---

## Usage Examples

### Manually trigger contact import

```python
xero_account = self.env['xero.account'].browse(1)
xero_account.import_contact_overwrite()
```

### Check export eligibility

```python
invoice = self.env['account.move'].browse(123)
if invoice.able_to_xero_export and invoice.partner_id:
    # Ready for export
```

---

This documentation covers the core functionality. For the parent `sync_xero_connector` module API details, refer to that module's documentation.