/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SectionAndNoteListRenderer } from
    "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";

patch(SectionAndNoteListRenderer.prototype, {
    /**
     * Override getSectionColumns to include button_group columns alongside
     * the handle widget and name field on section/note lines.
     *
     * In Odoo 18, buttons in list views are parsed as type "button_group"
     * (not "button"). The default getSectionColumns only keeps:
     *   - columns with widget "handle"
     *   - field columns with name === titleField ("name")
     * This patch also keeps "button_group" columns so buttons are visible
     * on section and note lines.
     */
    getSectionColumns(columns) {
        // Keep: handle, titleField, AND button_group columns
        const sectionCols = columns.filter(
            (col) =>
                col.widget === "handle" ||
                (col.type === "field" && col.name === this.titleField) ||
                col.type === "button_group"
        );

        // Calculate colspan for the title field
        // It should span across all the columns that were removed
        return sectionCols.map((col) => {
            if (col.name === this.titleField) {
                return {
                    ...col,
                    colspan: columns.length - sectionCols.length + 1,
                };
            }
            return { ...col };
        });
    },

    /**
     * Override getCellClass to NOT hide button_group columns
     * on section/note lines (secondary safety mechanism).
     */
    getCellClass(column, record) {
        const classNames = super.getCellClass(column, record);
        if (this.isSectionOrNote(record) && column.type === "button_group") {
            return classNames.replace(/\bo_hidden\b/g, "");
        }
        return classNames;
    },
});
