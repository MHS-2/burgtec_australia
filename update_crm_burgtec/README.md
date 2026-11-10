# Update CRM Burgtec

A comprehensive Odoo 18 CRM customization module that provides bi-directional integration between HubSpot and Odoo's CRM system.

## Overview

This module extends Odoo's CRM functionality to manage HubSpot deals, enabling seamless synchronization of deal data, sales order workflows, and delivery stage planning between the two platforms.

## Features

- **Bi-directional HubSpot Sync**: Import deals from HubSpot and export CRM leads back
- **Deal Number Management**: Auto-generate unique 6-digit deal numbers with duplicate validation
- **Metadata Synchronization**: Sync deal stages, types, territories, and pipeline stages
- **Sales Order Integration**: Link sales orders to CRM deals via deal number reference
- **Delivery Stage Planning**: Create delivery stage quotations with BOM components
- **Gross Profit Tracking**: Track quoted GP value and percentage per deal

## Dependencies

```
base
crm
sale_crm
sale_custom_report
quotation_type_customization
burgtec_hubspot_customization
contacts
sales_team
```

## Installation

1. Ensure all dependencies are installed
2. Copy this module to your Odoo addons directory
3. Update the apps list: `Settings > Apps > Update Apps List`
4. Install the module: Search for "update_crm_burgtec" and click Install

## Configuration

### HubSpot API Setup

Configure the following system parameters in `Settings > Technical > System Parameters`:

| Key | Description |
|-----|-------------|
| `burgtec_hubspot_customization.hubspot_integrations_token` | Your HubSpot Bearer token |
| `burgtec_hubspot_customization.hubspot_base_url` | HubSpot API base URL (e.g., `https://api.hubapi.com`) |

### Menu Access

After installation, configure HubSpot metadata via:

`CRM > Configuration > HubSpot Deals`

- **Deal Stage**: Manage deal stages with win probabilities
- **Deal Type**: Configure deal types (New Business, Expansion, etc.)
- **Territory/Location**: Set up project territories
- **Pipeline Stage**: Define pipeline stages

## Usage

### Importing Deals from HubSpot

1. Navigate to `CRM > Pipeline`
2. Click `Action > Fetch and Sync HubSpot Deals`
3. Deals are imported/updated automatically

### Exporting a Deal to HubSpot

1. Open a CRM Lead/Opportunity
2. Generate a deal number using the "Generate" button
3. Click "Export to HubSpot" button
4. The deal is created/updated in HubSpot

### Syncing Metadata

Use the Action menu on the CRM Pipeline view to sync:

- Deal Stages
- Deal Types
- Project Locations
- Pipeline Stages

### Linking Sale Orders to Deals

1. Navigate to `Sales > Quotations`
2. Select orders to link
3. Click `Action > Attach Sale Orders with Old CRM Lead`
4. Orders are linked via matching deal numbers

## Models

### New Models

| Model | Description |
|-------|-------------|
| `deal.stage` | HubSpot deal stages with probabilities |
| `deal.type` | Deal type classification |
| `deal.location` | Project territories/locations |
| `deal.pipeline.stage` | Pipeline stage information |

### Extended Models

| Model | Changes |
|-------|---------|
| `crm.lead` | HubSpot deal fields, sync methods, deal number generation |
| `res.partner` | HubSpot company ID tracking |
| `sale.order` | Deal linking, opportunity view action |
| `planning.screen` | Delivery stage creation with BOM components |

## CRM Lead Fields

| Field | Description |
|-------|-------------|
| `id_of_hubspot_deal` | HubSpot Deal ID |
| `odoo_deal_number_6digit` | 6-digit internal deal number |
| `deal_stage_id` | Current deal stage |
| `deal_type_id` | Type of deal |
| `deal_territory_id` | Project territory/location |
| `deal_pipeline_and_stage_id` | Pipeline stage |
| `deal_create_date` | Deal creation date from HubSpot |
| `deal_date_quoted` | First quotation date |
| `deal_quoted_gp_value` | Quoted Gross Profit value |
| `deal_quoted_gp_percentage` | Quoted Gross Profit percentage |
| `deal_probability` | Win probability (from stage) |
| `is_deal_imported` | Imported from HubSpot flag |
| `is_deal_exported` | Exported to HubSpot flag |
| `is_closed_won` | Deal won flag |
| `is_closed_lost` | Deal lost flag |

## API Methods

### CRM Lead

```python
# Sync all deals from HubSpot
self.env['crm.lead'].sync_deals_from_hubspot()

# Export single lead to HubSpot
lead.export_deal_in_hubspot()

# Import single deal from HubSpot
lead.import_deal_from_hubspot()

# Generate deal number
lead.action_generate_deal_number()

# Sync metadata
self.env['crm.lead'].fetch_hubspot_deals_stages_to_odoo()
self.env['crm.lead'].fetch_hubspot_deals_types_to_odoo()
self.env['crm.lead'].fetch_hubspot_deals_project_locations()
self.env['crm.lead'].fetch_hubspot_deals_pipeline_stage()
```

### Sale Order

```python
# Link orders to CRM leads by deal number
orders._attach_sale_orders_with_old_crm_lead()

# View related opportunity
order.action_view_opportunity()
```

## File Structure

```
update_crm_burgtec/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── crm_lead_ext.py
│   ├── deal_stage.py
│   ├── deal_type.py
│   ├── deal_pipeline_stage.py
│   ├── deal_territory_location.py
│   ├── res_partner_ext.py
│   ├── sale_order_ext.py
│   └── planning_screen_ext.py
├── views/
│   ├── crm_lead_view_extended.xml
│   ├── deal_stage_views.xml
│   ├── deal_type_views.xml
│   ├── deal_pipeline_stage_views.xml
│   ├── deal_location_views.xml
│   ├── res_partner_ext.xml
│   └── sale_order_view_extended.xml
├── data/
│   └── ir_action_data.xml
└── security/
    └── ir.model.access.csv
```

## Troubleshooting

### Common Issues

**Sync fails with authentication error**
- Verify the HubSpot token in system parameters
- Ensure the token has required scopes (deals, companies, owners)

**Duplicate deal number error**
- The deal number already exists in HubSpot
- Use the "Generate" button to get a new unique number

**Deals not appearing after sync**
- Check the Odoo logs for specific error messages
- Verify the HubSpot base URL is correct
- Ensure the HubSpot account has deals to sync

**Sale orders not linking**
- Verify the `burgtec_quote_reference` matches `odoo_deal_number_6digit`
- Run the "Attach Sale Orders" action from the Action menu

### Logging

Enable debug logging to troubleshoot sync issues:

```python
import logging
_logger = logging.getLogger(__name__)
```

All sync operations log to the `update_crm_burgtec` logger.

## Security

### Access Rights

All users have full access to:
- `deal.stage`
- `deal.type`
- `deal.location`
- `deal.pipeline.stage`

Salesperson group has read-only access to `res.partner`.

### Data Protection

- HubSpot tokens are stored in system parameters (admin access only)
- Deal sync operations are logged for audit purposes
- Duplicate validation prevents data inconsistency

## Extending the Module

### Adding New HubSpot Properties

1. Add field to `crm.lead` in `models/crm_lead_ext.py`
2. Map the property in `sync_deals_from_hubspot()` method
3. Include in export payload in `export_deal_in_hubspot()`
4. Add field to view in `views/crm_lead_view_extended.xml`

### Adding New Metadata Types

1. Create new model file in `models/`
2. Add Many2one field to `crm.lead`
3. Create fetch method in `crm.lead`
4. Add server action in `data/ir_action_data.xml`
5. Create views in `views/`
6. Add access control in `security/ir.model.access.csv`
7. Update `__manifest__.py` with new files

## Version History

| Version | Changes |
|---------|---------|
| 0.1 | Initial release |

## License

LGPL-3

## Support

For issues and feature requests, contact the development team.