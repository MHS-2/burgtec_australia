import { _t } from "@web/core/l10n/translation";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";

export class SaleOrderFormController extends FormController {
    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
        console.log('Setup;');
    }

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();

        // Check if we should hide the menu item
        const shouldHideGenerateProject = this._shouldHideGenerateProject();
        const currentRecord = this.model.root;
        const isOldData = currentRecord.data.is_old_data;


        if (!shouldHideGenerateProject) {
            menuItems.newDeliveryStage = {
                sequence: 30,
                icon: "fa fa-clone",
                description: _t('Generate Project'),
                callback: () => this.createDeliveryQuotation(),
            };
        }

        return menuItems;
    }

    _shouldHideGenerateProject() {
        // Check if current record is a sale.order with quote_type === 'delivery_stage'
        const currentRecord = this.model.root;

        // Make sure we have a record and it's saved (has an ID)
        if (!currentRecord || !currentRecord.resId) {
            return false;
        }

        // Check if the model is sale.order
        if (currentRecord.resModel !== 'sale.order') {
            return false;
        }

        // Check the quote_type field value
        const quoteType = currentRecord.data.quote_type;


        return quoteType === 'delivery_stage' || quoteType === 'project_quote';
    }

    async createDeliveryQuotation() {
        console.log('Root RESID', this.model.root.resId);
        console.log('This', this);
        console.log('res from props', this.props.resId);
        const res_id = await this.orm.call("sale.order", "create_new_delivery_stage", [this.model.root.resId]);
        console.log('res', res_id);
        this.viewChildSaleOrder(res_id);
    }

    viewChildSaleOrder(res_id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Child Quotation",
            res_model: "sale.order",
            res_id: res_id,
            views: [
                [false, "form"],
            ],
            context: {
                create: false,
                duplicate: false,
            },
        });
    }
}

registry.category("views").add("new_delivery_stage_form", {
    ...formView,
    Controller: SaleOrderFormController,
});