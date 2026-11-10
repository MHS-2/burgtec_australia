/** @odoo-module **/

import { Component, onPatched, onMounted, onWillStart, onWillUpdateProps, useState } from '@odoo/owl';
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class CustomColorPicker extends Component {
    static template = "burgtec_back_order.custom_color_picker";
    static components = {};
    static props = {
        ...standardFieldProps,
        name: { type: String, optional: true  },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            'hexcolor': ''
        });
        onMounted(this.ormGetColor);
        onPatched(()=>{
            this.ormGetColor()
        });
    }

    color_pick(ev, record) {
        var color = ev.target.value
        var record = this.props.record;
        const recordId = record.model.config.resId;

        // Update color picker input value
        ev.target.value = color;

        // ORM Call
        this.orm.call("back.order.color", "set_color", [recordId], {
            record_color: color,
        })

        // .then(function(data) {
        //     // You might want to handle the response here if needed
        // })
            
        // // Update row background color
        // ev.target.closest('tr').style.backgroundColor = color;
    }

    color(props) {
        const record = (props && props.record) || this.props.record;
        var self = this;
        const recordId = record.model.config.resId;

        const color = this.orm.call("back.order.color", "get_color", [recordId])

        var colorpicker_checkbox = document.getElementsByClassName('color_picker_checkbox')

        console.log('=====>>',colorpicker_checkbox)

        // Update color picker input value
        let colorPicker = document.querySelector('input[type="color"]');
        if (colorPicker) {
            colorPicker.value = color;
        }
    }

    async ormGetColor(props) {
        const record = (props && props.record) || this.props.record;
        const recordId = record.model.config.resId;
        console.log('------>',recordId);
        const color = await this.orm.call("back.order.color", "get_color", [recordId])
        console.log('------>',color);
        // const res = await this.orm.call("warehouse.receiving", "open_create_backorder_dialog", [Number(warehouseId)], {purchase_order_id: Number(purchaseOrderId)});
        this.state.hexcolor = color;
    }
}

const customcolorpicker = {
  component: CustomColorPicker,
};

registry.category("view_widgets").add("customcolorpicker", customcolorpicker);