/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useRef, onMounted, onWillUpdateProps, onWillPatch } from "@odoo/owl";
import { ListRenderer } from "@web/views/list/list_renderer";

patch(ListRenderer.prototype, {

    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this._isLoadingLimit = false; // 🔒 re-entrancy guard

        onMounted(async () => {
            const list = this.props.list;
            if (list.config?.resModel !== 'sale.order.bom.component.line') return;
            

            const bomId = list.model?.root?.config?.resId;
            if (!bomId) return;

            const limit_data = await this.orm.call(
                "sale.order.bom.component",
                "get_min_max_limits",
                [Number(bomId)]
            );
            // console.log("ONMOUNT Limit Data---", limit_data);
            const limit = limit_data.limit;
            const offset = limit_data.offset;
            await list.load({ limit, offset: offset });
            this.render(true);
        });

        onWillPatch(async () =>{
            if (this.props.list?.config?.resModel !== 'sale.order.bom.component.line') return;
            // console.log('WILL PATCH', this.props.list);
            const newLimit = this.props.list?.limit;
            const offSet = this.props.list?.offset;
            const bomId = this.props.list?.model?.root?.config?.resId;
            if (!bomId) return;

            // await this.orm.call(
            //     "sale.order.bom.component",
            //     "set_min_max_limits",
            //     [Number(bomId)],
            //     { min_limit: offSet, max_limit: newLimit}
            // );

            const limit_data = await this.orm.call(
                "sale.order.bom.component",
                "get_min_max_limits",
                [Number(bomId)]
            );
            // console.log('Will Patch Limit Data',limit_data);
            const oldLimit = limit_data.limit;
            const oldOffset = limit_data.offset;

            // const prevLimit = await this.orm.call(
            //         "sale.order.bom.component",
            //         "get_record_limit",
            //         [Number(bomId)]
            //     );
            // console.log('Patch Limits ---=>',oldLimit, newLimit);
            // console.log('Patch Offsets ---=>',oldOffset, offSet);
            if (oldLimit === newLimit && oldOffset === offSet) return;
            // await this.orm.call(
            //         "sale.order.bom.component",
            //         "set_record_limit",
            //         [Number(bomId)],
            //         { limit: newLimit }
            //     );
            // await this.orm.call(
            //     "sale.order.bom.component",
            //     "set_min_max_limits",
            //     [Number(bomId)],
            //     { min_limit: offSet, max_limit: newLimit}
            // );
            await this.props.list.load({ limit: oldLimit, offset: oldOffset });
            this.render(true);


        });

        onWillUpdateProps(async (nextProps) => {
            // ✅ Guard 1: only run for our model
            if (nextProps.list?.config?.resModel !== 'sale.order.bom.component.line') return;

            // ✅ Guard 2: prevent re-entrant calls (load() triggers onWillUpdateProps again)
            if (this._isLoadingLimit) return;

            // ✅ Guard 3: only act if the limit actually changed
            var prevLimit = this.props.list?.limit;
            var nextLimit = nextProps.list?.limit;
            var offset = this.props.list?.offset;
            var nextOffset = nextProps.list?.offset;
            
            
            const bomId = nextProps.list?.model?.root?.config?.resId;
            if (!bomId) return;

            const limit_data = await this.orm.call(
                "sale.order.bom.component",
                "get_min_max_limits",
                [Number(bomId)]
            );
            const oldLimit = limit_data.limit;
            const oldOffset = limit_data.offset;


            // console.log('Compare Limit -->',oldLimit,nextLimit);
            // console.log('Compare Offset -->',oldOffset,nextOffset);

            // console.log("<><> Limit Data <><>", limit_data);
            
            if (oldLimit === nextLimit && oldOffset === nextOffset) return;
            const isReset = await this.orm.call(
                "sale.order.bom.component",
                "get_is_reset_check",
                [Number(bomId)]
            );

            // console.log("Reset value =>",isReset);
            
            // console.log("<><> Passed <><>");
            await this.orm.call(
                "sale.order.bom.component",
                "set_min_max_limits",
                [Number(bomId)],
                { min_limit: offset, max_limit: prevLimit}
            );

            this._isLoadingLimit = true;
            try {
                // console.log('=======>> TRY   <=========', nextProps);
                // Combine into one call if possible, or run in parallel

                // Reset Limit Initiated.
                if (!isReset){
                    await nextProps.list.load({ limit: prevLimit, offset: offset });
                }
                if(isReset){
                    // console.log('--------- IS RESET -------');
                    prevLimit = 100
                    // mark the field back to false for future.
                    await this.orm.call(
                        "sale.order.bom.component",
                        "set_reset_false",
                        [Number(bomId)]
                    );
                    await this.orm.call(
                        "sale.order.bom.component",
                        "set_min_max_limits",
                        [Number(bomId)],
                        { min_limit: 0, max_limit: 100}
                    );
                    await nextProps.list.load({ limit: 100, offset: 0 });

                }
                // await this.orm.call(
                //     "sale.order.bom.component",
                //     "set_record_limit",
                //     [Number(bomId)],
                //     { limit: prevLimit }
                // );

                // const confirmedLimit = await this.orm.call(
                //     "sale.order.bom.component",
                //     "get_record_limit",
                //     [Number(bomId)]
                // );
                // console.log('New Confirmed Limit', confirmedLimit);

                // await nextProps.list.load({ limit: nextLimit, offset: nextOffset });
                this.render(true);
            } finally {
                // console.log('=======>> FINALLY   <=========');
                this._isLoadingLimit = false; // always release the lock
            }
        });
    },
});