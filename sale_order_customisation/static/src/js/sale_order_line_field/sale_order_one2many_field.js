import { SaleOrderLineOne2Many } from "@sale/js/sale_order_line_field/sale_order_line_field";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import {  onMounted } from "@odoo/owl";


patch(SaleOrderLineOne2Many.prototype, {

    setup() {
        // console.log('SaleOrderLineOne2Many setup!');
        super.setup();
        this.bus = useService("bus_service");

        onMounted(async () => {
            await this.sendDataToListRenderer();
         });
        
    },

    async sendDataToListRenderer() {
        // console.log('1. About to trigger event at:', new Date().getTime());
        this.bus.trigger("data-for-list-renderer", {
            fieldName: this.props?.name
        });
        // console.log('2. Event triggered at:', new Date().getTime());
    }


});
