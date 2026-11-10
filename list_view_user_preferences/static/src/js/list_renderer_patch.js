/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.listViewPreferenceService = useService("listViewPreference");

        // Load server preferences before the first render
        onWillStart(async () => {
            await this.listViewPreferenceService.loadPreferences();
        });
    },

    /**
     * Override to check server-side preferences before localStorage.
     */
    computeOptionalActiveFields() {
        const serverValue = this.listViewPreferenceService
            ? this.listViewPreferenceService.getPreference(this.keyOptionalFields)
            : null;

        if (serverValue !== null) {
            const optionalColumns = this.allColumns.filter(
                (col) => col.type === "field" && col.optional
            );
            // If there are no optional columns, fall back to default
            if (!optionalColumns.length) {
                return super.computeOptionalActiveFields(...arguments);
            }
            const serverActiveFields = serverValue ? serverValue.split(",") : [];
            const optionalActiveFields = {};
            for (const col of optionalColumns) {
                optionalActiveFields[col.name] = serverActiveFields.includes(col.name);
            }
            return optionalActiveFields;
        }
        // No server preference found - use original localStorage behavior
        return super.computeOptionalActiveFields(...arguments);
    },

    /**
     * Override to save preferences to server in addition to localStorage.
     */
    saveOptionalActiveFields() {
        // Save to localStorage first (original behavior, immediate)
        super.saveOptionalActiveFields(...arguments);

        // Also save to server for cross-session persistence
        if (this.listViewPreferenceService) {
            const activeFieldNames = Object.keys(this.optionalActiveFields)
                .filter((fieldName) => this.optionalActiveFields[fieldName])
                .join(",");
            this.listViewPreferenceService.savePreference(
                this.keyOptionalFields,
                activeFieldNames
            );
        }
    },
});
