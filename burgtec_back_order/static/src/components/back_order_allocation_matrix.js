/** @odoo-module */

import { Component, useState, useEffect, useRef, onWillUpdateProps, onPatched, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class BackOrderAllocationMatrix extends Component {
    static template = "burgtec_back_order.BackOrderAllocationMatrix";
    static props = {
        record: { type: Object, optional: true },
        "*": true,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            back_orders: [],
            products: [],
            allocations: {},
            isLoading: true,
            isSaving: false,
            process_completed: false
        });
        this._lastLoadKey = null;

         // Track last-loaded write_date to detect saves
        this._loadedWriteDate = null;
        this._isLoadingData = false;



        onWillStart(async () => {
            this._loadData();
        });

        
        // Reload when parent passes new props (e.g., navigating to another record)
        onWillUpdateProps(async (nextProps) => {
            const nextRecord = nextProps.record;
            const currentId = this.props.record && this.props.record.resId;
            const nextId = nextRecord && nextRecord.resId;
            if (nextId !== currentId) {
                this.state.isLoading = true;
                await this._loadData(nextProps);
            }
        });

        // After every DOM patch, check if write_date changed (meaning a save happened).
        // This is the reliable mechanism: the template reads write_date reactively
        // (via the hidden <span>), which triggers a re-render on save. Then
        // onPatched fires, we detect the write_date change, and reload data.
        onPatched(() => {
            const rec = this.props.record;
            if (!rec || !rec.resId) return;
            const currentWriteDate = rec.data.write_date;
            if (currentWriteDate && currentWriteDate !== this._loadedWriteDate && !this._isLoadingData) {
                this._loadData();
            }
        });
    }

    get recordId() {
        return this.props.record && this.props.record.resId;
    }

    async _loadData(props) {
        const record = (props && props.record) || this.props.record;
        if (!record) {
            this.state.isLoading = false;
            return;
        }
        const recordId = record.resId;
        if (!recordId) {
            this.state.isLoading = false;
            return;
        }

        // Build a load key to avoid redundant reloads
        // const numAreas = record.data.number_of_areas || 0;
        // this.state.currentarea = numAreas;
        // const loadKey = `${recordId}_${numAreas}`;
        // this._lastLoadKey = loadKey;

        try {
            const data = await this.orm.call(
                "back.order.planning",
                "get_back_order_matrix_data",
                [recordId]
            );
            // Only apply if this is still the latest load request
            // if (this._lastLoadKey === loadKey) {
            // }
            this.state.back_orders = data.back_orders || [];
            this.state.products = data.products || [];
            this.state.allocations = data.allocations || {};
            this.state.isLoading = false;
            this.state.process_completed = data.process_completed;
            // Record the write_date we loaded data for, so onPatched
            // doesn't trigger another reload for the same save.
            this._loadedWriteDate = record.data.write_date;
        } catch (error) {
            this.state.isLoading = false;
            console.error("Error loading area matrix data:", error);
        }
    }


    getAllocation(orderlineID, productID, backorderId) {
        
        // const key = `${productID}_${areaId}`;
        
        //  # Each Purchase Order Line with product is treated seperately whether the product was same or not.

        const key = `${orderlineID}_${backorderId}`;
        if (key in this.state.allocations) {
            return this.state.allocations[key] || 0;
        }

        else{
            return 'not-exist'
        }
    }

    getTotalQty(product) {
        let allocated = 0;
        for (const bo of this.state.back_orders) {
            allocated += this.getAllocation(product.order_line_id, product.product_id, bo.id);
        }
        return allocated
    }

    getAvailableQty(product) {
        let allocated = 0;
        for (const bo of this.state.back_orders) {
            allocated += this.getAllocation(product.order_line_id, product.product_id, bo.id);
        }
        if (product.total_qty > 0){
            return product.total_qty - allocated;
        }
        else{
            return 0
        }
    }

    async onAllocationChange(productorderlineID,productID, backOrderId, ev) {
        const qty = parseFloat(ev.target.value) || 0;
        if (qty < 0) {
            ev.target.value = 0;
            return;
        }

        // Client-side check: total allocation must not exceed total qty

        //  # Each Purchase Order Line with product is treated seperately whether the product was same or not.

        const product = this.state.products.find(
            (p) => p.order_line_id === productorderlineID
        );

        if (product) {
            let totalAllocated = 0;
            for (const bo of this.state.back_orders) {
                if (bo.id === backOrderId) {
                    totalAllocated += qty;
                } else {
                    totalAllocated += this.getAllocation(productorderlineID, productID, bo.id);
                }
            }
            if (totalAllocated > product.total_qty) {
                this.notification.add(
                    _t(
                        "Total allocated quantity (%(allocated)s) exceeds the back order quantity (%(total)s) for \"%(product)s\".",
                        {
                            allocated: totalAllocated,
                            total: product.total_qty,
                            product: product.display_name,
                        }
                    ),
                    { type: "danger" }
                );
                ev.target.value = this.getAllocation(productorderlineID, productID, backOrderId);
                return;
            }
        }

        this.state.isSaving = true;
        try {
            const data = await this.orm.call(
                "back.order.planning",
                "save_back_order_allocation",
                [this.recordId, productorderlineID, productID, backOrderId, qty]
            );
            this.state.back_orders = data.back_orders || [];
            this.state.products = data.products || [];
            this.state.allocations = data.allocations || {};
        } catch (error) {
            this.notification.add(
                error.message || _t("Failed to save back order allocation."),
                { type: "danger" }
            );
            await this._loadData();
        }
        this.state.isSaving = false;
    }


    formatQty(value) {
        return parseFloat(value) || 0;
    }
}

export const backOrderAllocationMatrix = {
    component: BackOrderAllocationMatrix,
};
registry
    .category("view_widgets")
    .add("back_order_allocation_matrix", backOrderAllocationMatrix);
