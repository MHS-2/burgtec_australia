# Many2Many Attachments Carousel View - Developer Documentation

## Module Overview

| Property | Value |
|----------|-------|
| **Technical Name** | `m2m_attachment_carousel_view` |
| **Version** | 18.1 |
| **Category** | Uncategorized |
| **License** | LGPL-3 |
| **Dependencies** | `base`, `web`, `product` |
| **Application** | Yes |
| **Auto Install** | No |

### Purpose

This module provides a custom OWL field widget called `image_carousel` that displays Many2Many attachment fields as an interactive image carousel. It allows users to browse through multiple images with navigation arrows, thumbnail previews, and supports adding/deleting images directly from the widget.

---

## Directory Structure

```
m2m_attachment_carousel_view/
├── __init__.py
├── __manifest__.py
├── DEVELOPER.md
└── static/
    └── src/
        ├── css/
        │   └── image_carousel.css
        ├── js/
        │   └── m2m_attachment_carousel_view.js
        └── xml/
            └── image_carousel_template.xml
```

---

## Widget Implementation

### JavaScript Component

**File:** `static/src/js/m2m_attachment_carousel_view.js`

**Class:** `ImageCarouselWidget`

**Template:** `m2m_attachment_carousel_view.ImageCarouselWidget`

#### Component Registration

```javascript
registry.category("fields").add("image_carousel", imageCarouselWidget);
```

#### Supported Field Types

- `many2many` (specifically for `ir.attachment` records)

#### Component Properties

```javascript
static props = {
    ...standardFieldProps,
};
```

#### State Management

```javascript
this.state = useState({
    currentIndex: 0,  // Index of currently displayed image
});
```

#### Services Used

| Service | Purpose |
|---------|---------|
| `orm` | CRUD operations on `ir.attachment` |
| `notification` | Success/error toast notifications |

#### Refs

| Ref Name | Element | Purpose |
|----------|---------|---------|
| `fileInput` | `<input type="file">` | Hidden file input for image upload |

---

### Computed Getters

#### `images`

Transforms the Many2Many field data into an array of image objects.

```javascript
get images() {
    const value = this.props.record.data[this.props.name];
    if (!value || !value.records) {
        return [];
    }
    return value.records.map(record => ({
        id: record.resId,
        name: record.data.name || 'Image',
        url: `/web/image/${record.resId}`,
        datas: record.data.datas
    }));
}
```

**Returns:** Array of objects with `id`, `name`, `url`, `datas` properties.

#### `currentImage`

Returns the currently displayed image based on `currentIndex`.

```javascript
get currentImage() {
    return this.images[this.state.currentIndex] || null;
}
```

#### `hasImages`

Boolean indicating if there are any images to display.

```javascript
get hasImages() {
    return this.images.length > 0;
}
```

#### `isReadonly`

Boolean indicating if the field is in readonly mode.

```javascript
get isReadonly() {
    return this.props.readonly;
}
```

---

### Methods

#### Navigation Methods

| Method | Description |
|--------|-------------|
| `nextImage(ev)` | Increments `currentIndex` if not at last image |
| `prevImage(ev)` | Decrements `currentIndex` if not at first image |
| `goToImage(index, ev)` | Sets `currentIndex` to specified index (thumbnail click) |
| `openImageGallery(ev)` | Opens current image in new browser tab |

#### Upload Methods

##### `onAddImageClick(ev)`

Triggers the hidden file input click to open file picker.

##### `onFileChange(ev)`

Handles file selection and upload process:

1. Reads selected files
2. Converts each file to base64
3. Creates `ir.attachment` record via ORM
4. Links attachment to Many2Many field using command `[4, id]`
5. Shows success/error notification

**Attachment Creation:**
```javascript
const attachmentId = await this.orm.create("ir.attachment", [{
    name: file.name,
    datas: base64.split(',')[1],  // Strip data URI prefix
    res_model: this.props.record.resModel,
    res_id: this.props.record.resId,
    mimetype: file.type,
}]);
```

##### `fileToBase64(file)`

Utility method that converts a File object to base64 data URI using FileReader.

```javascript
fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}
```

#### Delete Method

##### `onDeleteImage(ev)`

Handles image deletion:

1. Shows confirmation dialog
2. Removes from Many2Many field using command `[3, id]`
3. Deletes the `ir.attachment` record
4. Adjusts `currentIndex` if needed
5. Shows success/error notification

---

### OWL Template

**File:** `static/src/xml/image_carousel_template.xml`

**Template Name:** `m2m_attachment_carousel_view.ImageCarouselWidget`

#### Template Structure

```
┌─────────────────────────────────────────────────────────────┐
│ .o_field_image_carousel                                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ <input type="file" hidden> (for uploads)                │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ IF hasImages:                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ .carousel-container                                      │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ .carousel-image-wrapper                              │ │ │
│ │ │ ┌─────────────────────────────────────────────────┐ │ │ │
│ │ │ │ <img> Main Image (click to open in new tab)     │ │ │ │
│ │ │ └─────────────────────────────────────────────────┘ │ │ │
│ │ │ [◀ Prev]                              [Next ▶]      │ │ │
│ │ │                              [+Add] [🗑Delete]       │ │ │
│ │ │                                    [1 / 5]          │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ .carousel-thumbnails                                 │ │ │
│ │ │ [thumb1] [thumb2] [thumb3] [thumb4] [thumb5]        │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ELSE (no images):                                           │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ .carousel-empty-state                                   │ │
│ │ "No images attached"                                    │ │
│ │ [+ Add Image] button                                    │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### Key Template Elements

| Element | Class | Purpose |
|---------|-------|---------|
| File Input | (hidden) | Multiple image file selection, accepts `image/*` |
| Main Image | `.carousel-main-image` | Displays current image, clickable to open full size |
| Prev Button | `.carousel-btn-prev` | Navigate to previous image |
| Next Button | `.carousel-btn-next` | Navigate to next image |
| Add Button | `.carousel-add-btn` | Trigger file upload (hidden in readonly) |
| Delete Button | `.carousel-delete-btn` | Delete current image (hidden in readonly) |
| Counter | `.carousel-counter` | Shows "X / Y" position indicator |
| Thumbnails | `.carousel-thumbnail` | Clickable thumbnail strip |

---

### CSS Styles

**File:** `static/src/css/image_carousel.css`

Uses SCSS-like nested syntax (processed by Odoo's asset pipeline).

#### Key Style Classes

| Class | Description |
|-------|-------------|
| `.o_field_image_carousel` | Root container |
| `.carousel-container` | Max-width 800px, centered |
| `.carousel-image-wrapper` | Relative positioned, rounded corners, overflow hidden |
| `.carousel-main-image` | 100% width, 400px height, `object-fit: contain` |
| `.carousel-btn` | Navigation buttons with semi-transparent black background |
| `.carousel-btn-prev` | Positioned left 10px |
| `.carousel-btn-next` | Positioned right 10px |
| `.carousel-counter` | Bottom-right position indicator |
| `.carousel-thumbnails` | Horizontal scrollable flex container |
| `.carousel-thumbnail` | 80x80px, border highlight on active/hover |
| `.carousel-empty-state` | Centered text with dashed border |

#### Color Scheme

| Element | Color |
|---------|-------|
| Thumbnail Hover | `#00a09d` (Teal) |
| Thumbnail Active | `#875a7b` (Odoo Purple) |
| Navigation Buttons | `rgba(0, 0, 0, 0.5)` → `rgba(0, 0, 0, 0.7)` on hover |
| Counter Background | `rgba(0, 0, 0, 0.7)` |

---

## Usage

### Field Definition (Python)

Add a Many2Many field to `ir.attachment` on your model:

```python
from odoo import models, fields

class MyModel(models.Model):
    _name = 'my.model'

    image_ids = fields.Many2many(
        'ir.attachment',
        string='Images',
    )
```

### View Definition (XML)

Use the `image_carousel` widget on the Many2Many field:

```xml
<field name="image_ids" widget="image_carousel"/>
```

#### Readonly Mode

```xml
<field name="image_ids" widget="image_carousel" readonly="1"/>
```

In readonly mode:
- Add and Delete buttons are hidden
- Users can still navigate and view images
- Clicking main image still opens in new tab

---

## Features

### Image Navigation

- **Arrow Buttons:** Previous/Next navigation (hidden at boundaries)
- **Thumbnail Click:** Direct navigation to specific image
- **Counter:** Shows current position (e.g., "3 / 7")

### Image Management (Edit Mode)

- **Add Images:** Click + button or "Add Image" in empty state
- **Multiple Upload:** File input accepts multiple files
- **Delete Images:** Click trash icon with confirmation dialog
- **Auto-link:** New attachments automatically linked to current record

### Image Viewing

- **Main Display:** 400px height, maintains aspect ratio
- **Thumbnail Strip:** Horizontal scrollable with custom scrollbar
- **Full Size:** Click main image to open in new browser tab

---

## Many2Many Field Commands Used

| Command | Syntax | Purpose |
|---------|--------|---------|
| Link | `[4, id]` | Add existing attachment to field |
| Unlink | `[3, id]` | Remove attachment from field (doesn't delete record) |

---

## Error Handling

### Upload Errors

```javascript
catch (error) {
    console.error("Error uploading image:", error);
    this.notification.add("Failed to upload image", {
        type: "danger",
    });
}
```

### Delete Errors

```javascript
catch (error) {
    console.error("Error deleting image:", error);
    this.notification.add("Failed to delete image", {
        type: "danger",
    });
}
```

---

## Extending the Widget

### Adding Custom Actions

1. Add method to `ImageCarouselWidget` class
2. Add button in template with `t-on-click` handler
3. Style button in CSS

### Customizing Image Display

Modify `.carousel-main-image` in CSS:

```css
.carousel-main-image {
    height: 300px;  /* Change height */
    object-fit: cover;  /* Change fit mode */
}
```

### Changing Thumbnail Size

Modify `.carousel-thumbnail` in CSS:

```css
.carousel-thumbnail {
    width: 100px;
    height: 100px;
}
```

---

## Technical Notes

### Image URL Format

Images are loaded using Odoo's web image controller:

```
/web/image/{attachment_id}
```

### Base64 Processing

When uploading, the data URI prefix is stripped:

```javascript
datas: base64.split(',')[1]  // "data:image/png;base64,ABC..." → "ABC..."
```

### Index Management on Delete

After deletion, the index is adjusted to prevent out-of-bounds:

```javascript
if (this.state.currentIndex >= this.images.length - 1 && this.state.currentIndex > 0) {
    this.state.currentIndex--;
}
```

---

## Browser Compatibility

- Uses modern JavaScript features (async/await, arrow functions)
- FileReader API for base64 conversion
- CSS flexbox for thumbnail layout
- Custom scrollbar styling (webkit-specific)

---

## File Reference

| File | Purpose |
|------|---------|
| `__init__.py` | Empty module initialization |
| `__manifest__.py` | Module metadata and asset registration |
| `static/src/js/m2m_attachment_carousel_view.js` | OWL component implementation |
| `static/src/xml/image_carousel_template.xml` | QWeb template for widget |
| `static/src/css/image_carousel.css` | Widget styling |