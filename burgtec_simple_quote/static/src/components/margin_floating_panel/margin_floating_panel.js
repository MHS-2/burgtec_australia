/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { onMounted, onPatched, onWillUnmount } from "@odoo/owl";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);

        this._marginPanel = null;

        onMounted(() => {
            // this._applyChatterDefault();

            if (this._isSaleOrder()) {
                this._createHeaderMarginPanel();
                this._updateMarginValues();
            }
        });

        onPatched(() => {
            if (this._isSaleOrder()) {
                this._createHeaderMarginPanel();
                // if (!this._marginPanel || !this._marginPanel.isConnected) {
                // }
                this._updateMarginValues();
            }
        });

        onWillUnmount(() => {
            this._destroyMarginPanel();
        });
    },

    //----------------------------------------------------------
    // Chatter default
    //----------------------------------------------------------

    _applyChatterDefault() {
        const formSheet = document.querySelector(".o_form_sheet_bg");
        const chatterContainer = document.querySelector(".o-mail-ChatterContainer");
        const btn = document.querySelector(".o_chatter_toggle_btn");
        if (!formSheet || !chatterContainer) return;

        if (this._isSaleOrder()) {
            formSheet.classList.add("max-width-unset");
            chatterContainer.classList.add("d-none");
            if (btn) {
                btn.dataset.collapsed = "true";
                btn.setAttribute("title", "Show Chatter");
            }
        } else {
            formSheet.classList.remove("max-width-unset");
            chatterContainer.classList.remove("d-none");
            if (btn) {
                btn.dataset.collapsed = "false";
                btn.setAttribute("title", "Hide Chatter");
            }
        }
    },

    _isSaleOrder() {
        if ("simple_quote" in this.props.context) {
            if (this.props.context.simple_quote){
                return false
            }
        }
        return this.props.resModel === "sale.order";
    },

    //----------------------------------------------------------
    // Header margin panel (inline in control panel)
    //----------------------------------------------------------

    _createHeaderMarginPanel() {
        console.log("Creating Header");
        const records = this.model.root.data.defected_line_ids?.records;
        if (!records && this._marginPanel && this._marginPanel.isConnected) return;
        this._destroyMarginPanel();

        // Find the control panel navigation area (where pager/toggle lives)
        // Try multiple selectors for compatibility across Odoo 17/18
        const anchor =
            document.querySelector(".o_control_panel_navigation") ||
            document.querySelector(".o_control_panel_main .o_cp_pager")?.parentElement ||
            document.querySelector(".o_control_panel_main");

        if (!anchor) return;

        

        const panel = document.createElement("div");
        panel.className = "o_margin_header_panel";
        if (records && records.length > 0) {
            panel.innerHTML = `
            <table class="o_margin_header_table">
                <tr>
                    <td class="o_mh_label">Excl Def</td>
                    <td class="o_mh_value" data-field="total_untaxed_amount_excl">?</td>
                    <td class="o_mh_sep">┃</td>
                    <td class="o_mh_label">GP$</td>
                    <td class="o_mh_value" data-field="gp_excl">?</td>
                    <td class="o_mh_sep">┃</td>
                    <td class="o_mh_label">Margin</td>
                    <td class="o_mh_value" data-field="margin_excl">?</td>
                    <td class="o_mh_sep">┃</td>
                    <td class="o_mh_label">Markup</td>
                    <td class="o_mh_value" data-field="markup_excl">?</td>
                </tr>
                <tr class="border-top-custom" style="color:#FF2A00">
                    <td class="o_mh_label_incl">Incl Def</td>
                    <td class="o_mh_value_incl" data-field="total_untaxed_amount">?</td>
                    <td class="o_mh_sep_incl">┃</td>
                    <td class="o_mh_label_incl">GP$</td>
                    <td class="o_mh_value_incl" data-field="gp">?</td>
                    <td class="o_mh_sep_incl">┃</td>
                    <td class="o_mh_label_incl">Margin</td>
                    <td class="o_mh_value_incl" data-field="margin">?</td>
                    <td class="o_mh_sep_incl">┃</td>
                    <td class="o_mh_label_incl">Markup</td>
                    <td class="o_mh_value_incl" data-field="markup">?</td>
                   
                </tr>
            </table>
        `;
        }
        else{
            panel.innerHTML = `
                <table class="o_margin_header_table">
                    <tr>
                        <td class="o_mh_label">Total</td>
                        <td class="o_mh_value" data-field="total_untaxed_amount">?</td>
                        <td class="o_mh_sep">┃</td>
                        <td class="o_mh_label">GP$</td>
                        <td class="o_mh_value" data-field="gp">?</td>
                        <td class="o_mh_sep">┃</td>
                        <td class="o_mh_label">Margin</td>
                        <td class="o_mh_value" data-field="margin">?</td>
                        <td class="o_mh_sep">┃</td>
                        <td class="o_mh_label">Markup</td>
                        <td class="o_mh_value" data-field="markup">?</td>
                       
                    </tr>
                </table>
            `;
        }
        // Insert before the pager so it sits to its left,
        // or just prepend into the navigation area
        const pager = anchor.querySelector(".o_cp_pager");
        if (pager) {
            anchor.insertBefore(panel, pager);
        } else {
            anchor.prepend(panel);
        }

        this._marginPanel = panel;
    },

    _destroyMarginPanel() {
        if (this._marginPanel) {
            this._marginPanel.remove();
            this._marginPanel = null;
        }
    },

    _updateMarginValues() {
        if (!this._marginPanel) return;
        const record = this.model.root;
        if (!record || !record.data) return;
        const d = record.data;

        const fmt = (val) => {
            if (val === undefined || val === null || val === false) return "?";
            return parseFloat(val).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            });
        };
        const pct = (val) => {
            if (val === undefined || val === null || val === false) return "?";
            return (parseFloat(val) * 100).toFixed(2) + "%";
        };

        const cells = this._marginPanel.querySelectorAll("td[data-field]");
        const values = {
            total_untaxed_amount : fmt(d.amount_untaxed),
            gp: fmt(d.live_unit_cost),
            markup: pct(d.percentage_markup_live_cost),
            margin: pct(d.percentage_margin_live_cost),
            total_untaxed_amount_excl : fmt(d.total_amount_untaxed_exl_defect),
            gp_excl: fmt(d.total_gp_exl_defect),
            markup_excl: pct(d.percentage_markup_live_cost_exl_defect),
            margin_excl: pct(d.percentage_margin_live_cost_exl_defect),
        };

        cells.forEach((cell) => {
            const field = cell.dataset.field;
            cell.textContent = values[field] || "?";
        });
    },
});