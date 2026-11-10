import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import {
    deleteConfirmationMessage,
    ConfirmationDialog,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import { ListController } from "@web/views/list/list_controller";

patch(ListController.prototype, {

    getStaticActionMenuItems() {
        var duplicate_string = 'Duplicate';

        if (this.props.resModel == 'sale.order'){
            duplicate_string = 'Duplicate Sale Quote'
        }
        return {
            export: {
                isAvailable: () => this.isExportEnable,
                sequence: 10,
                icon: "fa fa-upload",
                description: _t("Export"),
                callback: () => this.onExportData(),
            },
            archive: {
                isAvailable: () => this.archiveEnabled,
                sequence: 20,
                icon: "oi oi-archive",
                description: _t("Archive"),
                callback: () => {
                    this.dialogService.add(ConfirmationDialog, this.archiveDialogProps);
                },
            },
            unarchive: {
                isAvailable: () => this.archiveEnabled,
                sequence: 30,
                icon: "oi oi-unarchive",
                description: _t("Unarchive"),
                callback: () => this.toggleArchiveState(false),
            },
            duplicate: {
                isAvailable: () => this.activeActions.duplicate,
                sequence: 35,
                icon: "fa fa-clone",
                description: _t(duplicate_string),
                callback: () => this.duplicateRecords(),
            },
            delete: {
                isAvailable: () => this.activeActions.delete,
                sequence: 40,
                icon: "fa fa-trash-o",
                description: _t("Delete"),
                callback: () => this.onDeleteSelectedRecords(),
            },
        };
    }

});