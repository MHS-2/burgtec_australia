# List View User Preferences (Odoo 18)

Per-user, server-side list view preferences:

* **optional columns** (show/hide) — existing feature
* **column widths** — new: drag a column border once, that user keeps that exact
  width everywhere, forever (reload, logout/login, another browser or device)

## How the width feature works

Odoo 18 computes column widths in
`addons/web/static/src/views/list/column_width_hook.js` (`useMagicColumnWidths`).
`getWidthSpecs()` treats an arch attribute `width="130px"` as
`minWidth === maxWidth`: the column is pinned and the algorithm redistributes the
remaining space over the *other* columns.

This module simply stamps the user's saved width onto the column at render time
(`ListRenderer.processAllColumn`), so core enforces it on every recompute
(filters, grouping, paging, optional column toggle, window resize).
The width is captured by decorating `columnWidths.onStartResize` and reading the
final `th` width on `pointerup`.

Key = core's `ListRenderer.createViewKey()`, prefixed `column_widths,`.
It contains model + view id + sorted field names, and for x2many sub-lists the
parent model + relational field — so a one2many inside a form is keyed separately
from the standalone list of the same model.

## Install / test

1. Drop the folder in your addons path (replaces the previous version of the
   same module — bump is `18.0.2.0.0`).
2. `odoo-bin -u list_view_user_preferences -d <db>` and hard-refresh the browser
   (assets).
3. Open any list view, drag a column border, reload → same width. Log in as
   another user → that user's own width (or the Odoo default).
4. Check `Settings > Technical > List View User Preferences` (developer mode) to
   see/delete stored rows. Deleting a row resets that view for that user.

## Isolation from the existing show/hide feature

The width feature never touches the optional-columns code path:

| | optional columns | column widths |
|---|---|---|
| DB column | `active_fields` (Text) | `column_widths` (Json) |
| DB row | `view_key` = `optional_fields,<key>` | `view_key` = `column_widths,<key>` |
| load route | `/web/list_view/load_all_preferences` (unchanged payload) | `/web/list_view/load_all_column_widths` (new) |
| save route | `/web/list_view/save_preference` (unchanged) | `/web/list_view/save_column_widths` (new) |
| JS patch | `list_renderer_patch.js` (byte-identical to v1) | `list_column_width_patch.js` (new) |
| service cache | `preferences` / `getPreference` / `savePreference` (unchanged) | `widths` / `getWidths` / `saveWidths` (added) |
| renderer hook | `computeOptionalActiveFields` / `saveOptionalActiveFields` | `processAllColumn` / `onStartResize` |

* Existing rows are untouched: `column_widths` is a new nullable column, nothing
  is renamed or migrated.
* `_set_for_user()` writes only the keys it is given, so saving a width can never
  blank an `active_fields` value and vice versa.
* `load_all_preferences` now filters `active_fields != False`, so width-only rows
  cannot leak into the optional-columns cache (a row present with an empty value
  would be read as "all optional columns hidden").
* Width columns are cloned before `attrs.width` is stamped on them, so
  `props.archInfo` stays pristine for the optional-columns logic (`col.optional`,
  `col.name`, `col.label`, `col.id` are all preserved by the clone).
* If the width RPC fails, `getWidths()` returns null and core's native sizing
  applies; the show/hide feature is unaffected either way.

Covered by `TestListViewColumnWidth` and
`TestOptionalFieldsPayloadNonRegression` in `tests/`.

## Notes / limits

* Only the dragged column is persisted, on purpose. If *every* column were
  pinned, core's last-resort branch in `computeWidths()` spreads leftover space
  over all columns and exact widths would drift.
* `createViewKey()` includes the field names, so editing the view arch (adding a
  field) invalidates the saved widths for that view. For a key that survives arch
  changes, replace `this.keyColumnWidths` in
  `static/src/js/list_column_width_patch.js` with:

  ```js
  const n = this.props.nestedKeyOptionalFieldsData;
  this.keyColumnWidths = n
      ? `column_widths,${n.model},${n.viewMode},${n.field},list`
      : `column_widths,${this.props.list.resModel},list,${this.env.config.viewId}`;
  ```

* Widths are stored **without** cell padding (same unit as `width="Npx"` in the
  arch); core adds the padding back when applying.
* v18 only: `this.columnWidths` / `useMagicColumnWidths` do not exist in v17.
  The patch degrades gracefully (no crash), but nothing is persisted.
* Removed `static/src/js/patch_list_width_render.js` from the previous version:
  it set `ListRenderer.useMagicColumnWidths = false` and re-implemented sizing,
  which conflicts with this approach.
