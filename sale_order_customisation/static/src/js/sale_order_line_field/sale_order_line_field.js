import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";
const { useState } = owl
import {  onMounted } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

patch(ListRenderer.prototype, {
    
    setup() {
        // console.log('ListRenderer Setup ----->');
        
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
         this.notification = useService("notification");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.bus = useService("bus_service");
        this.state = useState({
            customButtons: false,
            disable: false,
            fieldName: 'N/A',
        });
    //    console.log('Props',this.props);
    //    console.log('Props List',this.props.list);
    //    console.log('Res Model',this.props.list?.resModel);
    //    console.log('Parent Res Model',this.props.list?._parent?.resModel);
    //    console.log('State Custom Buttons Before',this.state.customButtons);
    //    console.log('Props list', this.props.list._parent.resModel);
//        console.log('Res Model', this.props.list.resModel);
//        console.log('Res Model', this.props.list.relationField);
//        console.log('String', this.props.archInfo.xmlDoc.attributes[0]);

               // Check if this is a sale.order.line list view inside sale.order form
        const isSaleOrderLine = this.props.list?.resModel === 'sale.order.line';
        const isSaleOrder = this.props.list?._parent?.resModel === 'sale.order';

        // Check if this is a split.do.line list view inside split.do form
        const isPlanningScreenLine = this.props.list?.resModel === 'planning.screen.line';
        const isPlanningScreen = this.props.list?._parent?.resModel === 'planning.screen';

        


        if (isSaleOrderLine && isSaleOrder) {
            console.log('State Custom Buttons Before',this.state.customButtons);
            this.state.customButtons = true;
            this.bus.addEventListener("data-for-list-renderer", this.handleData.bind(this));
        }

        // console.log('State Custom Buttons After',this.state.customButtons);
        
          onMounted(async () => {
            if (isPlanningScreenLine && isPlanningScreen) {
                await this.fetchDoStages();
            }
         });


         
    },

    handleData(event) {
        // console.log('3. handleData called at:', new Date().getTime(), event);
        const { fieldName } = event.detail;
        // console.log('4. FIELDNAME ------>', fieldName);
        
        if (fieldName === 'filtered_order_line_ids') {
            this.state.fieldName = 'filtered_order_line_ids';
        } else if (fieldName === 'down_payment_order_line_ids') {
            this.state.fieldName = 'down_payment_order_line_ids';
        } else {
            this.state.fieldName = 'other';
        }
        // console.log('5. Updated fieldName to:', this.state.fieldName);
        // Force a re-render to make sure the template updates
        this.render();
    },

    async fetchDoStages() {


        try {
            const recordIds = this.props.list._parent._config.resId;
            const stageData = await this.orm.call("planning.screen", "fetch_do_stages", [recordIds], {});
            this.updateDropdowns(stageData);
            return stageData;
        } catch (err) {
            console.error('Error fetching stages:', err);
        }
    },
    updateDropdowns(stageData) {

    document.querySelectorAll('.o_custom_header_dropdown').forEach(container => {
        const draftPlannedDropdown = container.querySelector('.draft-planned-dropdown');
        const confirmedDropdown = container.querySelector('.confirmed-dropdown');

        if (draftPlannedDropdown && confirmedDropdown) {
            const fieldName = draftPlannedDropdown.dataset.fieldname;
            const stage = stageData[fieldName];

            if (stage && stage.value === 'confirmed') {
                draftPlannedDropdown.style.display = 'none';
                confirmedDropdown.style.display = 'block';
                confirmedDropdown.value = 'confirmed';
            } else {
                draftPlannedDropdown.style.display = 'block';
                confirmedDropdown.style.display = 'none';

                 if (stage && (stage.value === 'draft' || stage.value === 'planned')) {
                    draftPlannedDropdown.value = stage.value;

                    // Use the disabled flag from backend data
                    draftPlannedDropdown.disabled = stage.disabled || false;
                } else {
                    draftPlannedDropdown.value = 'draft';
                    draftPlannedDropdown.disabled = false;
                }
            }
        }
    });
},

//async onHeaderSelectChange(ev) {
//    const select = ev.target;
//    if (select.disabled) return;
//
//    const selectedValue = select.value;
//    const fieldName = select.dataset.fieldname;
//
//    try {
//        const recordIds = this.props.list._parent._config.resId;
//
//        // get the return value from Python
//        const actionOrData = await this.orm.call("split.do", "action_handle_do_stage", [recordIds], {
//            selectedValue, fieldName
//        });
//        console.log('return',actionOrData)
//
//        // if Python returned an action dict, open it
//        if (actionOrData && actionOrData.type === 'ir.actions.act_window') {
//    // open the action and exit early
//             return this.action.doAction(actionOrData);
//        }
//        await this.props.list.model.load();
//        await this.fetchDoStages();
//    } catch (err) {
//        this.notification.add(err.message || "Error updating stage", { type: "danger" });
//        await this.fetchDoStages();
//    }
//},
async onHeaderSelectChange(ev) {
    const select = ev.target;
    if (select.disabled) return;

    const selectedValue = select.value;
    const fieldName = select.dataset.fieldname;

    try {
        const recordIds = this.props.list._parent._config.resId;

        // get the return value from Python
        const actionOrData = await this.orm.call("planning.screen", "action_handle_do_stage", [recordIds], {
            selectedValue, fieldName
        });
        console.log('return', actionOrData);

        // if Python returned an action dict, open it
        if (actionOrData && actionOrData.type === 'ir.actions.act_window') {
            return this.action.doAction(actionOrData);
        }

        await this.props.list.model.load();
        await this.fetchDoStages();

    } catch (err) {
        // Comprehensive debug logging
        console.log('err.message:', err.message);
        // Extract the actual message from Python UserError with multiple fallbacks
        let errorMsg = "Error updating stage"; // default fallback

        // Try different paths where the UserError message might be located
        if (err.data && err.data.message) {
            errorMsg = err.data.message;
            console.log('Found error message in err.data.message:', errorMsg);
        } else if (err.message && typeof err.message === 'object') {
            if (err.message.data && err.message.data.message) {
                errorMsg = err.message.data.message;
                console.log('Found error message in err.message.data.message:', errorMsg);
            } else if (err.message.data && err.message.data.arguments && err.message.data.arguments.length > 0) {
                errorMsg = err.message.data.arguments[0];
                console.log('Found error message in err.message.data.arguments[0]:', errorMsg);
            } else if (err.message.message) {
                errorMsg = err.message.message;
                console.log('Found error message in err.message.message:', errorMsg);
            }
        } else if (typeof err.message === 'string') {
            errorMsg = err.message;
            console.log('Found error message in err.message (string):', errorMsg);
        }

        // Additional checks for nested error structures
        if (err.cause && err.cause.message) {
            errorMsg = err.cause.message;
            console.log('Found error message in err.cause.message:', errorMsg);
        }

        // Check if it's a validation error with specific format
        if (err.data && err.data.name === 'odoo.exceptions.UserError' && err.data.arguments) {
            errorMsg = err.data.arguments[0] || errorMsg;
            console.log('Found UserError in err.data.arguments[0]:', errorMsg);
        }

        // show as notification
        this.notification.add(errorMsg, { type: "danger" });
        await this.fetchDoStages();
    }
},

    async addCode(record) {
        try {
            // let list_view = await this.orm.searchRead("ir.model.data", [['name', '=', 'sale_order_line_wizard_add_code_form_view']], ['res_id'])
            const view_id = await this.orm.call(
                "sale.order.line",
                "get_add_code_form_view_id",
                []
            );

            const result = await this.orm.call(
                "sale.order.line", 
                "action_show_wizard_to_add_code", 
                [record.resId]
            );
            
            if (result) {
                const action = {
                    ...result,
                    context: {active_id: record.resId, 'dialog_size': 'extra-large',},
                    views: [[view_id, 'form']],
                    // views: [[list_view.length > 0 ? list_view[0].res_id : false, 'form']],
                    target: 'new',
                }
                await this.action.doAction(action, {
                    onClose: () => this.env.model.root.load()
                });

            }
        } catch (error) {
            console.error("Error opening wizard:", error);
            throw error;
        }
    },

    async swapGroup(record) {
        console.log("Record", record.data);
        console.log("Order ID", record.data.order_id[0]);
        try {
            // let list_view = await this.orm.searchRead("ir.model.data", [['name', '=', 'sale_order_line_wizard_swap_group_form_view']], ['res_id'])

            const view_id = await this.orm.call(
                "sale.order.line",
                "get_swap_group_form_view_id",
                []
            );
            
            const result = await this.orm.call(
                "sale.order.line", 
                "action_show_wizard_to_swap_groups", 
                [record.resId]
            );
            
            if (result) {
                const action = {
                    ...result,
                    context: {active_id: record.resId, '': 'extra-large','default_active_group_id': record.resId, 'default_sale_order_id': record.data.order_id[0],},
                    views: [[view_id, 'form']],
                    // views: [[list_view.length > 0 ? list_view[0].res_id : false, 'form']],
                    target: 'new',
                }
                await this.action.doAction(action, {
                    onClose: () => this.env.model.root.load()
                });

            }
        } catch (error) {
            console.error("Error opening wizard:", error);
            throw error;
        }
    },

    async addProduct(record) {
        try {
            // let list_view = await this.orm.searchRead("ir.model.data", [['name', '=', 'sale_order_line_wizard_add_product_form_view']], ['res_id'])
             const view_id = await this.orm.call(
                "sale.order.line",
                "get_add_product_form_view_id",
                []
            );
            const result = await this.orm.call(
                "sale.order.line", 
                "action_show_wizard_to_add_product", 
                [record.resId]
            );
            
            if (result) {
                const action = {
                    ...result,
                    context: {active_id: record.resId, 'dialog_size': 'extra-large', default_sale_order_id: record.data.order_id[0]},
                    views: [[view_id, 'form']],
                    target: 'new',
                }
                await this.action.doAction(action, {
                    onClose: () => this.env.model.root.load()
                });

            }
        } catch (error) {
            console.error("Error opening wizard:", error);
            throw error;
        }
    },

    async swapCode(record) {
        console.log("Record", record.data);
        console.log("Order ID", record.data.order_id[0]);
        try {
            // let list_view = await this.orm.searchRead("ir.model.data", [['name', '=', 'sale_order_line_wizard_swap_code_form_view']], ['res_id'])

            const view_id = await this.orm.call(
                "sale.order.line",
                "get_swap_code_form_view_id",
                []
            );
            const result = await this.orm.call(
                "sale.order.line", 
                "action_show_wizard_to_swap_codes", 
                [record.resId]
            );
            
            if (result) {
                const action = {
                    ...result,
                    context: {active_id: record.resId, 'dialog_size': 'extra-large','default_active_code_id': record.resId, 'default_sale_order_id': record.data.order_id[0],},
                    views: [[view_id, 'form']],
                    target: 'new',
                }
                await this.action.doAction(action, {
                    onClose: () => this.env.model.root.load()
                });

            }
        } catch (error) {
            console.error("Error opening wizard:", error);
            throw error;
        }
    },
});