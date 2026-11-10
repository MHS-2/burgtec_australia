/** @odoo-module */

import { Component, useState, useEffect, useRef, onWillUpdateProps, onPatched, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class AreaAllocationMatrix extends Component {
    static template = "sale_area_allocation.AreaAllocationMatrix";
    static props = {
        record: { type: Object, optional: true },
        "*": true,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            areas: [],
            products: [],
            allocations: {},
            isLoading: true,
            isSaving: false,
        });
        this._lastLoadKey = null;

         // Track last-loaded write_date to detect saves
        this._loadedWriteDate = null;
        this._isLoadingData = false;

        // useEffect watches reactive dependencies and re-runs when they change.
        // record.resId changes when form switches records or after first save.
        // record.data.number_of_areas changes when user edits and saves.
        // record.data.order_line triggers when order lines change.
        useEffect(
            () => {
                this._loadData();
            },
            () => {
                const rec = this.props.record;
                if (!rec) return [null, null, null];
                // Access reactive properties so OWL tracks them
                const resId = rec.resId;
                const numAreas = rec.data.number_of_areas;
                // For order_line One2many, access .records.length to track changes
                let lineCount = 0;
                try {
                    const ol = rec.data.order_line;
                    lineCount = ol && ol.records ? ol.records.length : 0;
                } catch {
                    lineCount = 0;
                }
                return [resId, numAreas, lineCount];
            }
        );

        onWillStart(async () => {
            console.log("On Will Start Executed:");
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
        const numAreas = record.data.number_of_areas || 0;
        this.state.currentarea = numAreas;
        const loadKey = `${recordId}_${numAreas}`;
        this._lastLoadKey = loadKey;

        try {
            const data = await this.orm.call(
                "sale.order",
                "get_area_matrix_data",
                [recordId]
            );
            // Only apply if this is still the latest load request
            if (this._lastLoadKey === loadKey) {
                this.state.areas = data.areas || [];
                this.state.products = data.products || [];
                this.state.allocations = data.allocations || {};
                this.state.isLoading = false;
                // Record the write_date we loaded data for, so onPatched
                // doesn't trigger another reload for the same save.
                this._loadedWriteDate = record.data.write_date;
            }
        } catch (error) {
            this.state.isLoading = false;
            console.error("Error loading area matrix data:", error);
        }
    }

    getAllocation(orderlineID, productID, areaId) {
        
        // const key = `${productID}_${areaId}`;
        
        //  # Each Sale Order Line with product is treated seperately whether the product was same or not.

        const key = `${orderlineID}_${areaId}`;
        return this.state.allocations[key] || 0;
    }

    getAvailableQty(product) {
        let allocated = 0;
        for (const area of this.state.areas) {
            allocated += this.getAllocation(product.order_line_id, product.product_id, area.id);
        }
        return product.total_qty - allocated;
    }

    async onAllocationChange(productorderlineID,productID, areaId, ev) {
        const qty = parseFloat(ev.target.value) || 0;
        if (qty < 0) {
            ev.target.value = 0;
            return;
        }

        // Client-side check: total allocation must not exceed total qty

        // const product = this.state.products.find(
        //     (p) => p.product_id === productID
        // );

        //  # Each Sale Order Line with product is treated seperately whether the product was same or not.

        const product = this.state.products.find(
            (p) => p.order_line_id === productorderlineID
        );

        if (product) {
            let totalAllocated = 0;
            for (const area of this.state.areas) {
                if (area.id === areaId) {
                    totalAllocated += qty;
                } else {
                    totalAllocated += this.getAllocation(productorderlineID, productID, area.id);
                }
            }
            if (totalAllocated > product.total_qty) {
                this.notification.add(
                    _t(
                        "Total allocated quantity (%(allocated)s) exceeds the order quantity (%(total)s) for \"%(product)s\".",
                        {
                            allocated: totalAllocated,
                            total: product.total_qty,
                            product: product.display_name,
                        }
                    ),
                    { type: "danger" }
                );
                ev.target.value = this.getAllocation(productorderlineID, productID, areaId);
                return;
            }
        }

        this.state.isSaving = true;
        try {
            const data = await this.orm.call(
                "sale.order",
                "save_area_allocation",
                [this.recordId, productorderlineID, productID, areaId, qty]
            );
            this.state.areas = data.areas || [];
            this.state.products = data.products || [];
            this.state.allocations = data.allocations || {};
        } catch (error) {
            this.notification.add(
                error.message || _t("Failed to save allocation."),
                { type: "danger" }
            );
            await this._loadData();
        }
        this.state.isSaving = false;
    }

    async onAreaNameChange(areaId, ev) {
        const name = ev.target.value.trim();
        if (!name) {
            const area = this.state.areas.find((a) => a.id === areaId);
            ev.target.value = area ? area.name : "";
            return;
        }

        try {
            await this.orm.call(
                "sale.order",
                "save_area_name",
                [this.recordId, areaId, name]
            );
            const area = this.state.areas.find((a) => a.id === areaId);
            if (area) {
                area.name = name;
            }
        } catch (error) {
            this.notification.add(
                _t("Failed to update area name."),
                { type: "danger" }
            );
        }
    }

    formatQty(value) {
        return parseFloat(value) || 0;
    }
}

export const areaAllocationMatrix = {
    component: AreaAllocationMatrix,
};
registry
    .category("view_widgets")
    .add("area_allocation_matrix", areaAllocationMatrix);
