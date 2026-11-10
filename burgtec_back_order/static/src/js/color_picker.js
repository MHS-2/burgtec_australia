/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ListController } from '@web/views/list/list_controller';
import { useService } from "@web/core/utils/hooks";

const { onWillStart, useRef, onPatched, onMounted, useState, onWillUpdateProps } = owl;

patch(ListRenderer.prototype, {
    setup() {
        super.setup()
        onWillStart(async () => {
            this.color();
        });
        onWillUpdateProps(async () => {
            this.color();
        });
    },

    color() {
        var current_model = this.props.list.model.env.searchModel.resModel
        var tr_list = document.getElementsByClassName('o_data_row')
        var self = this;

        // console.log('-----><----', current_model)

        if(current_model !== 'planning.screen'){
            return
        }

        this.orm.call("color.picker", "search_read", [], {
            domain: [
                ['res_model', '=', 'back.order.planning'],
            ],
        }).then(function(data) {
            Array.prototype.forEach.call(tr_list, function(tr) {
                data.forEach((item) => {
                    // console.log('ITEM --->',item);
                    if (tr.firstChild.nextElementSibling.dataset.id == item.record_id) {
                        // Update row background color
                        // console.log('===>',tr.firstChild.nextElementSibling.dataset.id)
                        tr.style.backgroundColor = item.color;
                    }
                });
            });
        })
    },

})

