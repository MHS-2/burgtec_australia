import {Component, onWillStart, useState} from "@odoo/owl";
import {rpc} from "@web/core/network/rpc";
import {useService} from "@web/core/utils/hooks"
import {AlertDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {Dialog} from "@web/core/dialog/dialog";
import {CustomDialog} from "@burgtec_online_quotation_link/custom_dialog/custom_dialog";
import {registry} from "@web/core/registry";

export class QuotationReview extends Component {
    static template = "burgtec_online_quotation_link.QuotationReview";
    static props = {token: String};

    setup() {
        // debugger;
        this.notification = useService('notification');
        this.dialog = useService('dialog');

        this.state = useState({
            loading: true,
            error: false,
            validations: '',
            order: {},
            customer: {},
            feedback_totals: {},
            lines: [],
        });
        // selected finishes on page {line_id: {attribute_id: value_id}}, written on Submit Review
        this.selectedFinishes = {};
        onWillStart(() => this._loadOrderDetails());
    }

    async _loadOrderDetails() {
        // debugger;

        try {
            const data = await rpc(`/quote/review/${this.props.token}/data`);
            Object.assign(this.state, data);
            console.log('Data =========>',data)
        } catch {
            this.state.error = "This link is invalid.";
        } finally {
            this.state.loading = false;
        }
    }

    async commentChange(event, line) {
        console.log('ON CHANGEEEEEEE 1');
        const lineId = line;
        const ev = event;
        const comment = ev.target.value;
        await rpc(`/quote/review/${this.props.token}/line/${lineId.id}/comment`, {comment: comment});
    }

    async revisionApproved(line) {
        const lines = [];
        const values = {};
        for (const attribute of line.attributes_and_values) {
            let valueId = false;
            if (this.selectedFinishes[line.id] && this.selectedFinishes[line.id][attribute.id]) {
                valueId = this.selectedFinishes[line.id][attribute.id];
            } else {
                // not changed on page -> keep current value
                const currentValue = attribute.values.find((v) => line.selected_value_ids.includes(v.id));
                if (currentValue) {
                    valueId = currentValue.id;
                } else if (attribute.values.length) {
                    valueId = attribute.values[0].id;
                }
            }
            if (valueId) {
                values[attribute.id] = valueId;
            }
        }
        lines.push({line_id: line.id, values: values});
        await this.confirmDialog(line,"approved",lines)


    }

    async revisionRequired(line) {
        const lines = [];
        const values = {};
        for (const attribute of line.attributes_and_values) {
            let valueId = false;
            if (this.selectedFinishes[line.id] && this.selectedFinishes[line.id][attribute.id]) {
                valueId = this.selectedFinishes[line.id][attribute.id];
            } else {
                // not changed on page -> keep current value
                const currentValue = attribute.values.find((v) => line.selected_value_ids.includes(v.id));
                if (currentValue) {
                    valueId = currentValue.id;
                } else if (attribute.values.length) {
                    valueId = attribute.values[0].id;
                }
            }
            if (valueId) {
                values[attribute.id] = valueId;
            }
        }
        lines.push({line_id: line.id, values: values});
        await this.confirmDialog(line,"revision",lines)
    }

    async confirmDialog(line,type,lines) {
        this.dialog.add(CustomDialog, {
            line: line,
            type : type,
            attribute_values: lines,
            token: this.props.token,
            onConfirmOrCancel: () => this._loadOrderDetails(),
        });
    }


    async viewShopDrawing(line) {
        console.log("Shop drawing for line", line.id);
    }

    async finishChange(event, line, attribute) {
        const valueId = parseInt(event.target.value);
        const attrValueIds = attribute.values.map((v) => v.id);

        // reactive state: keeps the select correct across re-renders
        line.selected_value_ids = [
            ...line.selected_value_ids.filter((id) => !attrValueIds.includes(id)),
            valueId,
        ];

        // keep your existing bookkeeping
        if (!this.selectedFinishes[line.id]) {
            this.selectedFinishes[line.id] = {};
        }
        this.selectedFinishes[line.id][attribute.id] = valueId;
    }

    async submitReview(order) {
        const lines = [];
        for (const line of this.state.lines) {
            if (line.display_type || !line.attributes_and_values || !line.attributes_and_values.length) {
                continue;
            }
            const values = {};
            for (const attribute of line.attributes_and_values) {
                let valueId = false;
                if (this.selectedFinishes[line.id] && this.selectedFinishes[line.id][attribute.id]) {
                    valueId = this.selectedFinishes[line.id][attribute.id];
                } else {
                    // not changed on page -> keep current value
                    const currentValue = attribute.values.find((v) => line.selected_value_ids.includes(v.id));
                    if (currentValue) {
                        valueId = currentValue.id;
                    } else if (attribute.values.length) {
                        valueId = attribute.values[0].id;
                    }
                }
                if (valueId) {
                    values[attribute.id] = valueId;
                }
            }
            lines.push({line_id: line.id, values: values});
        }

        const result = await rpc(`/quote/review/${this.props.token}/submit`, {lines: lines});
        if (result.status === 'error') {
            await this.dialogAlert(result.message);
            return;
        }
        this.selectedFinishes = {};
        this.notification.add('Review Submitted Successfully', {
            title: "Notification",
            type: 'success',
            sticky: false,
        });
        await this._loadOrderDetails();
    }

    async dialogAlert(alertBody) {
        this.dialog.add(AlertDialog, {
            title: 'Alert',
            body: alertBody,
            contentClass: 'text-danger'
        });
    }


}

registry
    .category("public_components")
    .add("burgtec_online_quotation_link.QuotationReview", QuotationReview);
