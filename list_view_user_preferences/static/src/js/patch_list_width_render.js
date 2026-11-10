// /** @odoo-module **/
//
// import { patch } from "@web/core/utils/patch";
// import { ListRenderer } from "@web/views/list/list_renderer";
// import {
//     onMounted,
//     onPatched,
//     useExternalListener,
// } from "@odoo/owl";
//
// /**
//  * Automatically sizes each list-view column according to its
//  * largest rendered content:
//  *
//  *     max(header, cell 1, cell 2, cell 3, ...)
//  *
//  * The browser performs the measurement, so this works better than
//  * canvas text measurement for:
//  *
//  * - char
//  * - many2one
//  * - monetary
//  * - selection
//  * - badges
//  * - links
//  * - dates
//  * - custom widgets
//  * - buttons
//  * - inputs
//  */
// function autoFitListColumns(table) {
//     if (!table) {
//         return;
//     }
//
//     const headers = [
//         ...table.querySelectorAll("thead > tr:first-child > th"),
//     ];
//
//     if (!headers.length) {
//         return;
//     }
//
//     /*
//      * Temporarily let the browser calculate the real natural
//      * width of every table column.
//      */
//     table.style.tableLayout = "auto";
//     table.style.width = "max-content";
//     table.style.minWidth = "0";
//
//     /*
//      * Remove widths previously applied by Odoo or by an earlier
//      * execution of this function.
//      */
//     for (const th of headers) {
//         th.style.width = "";
//         th.style.maxWidth = "";
//     }
//
//     /*
//      * Odoo itself uses this class while calculating natural widths.
//      * Among other things, it prevents text fields from wrapping while
//      * their widths are being measured.
//      */
//     table.classList.add("o_list_computing_widths");
//
//     // Force browser layout calculation.
//     void table.offsetWidth;
//
//     /*
//      * At this point HTML table layout has already made each TH as wide
//      * as the largest cell in that column.
//      */
//     const widths = headers.map((th) => {
//         return Math.ceil(th.getBoundingClientRect().width);
//     });
//
//     table.classList.remove("o_list_computing_widths");
//
//     /*
//      * Freeze the calculated widths so adding/editing a row doesn't
//      * make random columns jump around.
//      */
//     table.style.tableLayout = "fixed";
//
//     const totalWidth = widths.reduce((total, width) => total + width, 0);
//
//     table.style.width = `${Math.ceil(totalWidth)}px`;
//
//     headers.forEach((th, index) => {
//         th.style.width = `${widths[index]}px`;
//     });
// }
//
//
// /*
//  * Disable Odoo 18's native "magic" width redistribution.
//  *
//  * Odoo normally calculates content widths and then shrinks/expands
//  * columns according to the available viewport width.
//  *
//  * We don't want that behavior.
//  */
// patch(ListRenderer, {
//     useMagicColumnWidths: false,
// });
//
//
// /*
//  * Apply our automatic content-based widths to every standard
//  * ListRenderer.
//  */
// patch(ListRenderer.prototype, {
//     setup() {
//         super.setup();
//
//         const applyAutoWidths = () => {
//             const table = this.tableRef?.el;
//
//             if (!table) {
//                 return;
//             }
//
//             autoFitListColumns(table);
//         };
//
//         /*
//          * Initial list load.
//          */
//         onMounted(() => {
//             requestAnimationFrame(() => {
//                 applyAutoWidths();
//             });
//         });
//
//         /*
//          * Recalculate when:
//          *
//          * - records change
//          * - optional columns change
//          * - search/filter changes
//          * - groups expand
//          * - pagination changes
//          * - editable rows are rendered
//          */
//         onPatched(() => {
//             requestAnimationFrame(() => {
//                 applyAutoWidths();
//             });
//         });
//
//         /*
//          * Recalculate after browser/window resize.
//          */
//         useExternalListener(window, "resize", () => {
//             requestAnimationFrame(() => {
//                 applyAutoWidths();
//             });
//         });
//     },
// });

/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import {
    onMounted,
    onPatched,
    useExternalListener,
} from "@odoo/owl";


function autoFitListColumns(table) {
    if (!table) {
        return;
    }

    const headers = [
        ...table.querySelectorAll("thead > tr:first-child > th"),
    ];

    if (!headers.length) {
        return;
    }

    /*
     * STEP 1
     * Let the browser calculate natural widths.
     *
     * Natural width means:
     * max(header width, largest cell content width)
     */
    table.style.tableLayout = "auto";
    table.style.width = "max-content";
    table.style.minWidth = "0";

    /*
     * Remove widths previously applied by this code/Odoo
     * so measurements are fresh.
     */
    for (const th of headers) {
        th.style.width = "";
        th.style.minWidth = "";
        th.style.maxWidth = "";
    }

    /*
     * Odoo uses this while computing column widths.
     * It helps avoid unwanted wrapping during measurement.
     */
    table.classList.add("o_list_computing_widths");

    /*
     * Force browser layout.
     */
    void table.offsetWidth;

    /*
     * Because this is an HTML table, each TH width now represents
     * the width required by the largest content in that column.
     */
    const widths = headers.map((th) => {
        return Math.ceil(th.getBoundingClientRect().width);
    });

    table.classList.remove("o_list_computing_widths");

    /*
     * Natural total width of the table.
     */
    let totalWidth = widths.reduce((sum, width) => sum + width, 0);

    /*
     * Width available in the list container.
     */
    const parent = table.parentElement;

    const availableWidth = parent
        ? Math.floor(parent.getBoundingClientRect().width)
        : totalWidth;

    /*
     * STEP 2
     *
     * If the columns are smaller than the available page width,
     * distribute the remaining space.
     *
     * Example:
     *
     * Natural total = 600px
     * Available     = 1400px
     *
     * Extra 800px is distributed among normal columns.
     *
     * This prevents small lists from becoming narrow.
     */
    if (totalWidth < availableWidth) {
        const extraSpace = availableWidth - totalWidth;

        /*
         * Do NOT enlarge utility columns like:
         *
         * - checkbox selector
         * - action buttons
         * - optional-column menu
         *
         * Only normal field columns should expand.
         */
        const expandableIndexes = [];

        headers.forEach((th, index) => {
            const isUtilityColumn =
                th.classList.contains("o_list_record_selector") ||
                th.classList.contains("o_list_button") ||
                th.classList.contains("o_list_controller") ||
                th.classList.contains("o_optional_columns_dropdown") ||
                th.classList.contains("o_list_actions_header");

            if (!isUtilityColumn) {
                expandableIndexes.push(index);
            }
        });

        if (expandableIndexes.length) {
            const extraPerColumn =
                extraSpace / expandableIndexes.length;

            for (const index of expandableIndexes) {
                widths[index] += extraPerColumn;
            }
        }
    }

    /*
     * Recalculate final total after distributing extra space.
     */
    totalWidth = widths.reduce(
        (sum, width) => sum + width,
        0
    );

    /*
     * STEP 3
     *
     * Freeze calculated widths.
     *
     * If content is wider than the viewport,
     * the table stays wide and the list can scroll horizontally.
     *
     * We never shrink columns below their required content width.
     */
    table.style.tableLayout = "fixed";

    const finalWidth = Math.max(
        Math.ceil(totalWidth),
        availableWidth
    );

    table.style.width = `${finalWidth}px`;
    table.style.minWidth = "100%";

    /*
     * Apply widths to headers.
     *
     * With table-layout: fixed, these widths control
     * the corresponding TD cells too.
     */
    headers.forEach((th, index) => {
        const width = Math.ceil(widths[index]);

        th.style.width = `${width}px`;
        th.style.minWidth = `${width}px`;
        th.style.maxWidth = "";
    });
}


/*
 * Odoo 18 normally uses its "magic column width" system.
 *
 * That system:
 *
 * 1. calculates content widths
 * 2. applies field min/max rules
 * 3. shrinks/expands columns to fit the viewport
 *
 * We disable it because we want our own behavior.
 */
patch(ListRenderer, {
    useMagicColumnWidths: false,
});


/*
 * Apply the behavior globally to standard Odoo list views
 * using ListRenderer.
 */
patch(ListRenderer.prototype, {
    setup() {
        super.setup();

        let scheduledFrame = null;

        const applyAutoWidths = () => {
            const table = this.tableRef?.el;

            if (!table) {
                return;
            }

            /*
             * Prevent many recalculations in the same rendering cycle.
             */
            if (scheduledFrame) {
                cancelAnimationFrame(scheduledFrame);
            }

            scheduledFrame = requestAnimationFrame(() => {
                scheduledFrame = null;

                const currentTable = this.tableRef?.el;

                if (currentTable) {
                    autoFitListColumns(currentTable);
                }
            });
        };

        /*
         * Initial list rendering.
         */
        onMounted(() => {
            applyAutoWidths();
        });

        /*
         * Run again when Odoo updates the list.
         *
         * Examples:
         * - search/filter
         * - pagination
         * - group expand/collapse
         * - editable row
         * - optional columns
         * - records loaded
         */
        // onPatched(() => {
        //     applyAutoWidths();
        // });

        /*
         * Recalculate when browser/window size changes.
         */
        useExternalListener(
            window,
            "resize",
            applyAutoWidths
        );
    },
});