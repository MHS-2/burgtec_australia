// /** @odoo-module **/
// import {patch} from "@web/core/utils/patch";
// import {ListRenderer} from "@web/views/list/list_renderer";
// import {useEffect} from "@odoo/owl";
//
// // Freeze everything up to the LAST visible field in this list (left → right order)
// const FREEZE_FIELDS = ["item", "code", "product_id"];
// // Height of the inner scroll box. Must be set for the header to float.
// const SCROLL_MAX_H = "70vh";
//
// patch(ListRenderer.prototype, {
//     setup() {
//         super.setup(...arguments);
//         useEffect(() => {
//             const table = this.tableRef?.el;
//             if (!table || !table.closest(".sticky_list")) {
//                 return;
//             }
//
//             // Frozen columns: prep_view only
//             const record = this.props.list?.model?.root?.data;
//             if (record && record.view_team === "prep_view") {
//                 this._applyStickyCols(table);
//             } else {
//                 this._clearStickyCols(table);
//             }
//
//             // Floating header: ALL columns, every view_team
//             this._applyStickyHead(table);
//
//             const ro = new ResizeObserver(() => {
//                 if (this.props.list?.model?.root?.data?.view_team === "prep_view") {
//                     this._applyStickyCols(table);
//                 }
//                 this._applyStickyHead(table);
//             });
//             table.querySelectorAll("thead th").forEach((th) => ro.observe(th));
//             return () => ro.disconnect();
//         });
//     },
//
//     // -------- vertical scroll box + sticky header on every th --------
//     _applyStickyHead(table) {
//         const scroller = table.closest(".o_list_renderer") || table.parentElement;
//         if (scroller) {
//             scroller.classList.add("o_sticky_scroll");
//             scroller.style.setProperty("max-height", SCROLL_MAX_H, "important");
//             scroller.style.setProperty("overflow", "auto", "important");
//         }
//         table.querySelectorAll("thead th").forEach((th) => {
//             th.style.setProperty("position", "sticky", "important");
//             th.style.setProperty("top", "0px", "important");
//             th.style.removeProperty("z-index");
//             if (!th.classList.contains("o_sticky_col")) {
//                 // frozen header cells keep their higher z-index from SCSS (5 / 6)
//                 th.style.setProperty("z-index", "4", "important");
//             }
//         });
//     },
//
//     _clearStickyCols(table) {
//         table.querySelectorAll(".o_sticky_col").forEach((el) => {
//             el.classList.remove("o_sticky_col", "o_sticky_last");
//             el.style.left = "";
//         });
//     },
//
//     _applyStickyCols(table) {
//         this._clearStickyCols(table);
//
//         const headRow = table.querySelector("thead tr");
//         if (!headRow) {
//             return;
//         }
//         const ths = [...headRow.children];
//
//         // last visible freeze field (-1 if all hidden)
//         const stopIdx = Math.max(
//             -1,
//             ...FREEZE_FIELDS.map((f) => ths.findIndex((th) => th.dataset.name === f))
//         );
//
//         // 0..stopIdx + button columns (always)
//         const idxs = ths
//             .map((_, i) => i)
//             .filter((i) => i <= stopIdx || ths[i].classList.contains("o_list_button"));
//         if (!idxs.length) {
//             return;
//         }
//         const lastIdx = Math.max(...idxs);
//
//         let acc = 0;
//         const lefts = {};
//         idxs.forEach((i) => {
//             lefts[i] = acc;
//             acc += ths[i].getBoundingClientRect().width;
//         });
//
//         table.querySelectorAll("thead tr, tbody tr.o_data_row").forEach((tr) => {
//             const cells = [...tr.children];
//             if (cells.length < ths.length) {
//                 return; // colspan rows (section/note/add line)
//             }
//             idxs.forEach((i) => {
//                 const cell = cells[i];
//                 cell.classList.add("o_sticky_col");
//                 cell.classList.toggle("o_sticky_last", i === lastIdx);
//                 cell.style.left = `${lefts[i]}px`;
//             });
//         });
//     },
// });
/** @odoo-module **/
// Assuming Odoo v18/v19. Sticky cols + floating header: prep_view ONLY.
import {patch} from "@web/core/utils/patch";
import {ListRenderer} from "@web/views/list/list_renderer";
import {useEffect} from "@odoo/owl";

// Freeze columns 0..last visible field in this list (left → right order).
// ⚠️ Only leading columns can be frozen — anything to the right of the last
// entry here must stay in normal flow or it detaches and floats over the table.
const FREEZE_FIELDS = ["item", "code", "product_variant_id"];
// Inner scroll box height — required for the header to float
const SCROLL_MAX_H = "70vh";

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        useEffect(() => {
            const table = this.tableRef?.el;
            if (!table || !table.closest(".sticky_list")) {
                return;
            }
            const isPrep = this.props.list?.model?.root?.data?.view_team === "prep_view";

            if (!isPrep) {
                // full teardown → stock Odoo rendering for default / approval_view
                this._clearStickyCols(table);
                this._applyStickyHead(table);
                return;
            }

            this._applyStickyCols(table);
            this._applyStickyHead(table); // ✅ after cols: no inline z-index clash

            const ro = new ResizeObserver(() => {
                if (this.props.list?.model?.root?.data?.view_team !== "prep_view") {
                    return;
                }
                this._applyStickyCols(table);
                this._applyStickyHead(table);
            });
            table.querySelectorAll("thead th").forEach((th) => ro.observe(th));
            return () => ro.disconnect();
        });
    },

    // -------- floating header (vertical) --------
    _applyStickyHead(table) {
        const scroller = table.closest(".o_list_renderer") || table.parentElement;
        if (scroller) {
            scroller.classList.add("o_sticky_scroll");
            scroller.style.setProperty("max-height", SCROLL_MAX_H, "important");
            scroller.style.setProperty("overflow", "auto", "important");
        }
        // z-index is owned by the SCSS (plain 4 / frozen 5 / frozen button 6).
        // Never set it inline here: inline !important would outrank the SCSS.
        table.querySelectorAll("thead th").forEach((th) => {
            th.style.setProperty("position", "sticky", "important");
            th.style.setProperty("top", "0px", "important");
        });
    },

    _clearStickyHead(table) {
        const scroller = table.closest(".o_list_renderer") || table.parentElement;
        if (scroller) {
            scroller.classList.remove("o_sticky_scroll");
            scroller.style.removeProperty("max-height");
            scroller.style.removeProperty("overflow");
        }
        table.querySelectorAll("thead th").forEach((th) => {
            th.style.removeProperty("position");
            th.style.removeProperty("top");
            th.style.removeProperty("z-index");
        });
    },

    // -------- frozen columns (horizontal) --------
    _clearStickyCols(table) {
        table.querySelectorAll(".o_sticky_col").forEach((el) => {
            el.classList.remove("o_sticky_col", "o_sticky_last");
            el.style.left = "";
        });
    },

    _applyStickyCols(table) {
        this._clearStickyCols(table);

        const headRow = table.querySelector("thead tr");
        if (!headRow) {
            return;
        }
        const ths = [...headRow.children];

        // last visible freeze field (-1 if all hidden → nothing to freeze)
        const stopIdx = Math.max(
            -1,
            ...FREEZE_FIELDS.map((f) => ths.findIndex((th) => th.dataset.name === f))
        );
        if (stopIdx < 0) {
            return;
        }

        // Leading block only: 0..stopIdx. Button columns inside that range are
        // included automatically; ones to the right of it are left alone.
        const idxs = ths.map((_, i) => i).filter((i) => i <= stopIdx);
        const lastIdx = stopIdx;

        // Measure each column against the table in the same frame — scroll
        // position cancels out and there is no cumulative rounding error.
        const tableLeft = table.getBoundingClientRect().left;
        const lefts = {};
        idxs.forEach((i) => {
            lefts[i] = Math.round(ths[i].getBoundingClientRect().left - tableLeft);
        });

        table.querySelectorAll("thead tr, tbody tr.o_data_row").forEach((tr) => {
            const cells = [...tr.children];
            if (cells.length < ths.length) {
                return; // colspan rows (section/note/add line)
            }
            idxs.forEach((i) => {
                const cell = cells[i];
                cell.classList.add("o_sticky_col");
                cell.classList.toggle("o_sticky_last", i === lastIdx);
                cell.style.left = `${lefts[i]}px`;
            });
        });
    },
});