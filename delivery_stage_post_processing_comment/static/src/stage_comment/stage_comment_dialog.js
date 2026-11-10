/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class StageCommentDialog extends Component {
    static template = "delivery_stage_post_processing_comment.StageCommentDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        title: String,
        comment: { type: String, optional: true },
        onSave: Function,
    };

    setup() {
        this.state = useState({
            editing: !this.props.comment, // empty -> open directly in edit mode
            value: this.props.comment || "",
            saving: false,
        });
    }

    async save() {
        this.state.saving = true;
        try {
            await this.props.onSave(this.state.value);
            this.props.close();
        } catch (e) {
            this.state.saving = false;
            throw e;
        }
    }
}
