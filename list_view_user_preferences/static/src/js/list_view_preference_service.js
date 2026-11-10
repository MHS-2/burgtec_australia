/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const listViewPreferenceService = {
    dependencies: [],
    async start() {
        // --- optional columns (show/hide): unchanged ---------------------
        let preferences = {};
        let loaded = false;
        let loadPromise = null;

        // --- column widths: independent cache and request ----------------
        let widths = {};
        let widthsLoaded = false;
        let widthsPromise = null;

        async function ensureLoaded() {
            if (loaded) {
                return;
            }
            if (!loadPromise) {
                loadPromise = rpc("/web/list_view/load_all_preferences", {})
                    .then((result) => {
                        preferences = result || {};
                        loaded = true;
                    })
                    .catch(() => {
                        // If loading fails, use empty preferences (fallback to localStorage)
                        preferences = {};
                        loaded = true;
                    });
            }
            await loadPromise;
        }

        async function ensureWidthsLoaded() {
            if (widthsLoaded) {
                return;
            }
            if (!widthsPromise) {
                widthsPromise = rpc("/web/list_view/load_all_column_widths", {})
                    .then((result) => {
                        widths = result || {};
                        widthsLoaded = true;
                    })
                    .catch(() => {
                        // If loading fails, Odoo's native column sizing applies
                        widths = {};
                        widthsLoaded = true;
                    });
            }
            await widthsPromise;
        }

        return {
            /**
             * Ensure preferences are loaded from the server.
             */
            async loadPreferences() {
                await ensureLoaded();
            },

            /**
             * Get a preference value synchronously (must call loadPreferences first).
             * @param {string} key - The view key
             * @returns {string|null} Comma-separated active field names or null
             */
            getPreference(key) {
                if (!loaded) {
                    return null;
                }
                return key in preferences ? preferences[key] : null;
            },

            /**
             * Save a preference to server and local cache.
             * @param {string} key - The view key
             * @param {string} value - Comma-separated active field names
             */
            async savePreference(key, value) {
                preferences[key] = value;
                try {
                    await rpc("/web/list_view/save_preference", {
                        view_key: key,
                        active_fields: value,
                    });
                } catch {
                    // Silently fail - localStorage will still have the value
                }
            },

            /**
             * Ensure column widths are loaded from the server.
             */
            async loadWidths() {
                await ensureWidthsLoaded();
            },

            /**
             * Get the saved widths of a list view (must call loadWidths first).
             * @param {string} key - The view key
             * @returns {Object|null} {fieldName: widthInPx} or null
             */
            getWidths(key) {
                if (!widthsLoaded) {
                    return null;
                }
                return widths[key] || null;
            },

            /**
             * Save column widths to server and local cache.
             * @param {string} key - The view key
             * @param {Object} value - {fieldName: widthInPx}
             */
            async saveWidths(key, value) {
                widths[key] = value;
                try {
                    await rpc("/web/list_view/save_column_widths", {
                        view_key: key,
                        widths: value,
                    });
                } catch {
                    // Silently fail - the width stays applied for this session
                }
            },
        };
    },
};

registry
    .category("services")
    .add("listViewPreference", listViewPreferenceService);
