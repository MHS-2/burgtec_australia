# Burgtec HubSpot Customization - Developer Documentation

## Module Overview

| Property | Value |
|----------|-------|
| **Technical Name** | `burgtec_hubspot_customization` |
| **Version** | 18.0.1.0.0 |
| **Category** | Customizations |
| **License** | LGPL-3 |
| **Dependencies** | `base`, `sale`, `sale_custom_report`, `purchase` |

This module integrates HubSpot ticket data with Odoo, enabling synchronization of HubSpot tickets and linking them to Sale Orders and Purchase Orders for dispatch scheduling purposes.

---

## Architecture

```
burgtec_hubspot_customization/
├── __init__.py
├── __manifest__.py
├── controller/
│   ├── __init__.py
│   └── main.py                    # Webhook controller for HubSpot events
├── data/
│   └── ir_action_data.xml         # Server actions definitions
├── models/
│   ├── __init__.py
│   ├── hubspot_ticket_data.py     # Core HubSpot ticket model
│   ├── sale_order_ext.py          # Sale order extension
│   ├── purchase_order_ext.py      # Purchase order extension
│   └── res_config_settings.py     # Configuration settings
├── security/
│   └── ir.model.access.csv        # Access control rules
└── views/
    ├── hubspot_ticket_data.xml    # Ticket views and menu
    ├── sale_order_ext.xml         # Sale order form extension
    ├── purchase_order_ext.xml     # Purchase order form extension
    └── res_config_settings_views.xml  # Settings view
```

---

## Models

### 1. `hubspot.ticket.data`

**File:** `models/hubspot_ticket_data.py`

The core model for storing HubSpot ticket information synchronized from HubSpot CRM.

#### Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `hubspot_ticket_id` | `Char` | Unique HubSpot ticket ID (required, indexed) |
| `subject` | `Char` | Ticket subject from HubSpot (required) |
| `delivery_stage_number` | `Char` | Delivery stage number for matching with Sale Orders |
| `due_date` | `Date` | Ticket due date |
| `last_po_date_due` | `Date` | Last PO date due |
| `hs_last_closed_date` | `Date` | Last closed date from HubSpot |
| `scheduled_dispatch` | `Datetime` | Scheduled dispatch date/time |

#### SQL Constraints

- `hubspot_ticket_id_unique`: Ensures HubSpot Ticket ID is unique across all records

#### Key Methods

##### `_get_hubspot_config()`
Retrieves HubSpot API configuration from system parameters.

**Returns:** `tuple(base_url, token)`

**Raises:** `UserError` if configuration is missing

##### `_parse_date(date_string)`
Parses date strings from HubSpot API responses.

**Parameters:**
- `date_string`: Date string in various formats

**Returns:** `date` object or `False` if parsing fails

##### `sync_all_hubspot_tickets()`
Main synchronization method that fetches all tickets from HubSpot API and creates/updates them in Odoo.

**Features:**
- Paginated API calls (100 tickets per page)
- Savepoint-based transaction handling for error recovery
- Returns notification action with sync results

**Returns:** `dict` - `ir.actions.client` notification action

**Example Response:**
```python
{
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'HubSpot Sync Complete',
        'message': 'Created: 10, Updated: 5, Errors: 0',
        'type': 'success',
        'sticky': False,
    }
}
```

##### `_process_ticket(ticket_data)`
Processes a single ticket from HubSpot API response.

**Parameters:**
- `ticket_data`: Dictionary containing ticket data from HubSpot

**Returns:** `'created'` or `'updated'`

---

### 2. `sale.order` (Extension)

**File:** `models/sale_order_ext.py`

Extends the Sale Order model to link HubSpot tickets.

#### Additional Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `hubspot_ticket_id` | `Many2one` | Reference to `hubspot.ticket.data` |
| `hubspot_ticket_schedule_dispatch` | `Datetime` | Cached dispatch date from linked ticket |

#### Key Methods

##### `onchange_ticket_id()`
Triggered when `hubspot_ticket_id` changes. Automatically populates `hubspot_ticket_schedule_dispatch` from the selected ticket.

##### `action_attach_hubspot_ticket_and_dispatch_date()`
Server action method to attach HubSpot ticket to a single delivery stage quote.

**Business Logic:**
1. Validates quote type is `delivery_stage`
2. Determines stage value from `burgtec_quote_reference` or `delivery_stage` field
3. Searches for matching HubSpot ticket by `delivery_stage_number`
4. Updates quote with ticket reference and dispatch date

**Returns:** Notification action (success or warning)

##### `action_attach_hubspot_ticket_and_dispatch_date_to_all_delivery_quotes()`
Bulk action to attach tickets to multiple delivery stage quotes. Same logic as single action but without return notifications.

---

### 3. `purchase.order` (Extension)

**File:** `models/purchase_order_ext.py`

Extends the Purchase Order model to track HubSpot dispatch dates.

#### Additional Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `hubspot_dispatch_date` | `Datetime` | HubSpot dispatch date for the PO |
| `dispatch_arrival_mismatch` | `Boolean` | Computed field indicating date conflict |

#### Computed Fields

##### `_compute_dispatch_arrival_mismatch()`
Compares `hubspot_dispatch_date` with `date_planned` to detect scheduling conflicts.

**Returns:** `True` if dispatch date is earlier than planned arrival date

#### Key Methods

##### `action_assign_dispatch_date_to_parent_and_child_pos()`
Propagates dispatch date from linked Sale Order to Purchase Order and its child POs.

**Flow:**
1. Gets linked Sale Orders via `_get_sale_orders()`
2. Assigns `hubspot_ticket_schedule_dispatch` to `hubspot_dispatch_date`
3. Finds child POs through picking records
4. Updates all child POs with the same dispatch date

---

### 4. `res.config.settings` (Extension)

**File:** `models/res_config_settings.py`

Extends configuration settings to include HubSpot API credentials.

#### Configuration Parameters

| Field Name | Config Parameter Key | Description |
|------------|---------------------|-------------|
| `hubspot_integrations_token` | `burgtec_hubspot_customization.hubspot_integrations_token` | HubSpot API bearer token |
| `hubspot_base_url` | `burgtec_hubspot_customization.hubspot_base_url` | HubSpot API base URL |

---

## Controllers

### `HubspotController`

**File:** `controller/main.py`

HTTP controller for handling HubSpot webhook events.

#### Endpoints

##### `POST /hubspot_ticket_webhook`

Webhook endpoint for HubSpot ticket events.

**Authentication:** Public (no auth required)
**CSRF:** Disabled
**Methods:** GET, POST

**Supported Events:**
- `ticket.creation` - New ticket created in HubSpot
- `ticket.propertyChange` - Existing ticket properties updated

**Webhook Payload Example:**
```json
[
    {
        "subscriptionType": "ticket.creation",
        "objectId": "12345678"
    }
]
```

**Processing Flow:**
1. Receives webhook POST from HubSpot
2. Extracts ticket ID from payload
3. Fetches full ticket data from HubSpot API
4. Creates or updates `hubspot.ticket.data` record

---

## Server Actions

Defined in `data/ir_action_data.xml`:

### Active Actions

| ID | Name | Model | Binding | Description |
|----|------|-------|---------|-------------|
| `action_server_sync_hubspot_tickets` | Sync HubSpot Tickets | `hubspot.ticket.data` | List view | Triggers full sync of all HubSpot tickets |
| `action_attach_hubspot_ticket_and_dispatch_date` | Attach Hubspot Ticket and Dispatch date | `sale.order` | Form view | Links HubSpot ticket to delivery stage |

### Disabled Actions (Commented Out)

- `action_attach_hubspot_ticket_and_dispatch_date_to_all_delivery_quotes` - Bulk ticket attachment
- `action_assign_dispatch_date_to_parent_and_child_pos` - PO dispatch date propagation

---

## Views

### HubSpot Ticket Views

**List View** (`view_hubspot_ticket_list`)
- Read-only list of synchronized tickets
- Create disabled
- Columns: Ticket ID, Delivery Stage, Subject, Dispatch Date, Due Date, Last PO Date, Closed Date

**Form View** (`view_hubspot_ticket_form`)
- Read-only form for ticket details
- Create and edit disabled

**Search View** (`view_hubspot_ticket_search`)
- Searchable by: Ticket ID, Delivery Stage Number, Subject

### Sale Order Extension

Adds fields to `project_rev_details` group:
- `hubspot_ticket_id` - Visible only for delivery stages
- `hubspot_ticket_schedule_dispatch` - Visible only for delivery stages

### Purchase Order Extension

**Form View:**
- Adds `hubspot_dispatch_date` field before `picking_type_id`
- Shows warning banner when `dispatch_arrival_mismatch` is True

**List View:**
- Adds `hubspot_dispatch_date` column (optional by default)
- Makes `date_planned` optional

---

## Security

### Access Control (`ir.model.access.csv`)

| Model | Read | Write | Create | Delete | Groups |
|-------|------|-------|--------|--------|--------|
| `hubspot.ticket.data` | Yes | Yes | Yes | Yes | All users |

**Note:** Currently grants full access to all users. Consider restricting to specific groups in production.

---

## Configuration

### Required Setup

1. Navigate to **Sales > Configuration > Settings**
2. Locate **Hubspot Configuration** section
3. Configure:
   - **HubSpot Base URL**: e.g., `https://api.hubapi.com`
   - **HubSpot Integration Token**: Your HubSpot private app token

### HubSpot Webhook Setup

1. In HubSpot, create a webhook subscription
2. Point to: `https://your-odoo-domain/hubspot_ticket_webhook`
3. Subscribe to events:
   - `ticket.creation`
   - `ticket.propertyChange`

---

## API Integration

### HubSpot API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/crm/v3/objects/tickets` | GET | Fetch all tickets (with pagination) |
| `/crm/v3/objects/tickets/{id}` | GET | Fetch single ticket by ID |

### Properties Synced

- `subject`
- `delivery_stage_number`
- `due_date`
- `last_po_date_due`
- `hs_last_closed_date`
- `scheduled_dispatch`

---

## Data Flow Diagrams

### Ticket Synchronization Flow

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  HubSpot    │────▶│ Webhook/Manual   │────▶│ hubspot.ticket.data │
│  CRM        │     │ Sync             │     │ (Odoo)              │
└─────────────┘     └──────────────────┘     └─────────────────────┘
```

### Sale Order to Purchase Order Flow

```
┌─────────────────────┐     ┌────────────────┐     ┌─────────────────┐
│ hubspot.ticket.data │────▶│  sale.order    │────▶│ purchase.order  │
│ (scheduled_dispatch)│     │ (ticket_ref)   │     │ (dispatch_date) │
└─────────────────────┘     └────────────────┘     └─────────────────┘
                                                           │
                                                           ▼
                                                   ┌─────────────────┐
                                                   │ Child POs       │
                                                   │ (dispatch_date) │
                                                   └─────────────────┘
```

---

## Extending This Module

### Adding New HubSpot Properties

1. Add field to `hubspot.ticket.data` model
2. Add property name to `properties` list in:
   - `sync_all_hubspot_tickets()` method
   - `hubspot_ticket_webhook()` controller
3. Add field to `_process_ticket()` parsing logic
4. Update views as needed

### Adding New Webhook Events

1. Add event type check in `hubspot_ticket_webhook()` controller
2. Implement handler logic for the new event type

---

## Troubleshooting

### Common Issues

**Issue:** Sync fails with "HubSpot configuration is missing"
**Solution:** Configure API token and base URL in Sales Settings

**Issue:** Webhook not receiving events
**Solution:**
- Verify webhook URL is publicly accessible
- Check HubSpot webhook subscription is active
- Ensure HTTPS is configured

**Issue:** Date parsing errors in logs
**Solution:** HubSpot date format may have changed. Check `_parse_date()` method

### Logging

The module logs to:
- `hubspot_ticket_data` logger - Sync operations
- `main` controller logger - Webhook events

Enable debug logging:
```python
_logger.setLevel(logging.DEBUG)
```

---

## Dependencies on External Modules

This module depends on fields/features from `sale_custom_report`:
- `quote_type` field on `sale.order`
- `burgtec_quote_reference` field on `sale.order`
- `delivery_stage` field on `sale.order`
- `is_old_data` field on `sale.order`

Ensure `sale_custom_report` is installed and properly configured.

---

## Changelog

### Version 18.0.1.0.0
- Initial release
- HubSpot ticket synchronization
- Sale Order integration
- Purchase Order dispatch date tracking
- Webhook support for real-time updates