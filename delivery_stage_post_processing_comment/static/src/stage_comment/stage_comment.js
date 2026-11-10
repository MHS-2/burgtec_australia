/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { StageCommentDialog } from "./stage_comment_dialog";

const PS_LINE = "planning.screen.line";
const screenIdOf = (props) => props.list?._parent?._config?.resId;

patch(ListRenderer.prototype, {
    setup() {
        super.setup();
        this._scOrm = useService("orm");
        this._scDialog = useService("dialog");
        this._scNotif = useService("notification");
        this.stageComments = useState({ map: {} });

        onWillStart(() => this._loadStageComments(this.props));
        onWillUpdateProps((next) => {
            // reload only when parent planning.screen changes (pager next/prev)
            if (screenIdOf(next) !== screenIdOf(this.props)) {
                return this._loadStageComments(next);
            }
        });
    },

    async _loadStageComments(props) {
        const screenId = screenIdOf(props);
        if (props.list?.resModel !== PS_LINE || !screenId) {
            this.stageComments.map = {};
            return;
        }
        this.stageComments.map = await this._scOrm.call(
            "planning.screen.stage.comment", "get_comments", [screenId]
        );
    },

    getStageComment(columnName) {
        return this.stageComments?.map[columnName] || "";
    },

    openStageComment(column) {
        const screenId = screenIdOf(this.props);
        if (!screenId) {
            this._scNotif.add(_t("Save the planning screen first."), { type: "warning" });
            return;
        }
        const ref = this.getTicketStageForColumn?.(column.name) || "";
        this._scDialog.add(StageCommentDialog, {
            title: `${column.label}${ref ? " – " + ref : ""} ${_t("– Post Processing Comments")}`,
            comment: this.getStageComment(column.name),
            onSave: async (value) => {
                await this._scOrm.call(
                    "planning.screen.stage.comment", "set_comment",
                    [screenId, column.name, value]
                );
                this.stageComments.map[column.name] = value;
            },
        });
    },
});
