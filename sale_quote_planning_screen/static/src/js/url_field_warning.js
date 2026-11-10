/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { UrlField } from "@web/views/fields/url/url_field";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(UrlField.prototype, {
    setup() {
        super.setup();

        this.dialog = useService("dialog");

        this.originalValue = this.props.record.data[this.props.name] || "";
        this.allowEditing = false;
    },

    onKeyDown(ev) {
        const allowedModels = [
            "sale.quote.planning.screen.line",
            "planning.screen.line",
        ];

        // Only for these models
        if (!allowedModels.includes(this.props.record.resModel)) {
            return;
        }

        // Only if URL already exists
        if (!this.originalValue) {
            return;
        }

        // Already confirmed once
        if (this.allowEditing) {
            return;
        }

        // Ignore navigation keys
        const ignored = [
            "Tab",
            "Shift",
            "Control",
            "Alt",
            "Meta",
            "ArrowLeft",
            "ArrowRight",
            "ArrowUp",
            "ArrowDown",
            "Home",
            "End",
            "Escape",
        ];

        if (ignored.includes(ev.key)) {
            return;
        }

        // Prevent the edit
        ev.preventDefault();
        ev.stopPropagation();

        this.dialog.add(ConfirmationDialog, {
            title: "Warning",
            body: "Are you sure you want to change this URL?",
            confirmLabel: "Continue",
            cancelLabel: "Cancel",

            confirm: () => {
                this.allowEditing = true;

                // Focus back to the field
                setTimeout(() => {
                    ev.target.focus();
                }, 0);
            },

            cancel: () => {
                ev.target.blur();
            },
        });
    },
});