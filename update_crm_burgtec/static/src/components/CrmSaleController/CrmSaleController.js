/** @odoo-module */
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(FormController.prototype, {
    setup() {
        console.log("FORM CONTROLLER PATCHED!!!!!!!!!!!!!!!!!!!");
        super.setup(...arguments);
        const isSaleOrder = this.props?.resModel === 'sale.order';
        if(isSaleOrder){
            this.canCreate = false
        }
    },
});