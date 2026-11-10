/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, status } from "@odoo/owl";

/**
 * Per-user persistent column widths.
 *
 * Odoo 18 only. Column sizing lives in
 * `web/static/src/views/list/column_width_hook.js` (`useMagicColumnWidths`),
 * which ListRenderer.setup() stores in `this.columnWidths` ({resizing, onStartResize}).
 *
 * Read path : `getWidthSpecs()` turns an arch attribute width="130px" into
 *             minWidth === maxWidth, i.e. a column the layout algorithm can
 *             neither shrink nor expand. We stamp the saved width onto the
 *             column at render time, so core enforces it on every recompute
 *             (filters, grouping, window resize, optional column toggle...).
 * Write path : we decorate `onStartResize` and read the final width on pointerup.
 *
 * Only the column the user actually dragged is stored: if every column were
 * pinned, core's last-resort branch in computeWidths() spreads the leftover
 * space over all columns and the exact widths would drift.
 */

const MIN_SAVED_WIDTH = 20; // core clamps the drag at 10px - don't persist an unusable column

/**
 * @param {HTMLElement} el
 * @returns {number} sum of left and right padding, like core's getHorizontalPadding
 */
function horizontalPadding(el) {
    const { paddingLeft, paddingRight } = getComputedStyle(el);
    return parseFloat(paddingLeft) + parseFloat(paddingRight);
}

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.widthPref = useService("listViewPreference");
        // same view identity as core's optional fields key (handles x2many sub-lists)
        this.keyColumnWidths = `column_widths,${this.createViewKey()}`;
        onWillStart(() => this.widthPref.loadWidths());

        if (!this.columnWidths || !this.columnWidths.onStartResize) {
            return; // magic widths disabled (or non-v18 core): nothing to hook
        }
        const startResize = this.columnWidths.onStartResize;
        this.columnWidths.onStartResize = (ev) => {
            const th = ev.target.closest("th");
            startResize(ev);
            // core registers its own stopResize on window first, so this runs after it
            window.addEventListener("pointerup", () => this.saveResizedColumn(th), {
                once: true,
            });
        };
    },

    /**
     * @override
     * Inject the user's saved widths as a hard `width` arch attribute.
     * Columns are cloned: props.archInfo is shared by every renderer of that view.
     */
    processAllColumn() {
        const columns = super.processAllColumn(...arguments);
        const saved = this.widthPref && this.widthPref.getWidths(this.keyColumnWidths);
        if (!saved) {
            return columns;
        }
        return columns.map((col) =>
            col.type === "field" && saved[col.name]
                ? { ...col, attrs: { ...col.attrs, width: `${saved[col.name]}px` } }
                : col
        );
    },

    /**
     * Persist the width of the column whose border was just dragged.
     * @param {HTMLElement} th
     */
    saveResizedColumn(th) {
        if (status(this) === "destroyed" || !this.tableRef.el || !th || !th.isConnected) {
            return;
        }
        // thead = [selector?] + this.columns + [open form view?] + [actions?]
        const thIndex = [...th.parentNode.children].indexOf(th);
        const column = this.columns[thIndex - (this.hasSelectors ? 1 : 0)];
        if (!column || column.type !== "field") {
            return;
        }
        // store the content width: core adds the cell padding back when applying it
        const width = Math.max(
            MIN_SAVED_WIDTH,
            Math.round(th.getBoundingClientRect().width - horizontalPadding(th))
        );
        const saved = { ...(this.widthPref.getWidths(this.keyColumnWidths) || {}) };
        if (saved[column.name] === width) {
            return;
        }
        saved[column.name] = width;
        this.widthPref.saveWidths(this.keyColumnWidths, saved);
    },
});
