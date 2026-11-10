import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import {
    deleteConfirmationMessage,
    ConfirmationDialog,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    getStaticActionMenuItems() {
    console.log("Execuated!!!!")
        const { activeActions } = this.archInfo;
        var duplicate_string = 'Duplicate';

        if (this.props.resModel == 'sale.order'){
            const quoteType = this.model.root.data.quote_type;
            if (quoteType === 'sales_quote'){
                duplicate_string = 'Duplicate'
            }
            else if(quoteType === 'project_quote'){
                duplicate_string = 'Duplicate'
            }

        }
        return {
            archive: {
                isAvailable: () => this.archiveEnabled && this.model.root.isActive,
                sequence: 10,
                description: _t("Archive"),
                icon: "oi oi-archive",
                callback: () => {
                    this.dialogService.add(ConfirmationDialog, this.archiveDialogProps);
                },
            },
            unarchive: {
                isAvailable: () => this.archiveEnabled && !this.model.root.isActive,
                sequence: 20,
                icon: "oi oi-unarchive",
                description: _t("Unarchive"),
                callback: () => this.model.root.unarchive(),
            },
             duplicate: {
                isAvailable: () => {
                console.log("Arrow Execuated!!!!")
                    // Basic permission check
                    if (!activeActions.create || !activeActions.duplicate) {
                    console.log('Basic Permission Check')
                        return false;
                    }

                    // Hide duplicate for sale orders with quote_type = 'project_quote'
                    if (this.props.resModel == 'sale.order') {
                        const quoteType = this.model.root.data.quote_type;
                        const isOldData = this.model.root.data.is_old_data;
                        console.log('---------->',quoteType);
                        console.log('---------->',isOldData);
                        if (!isOldData && (quoteType === 'delivery_stage' || quoteType === 'project_quote')) {
                        console.log('IF QUOUTE TYPE',quoteType);
                            return false;
                        }
                        else if (isOldData && quoteType === 'project_quote') {
                        console.log('IS OLD TYPE',quoteType);
                            return true;
                        }
                        else{
                            console.log('ELSE QUOUTE TYPE',quoteType);
                            return true;
                        }
                    }

                    return true;
                },
                sequence: 30,
                icon: "fa fa-clone",
                description: _t(duplicate_string),
                callback: () => this.duplicateRecord(),
            },
            delete: {
                isAvailable: () => activeActions.delete && !this.model.root.isNew,
                sequence: 40,
                icon: "fa fa-trash-o",
                description: _t("Delete"),
                callback: () => this.deleteRecord(),
                skipSave: true,
            },
            addPropertyFieldValue: {
                isAvailable: () => activeActions.addPropertyFieldValue,
                sequence: 50,
                icon: "fa fa-cogs",
                description: _t("Add Properties"),
                callback: () => this.model.bus.trigger("PROPERTY_FIELD:ADD_PROPERTY_VALUE"),
            },
        };
    }
});