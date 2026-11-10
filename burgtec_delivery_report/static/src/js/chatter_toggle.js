/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { append, combineAttributes, createElement, setAttributes } from "@web/core/utils/xml";
import { FormCompiler } from "@web/views/form/form_compiler";

patch(FormCompiler.prototype, {
    compile(node, params) {
        const res = super.compile(node, params);
        const chatterContainerHookXml = res.querySelector(".o-mail-Form-chatter");
        if (!chatterContainerHookXml) {
            return res;
        }
        const hasPreview = !!res.querySelector(".o_attachment_preview");

        // default state: collapsed, baked into the arch
        combineAttributes(chatterContainerHookXml, "class", "d-none", " ");

        const floatingToggle = createElement("div");
        setAttributes(floatingToggle, {
            "t-attf-class": `{{ ["SIDE_CHATTER", "EXTERNAL_COMBO_XXL"].includes(__comp__.mailLayout(${hasPreview})) ? "o_chatter_floating_toggle" : "d-none" }}`,
        });
        const hideChatter = createElement("button");
        setAttributes(hideChatter, {
            type: "button",
            class: "btn btn-secondary o_chatter_toggle_btn",
            "data-collapsed": "true",
            title: "Show Chatter",
        });
        append(hideChatter, createElement("span"));
        append(floatingToggle, hideChatter);

        const formSheet = res.querySelector(".o_form_sheet_bg");
        if (formSheet) {
            combineAttributes(formSheet, "class", "max-width-unset", " ");
            append(formSheet, floatingToggle);
        }
        return res;
    },
});

// delegated listener, bound once, scoped per form — no persistence
if (!document.__chatterClickBound) {
    document.addEventListener("click", (ev) => {
        const btn = ev.target.closest(".o_chatter_toggle_btn");
        if (!btn) {
            return;
        }
        const root = btn.closest(".o_form_renderer") || btn.closest(".o_form_view");
        const sheet = btn.closest(".o_form_sheet_bg");
        const chatter = root && root.querySelector(".o-mail-Form-chatter");
        if (!sheet || !chatter) {
            return;
        }
        const collapsed = !JSON.parse(btn.dataset.collapsed);
        btn.dataset.collapsed = collapsed;
        sheet.classList.toggle("max-width-unset", collapsed);
        chatter.classList.toggle("d-none", collapsed);
        btn.setAttribute("title", collapsed ? "Show Chatter" : "Hide Chatter");
    });
    document.__chatterClickBound = true;
}