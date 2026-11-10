# Burgtec Website Customization

**Version:** 18.0.1.0.0
**Category:** Website/Customization
**License:** LGPL-3

## Overview

This module provides comprehensive website customization for Burgtec, transforming Odoo's standard product configurator into a sophisticated e-commerce system. It enables hierarchical product configuration, rich API endpoints, zone-based logistics, and advanced product bundling capabilities.

## Dependencies

- `base`
- `web`
- `website`
- `stock`
- `product`
- `website_sale`
- `sale_custom_report`
- `m2m_attachment_carousel_view`

## Module Structure

```
burgtec_website_customization/
├── __init__.py
├── __manifest__.py
├── controller/
│   ├── __init__.py
│   ├── main.py                    # API controllers
│   └── product_configurator.py    # Product configurator endpoints
├── models/
│   ├── __init__.py
│   ├── product_template_ext.py
│   ├── product_product_ext.py
│   ├── sub_attribute.py
│   ├── sub_attribute_value_line.py
│   ├── sub_attribute_line.py
│   ├── product_template_attribute_value_ext.py
│   ├── preconfigured_attribute_line.py
│   ├── preconfigured_attribute_option.py
│   ├── website_product_category.py
│   ├── zone_postal_code.py
│   ├── optional_groups.py
│   ├── product_attribute.py
│   └── material_allocation.py
├── views/
│   ├── product_template_ext.xml
│   ├── product_product_ext.xml
│   ├── product_attribute_views.xml
│   ├── sub_attribute_view.xml
│   ├── sub_attribute_type_view.xml
│   ├── website_product_category_view.xml
│   ├── zone_postal_code_views.xml
│   ├── zone_postal_views.xml
│   ├── optional_groups_views.xml
│   ├── material_allocation_view.xml
│   └── preconfigured_attribute_option.xml
├── static/src/
│   ├── js/
│   │   └── burgtec_product_configurator_dialog.js
│   ├── scss/
│   │   └── product_configurator_dialog_fix.scss
│   └── xml/
│       └── product_template_attribute_line_ext.xml
├── security/
│   ├── ir.model.access.csv
│   └── ir_rules.xml
└── data/
    └── ir_action_data.xml
```

---

## Features

### 1. Enhanced Product Management

Extended product templates and variants with website-specific fields including:

- Custom website naming and categorization
- Publishing controls (`is_product_published`, `is_purchasable_online_template`)
- Modular product flags for configurable products
- Multi-attachment support (images, 3D models, documents, featured images)
- Comprehensive dimension fields (height, width, depth, seat dimensions, worktop dimensions)
- Website content fields (features, finishes, warranty, lead time, description)

### 2. Sub-Attributes System

A hierarchical attribute system that allows nested selections under standard product attributes.

**Components:**
- **Sub-Attribute Types** (`sub.attribute.type`): Categorize sub-attributes (e.g., Material, Color, Size)
- **Sub-Attributes** (`sub.attribute`): Define configurable options with display types
- **Sub-Attribute Value Lines** (`sub.attribute.value.line`): Individual values with pricing, colors, textures, and 3D properties
- **Sub-Attribute Lines** (`sub.attribute.line`): Link sub-attributes to product attribute values

**Display Types:**
- `radio` - Radio buttons
- `pills` - Pill-style buttons
- `select` - Dropdown select
- `color` - Color swatches
- `multi` - Multi-checkbox selection

### 3. Preconfigured Products

Pre-defined product configurations for quick selection.

**Components:**
- **Preconfigured Attribute Lines** (`preconfigured.attribute.line`): Store selected sub-attribute values
- **Preconfigured Attribute Options** (`preconfigured.attribute.option`): Named configuration sets with images
- **Preconfigured Option Lines** (`preconfigured.option.line`): Individual selections within an option

### 4. Optional Product Groups

Bundle related products for upselling and cross-selling.

**Components:**
- **Optional Groups** (`optional.groups`): Define product bundles with publishing controls
- **Optional Groups Lines** (`optional.groups.line`): Link groups to products

### 5. Zone-Based Pricing

Multi-zone delivery and installation cost management.

**Components:**
- **Zone Postal** (`zone.postal`): Define zones with postal codes and costs
- **Zone Postal Codes** (`zone.postal.code`): Individual postal code records

**Features:**
- Three delivery zones per configuration
- Separate delivery and installation costs per zone
- Change tracking via mail.thread integration

### 6. Material Allocation

Track material types across attribute values for manufacturing and inventory purposes.

### 7. Website Categories

Custom product categorization independent of standard Odoo categories, with hierarchical parent-child relationships.

---

## Models Reference

### Product Extensions

#### product.template (Extended)

| Field | Type | Description |
|-------|------|-------------|
| `api_template_product_name` | Char | Website product name |
| `api_template_default_code` | Char | Website product code |
| `api_template_list_price` | Float | Website list price |
| `api_template_taxes_id` | Many2many | Associated taxes |
| `api_template_categ_id` | Many2one | Standard category |
| `api_template_custom_categ_id` | Many2one | Website category |
| `api_template_image_attachment_ids` | Many2many | Product images |
| `api_template_three_d_attachment_ids` | Many2many | 3D model files |
| `api_template_docs_attachment_ids` | Many2many | Documentation files |
| `api_template_featured_attachment_ids` | Many2many | Featured images |
| `api_website_dimensions` | Text | Product dimensions |
| `api_website_features` | Text | Product features |
| `api_website_finishes` | Text | Available finishes |
| `api_website_warranty` | Text | Warranty information |
| `api_website_lead_time` | Text | Lead time info |
| `api_website_description` | Text | Website description |
| `api_website_product_origin` | Char | Product origin |
| `is_product_published` | Boolean | Publishing status |
| `is_modular_template_product` | Boolean | Modular product flag |
| `is_purchasable_online_template` | Boolean | Online purchase enabled |
| `optional_group_ids` | One2many | Optional product groups |

#### product.product (Extended)

| Field | Type | Description |
|-------|------|-------------|
| `api_variant_list_price` | Float | Variant list price |
| `api_variant_three_d_attachment_ids` | Many2many | Variant 3D models |
| `api_variant_featured_attachment_ids` | Many2many | Variant featured images |
| `is_preconfigured` | Boolean | Preconfigured variant flag |
| `preconfigured_attribute_line_ids` | One2many | Preconfigured attribute lines |
| `preconfigured_attribute_option_ids` | One2many | Preconfigured options |

### Sub-Attribute Models

#### sub.attribute

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Sub-attribute name |
| `display_type` | Selection | Display type (radio/pills/select/color/multi) |
| `sub_attribute_type_id` | Many2one | Category reference |
| `sub_attribute_value_line_ids` | One2many | Available values |

#### sub.attribute.value.line

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Display value |
| `html_color` | Char | Color code (hex) |
| `image` | Binary | Thumbnail image |
| `texture_image` | Binary | Texture image |
| `default_extra_price` | Float | Additional price |
| `metalness` | Float | 3D metalness property |
| `roughness` | Float | 3D roughness property |
| `lead_time` | Char | Lead time information |
| `is_default_website` | Boolean | Default selection flag |
| `sequence` | Integer | Display order |

#### sub.attribute.line

| Field | Type | Description |
|-------|------|-------------|
| `website_product_template_attribute_value_id` | Many2one | Parent attribute value |
| `sub_attribute_id` | Many2one | Sub-attribute reference |
| `sub_attribute_value_ids` | Many2many | Available sub-values |

### Zone Models

#### zone.postal

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Zone configuration name |
| `zone1_postal_code_ids` | Many2many | Zone 1 postal codes |
| `zone2_postal_code_ids` | Many2many | Zone 2 postal codes |
| `zone3_postal_code_ids` | Many2many | Zone 3 postal codes |
| `delivery_cost_zone_1/2/3` | Float | Delivery costs per zone |
| `installation_cost_zone_1/2/3` | Float | Installation costs per zone |

### Optional Groups

#### optional.groups

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Internal name |
| `website_name` | Char | Website display name |
| `is_publish` | Boolean | Publishing status |
| `product_ids` | Many2many | Products in group |

---

## API Endpoints

### GET /api/products/published/search

Returns comprehensive product data for published products.

**Authentication:** Public (JSON)

**Parameters:** Dynamic keyword arguments for filtering

**Response Structure:**
```json
{
  "status": "success",
  "count": 10,
  "data": [
    {
      "id": 1,
      "name": "Product Name",
      "image_url": "...",
      "default_code": "PROD001",
      "list_price": 100.00,
      "categories": {
        "parent": "...",
        "child": "..."
      },
      "attachments": {
        "images": [...],
        "featured": [...],
        "three_d": [...],
        "docs": [...]
      },
      "variants": [...],
      "sub_attributes": [...],
      "zone_postal_data": {...},
      "optional_groups_data": [...],
      "preconfigured_options": [...]
    }
  ]
}
```

### GET /api/products/published/type/<type>

Filter products by type (product/service/etc.).

**Authentication:** Public (JSON)

### POST /burgtec/product_configurator/get_values

Enhanced configurator data with nested sub-attributes.

**Authentication:** Public (JSON)

**Parameters:**
- `product_template_id` (required): Product template ID
- `quantity` (required): Quantity
- `currency_id` (required): Currency ID
- `so_date` (required): Sale order date
- `product_uom_id` (optional): Unit of measure
- `company_id` (optional): Company ID
- `pricelist_id` (optional): Pricelist ID
- `ptav_ids` (optional): Selected attribute value IDs
- `only_main_product` (optional): Exclude optional products

---

## JavaScript Components

### BurgtecProductConfiguratorDialog

Extends Odoo's `ProductConfiguratorDialog` with nested sub-attribute support.

**Props:**
- `use_burgtec` (Boolean): Enable Burgtec configurator mode
- `initialSubSelection` (Object): Pre-fill sub-attribute selections

**Key Methods:**
- `_loadData()`: Fetches data from Burgtec endpoint
- `_updateSubAttributeSelection()`: Manages sub-attribute selections
- `_recomputeProductDisplayName()`: Builds nested display names

**Display Name Format:**
```
"Chair (Black (White))"
      ^      ^
      |      |__ Sub-attribute selection
      |__ Parent attribute selection
```

---

## Security

### Access Rights

Full CRUD permissions for:
- `sub.attribute`
- `sub.attribute.value.line`
- `sub.attribute.line`
- `preconfigured.attribute.line`
- `preconfigured.attribute.option`
- `preconfigured.option.line`
- `website.product.category`
- `zone.postal`
- `zone.postal.code`
- `optional.groups`
- `optional.groups.line`
- `sub.attribute.type`
- `material.allocation`

Read-only for public users:
- `product.template`
- `product.product`
- `ir.attachment`

### Record Rules

Published products are filtered by `is_product_published=True` for public access.

---

## Workflows

### Product Configuration Workflow

1. Create product template with main attributes
2. Link product template attribute values to sub-attributes via `sub.attribute.line`
3. Define sub-attribute values with pricing, colors, and 3D properties
4. Frontend configurator loads nested structure via `/burgtec/product_configurator/get_values`
5. User selects parent attribute, sub-attributes appear dynamically
6. Display name auto-updates with nested selections

### Preconfigured Products Workflow

1. Mark variant as `is_preconfigured=True`
2. Preconfigured attribute lines auto-populate from variant's attributes
3. Create named preconfigured options
4. Each option groups specific sub-attribute selections
5. API returns all options with configurations
6. Website presents as quick-select buttons

### Optional Products Workflow

1. Create `optional.groups` with product selections
2. Link `optional.groups.line` to product template/variant
3. API returns `optional_groups_data` with group info
4. Website displays as upselling recommendations

### Zone-Based Pricing Workflow

1. Define `zone.postal` record with postal codes per zone
2. Set delivery and installation costs per zone
3. Assign delivery code selection to product
4. API includes zone pricing data
5. Website calculates shipping based on postal code

---

## Menu Locations

Sub-attributes, optional groups, and material allocations are accessible from:

- **Inventory** > Product Configuration > Sub Attributes / Optional Groups / Material Allocation
- **Sales** > Product Configuration > Sub Attributes / Optional Groups / Material Allocation
- **Purchase** > Product Configuration > Sub Attributes / Optional Groups / Material Allocation

Zone configuration is accessible from:
- **Sales** > Zone Postal
- **Inventory** > Zone Postal

---

## Server Actions

### Update Product Variant Images

**Action:** Update Image 1920 of Product Variant with Featured Attachment

**Model:** `product.product`

**Binding:** List view (multi-select)

**Method:** `action_update_product_product_image_1920()`

Batch updates variant images from their featured attachments.

---

## Authors

- Burgtec Development Team

## Maintainers

- Burgtec