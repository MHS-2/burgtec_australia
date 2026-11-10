import {Component} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";
import {useService} from "@web/core/utils/hooks";
import {rpc} from "@web/core/network/rpc";


export class CustomDialog extends Component {
    static props = {line: Object, type: String, attribute_values: Array, token: String, onConfirmOrCancel: Function, close: Function};
    static components = {Dialog,};
    static template = "burgtec_online_quotation_link.customDialog";

    setup() {
        this.notification = useService('notification');
    };

    async onConfirm() {
        const lineId = this.props.line.id;
        const type = this.props.type;
        const attributeValues = this.props.attribute_values;
        if (type === 'approved') {
            await rpc(`/quote/review/${this.props.token}/line/${lineId}/feedback`, {feedback: 'approve', attribute_values: attributeValues})
            await this.notifiySticky('Status Set To Approved', 'success')
            await this.props.onConfirmOrCancel();
            this.props.close();
        } else if (type === 'revision') {
            await rpc(`/quote/review/${this.props.token}/line/${lineId}/feedback`, {feedback: 'rev_required', attribute_values: attributeValues})
            await this.notifiySticky('Status Set To Revision Required', 'warning')
            await this.props.onConfirmOrCancel();
            this.props.close();
        }

    };

    async onCancel() {
        const lineId = this.props.line.id;
        this.notification.add('Dialog Canceled !')
        await this.props.onConfirmOrCancel();
        this.props.close();
    };

    async notifiySticky(msg, type) {
        this.notification.add(msg, {
            title: "Notification",
            type: type,
            sticky: false,
        });
    }

}

