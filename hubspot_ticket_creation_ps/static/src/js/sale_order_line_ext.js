/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {ListRenderer} from "@web/views/list/list_renderer";
import {useService} from "@web/core/utils/hooks";
import {useState, onWillStart, onWillUpdateProps} from "@odoo/owl";
import {rpc} from "@web/core/network/rpc";

patch(ListRenderer.prototype, {

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.bus = useService("bus_service");

        // this.ticketState = useState({stages: {}});
        this.ticketState = useState({stages: {}, delivery: {}});


        onWillStart(async () => {
            if (this.props.list?.resModel === "planning.screen.line") {
                await this.fetchDoStages();
            }
        });

        onWillUpdateProps(async () => {
            console.log('onwillupdateprops execuated')
            if (this.props.list?.resModel === "planning.screen.line") {
                await this.fetchDoStages();
            }
        });
    },

    async fetchDoStages() {
        super.fetchDoStages();
        const resId = this.props.list?._parent?._config?.resId;
        if (!resId) return;
        try {
             const [data, plannedRefs] = await rpc("/hubspot_ticket_creation_ps/fetch_ticket_data", {
                planning_screen_id: resId,
            });
            console.log(data);
            if (!data || !data.length) return;
            if (!plannedRefs || !plannedRefs.length) return;

            const stageMap = {};
             const plannedRefsMap = {};

            // Map by field_name (e.g. "do_stage_3") not by positional index
            data.forEach((item) => {
                if (item.field_name) {
                    stageMap[item.field_name] = {
                    stage: item.stage ?? "",
                    url: item.url ?? "",
                    dispatch: item.Disp ?? "",
                    deliver: item.Deliver ?? "",
                    install: item.Inst_St ?? "",
                    install_complete: item.Inst_Cmp ?? "",
                    delivery_stage_status: item.delivery_stage_status ?? "",
                };
                }
            });

            plannedRefs.forEach((item) => {
                if (item.field_name) {
                    plannedRefsMap[item.field_name] = {
                        delivery_stage_status: item.delivery_stage_status ?? "",
                    };
                }
            });

            this.ticketState.stages = stageMap;
            this.ticketState.delivery = plannedRefsMap;
            console.log('stage_date',stageMap)
            console.log("Ticket stages loaded:", this.ticketState.stages);

        } catch (err) {
            console.error("Failed to fetch ticket stages:", err);
        }
    },


    getDeliveryStageStatusForColumn(columnName) {
    return this.ticketState.delivery?.[columnName]?.delivery_stage_status ?? "";
},

    getTicketStageForColumn(columnName) {
        return this.ticketState.stages[columnName]?.stage ?? "";  // ← .stage not whole object
    },

    getTicketScheduledDispatchDateForColumn(columnName) {
        return this.ticketState.stages[columnName]?.dispatch ?? "";  // ← .stage not whole object
    },

    getTicketScheduledDeliverDateForColumn(columnName) {
        return this.ticketState.stages[columnName]?.deliver ?? "";  // ← .stage not whole object
    },

    getTicketScheduledInstallDateForColumn(columnName) {
        return this.ticketState.stages[columnName]?.install ?? "";  // ← .stage not whole object
    },

    getTicketScheduledInstallCompleteDateForColumn(columnName) {
        return this.ticketState.stages[columnName]?.install_complete ?? "";  // ← .stage not whole object
    },

    // Add new getter for URL
    getTicketUrlForColumn(columnName) {
        return this.ticketState.stages[columnName]?.url ?? "";
    },


    async onHeaderSelectChange(ev) {
        const select = ev.target;
        if (select.disabled) return;
        debugger;

        const selectedValue = select.value;
        const fieldName = select.dataset.fieldname;
        const match = fieldName.match(/do_stage_(\d+)/);

        if (!match) {
            console.error("Invalid fieldName format:", fieldName);
            return;
        }

        const stageNumber = match[1];                          // e.g. "1"
        const targetField = `do_${stageNumber}_status`;

        try {
            // debugger;
            const recordIds = this.props.list._parent._config.resId;
            console.log(" OVER WRITTEN !!!!");
            // get the return value from Python
            const actionOrData = await this.orm.call("planning.screen", "action_handle_do_stage", [recordIds], {
                selectedValue, fieldName
            });

            if (actionOrData) {
                debugger;
                const ticketExists = await this.orm.call(
                    "planning.screen",
                    "check_existing_ticket",
                    [recordIds],
                    {targetField}
                );

                // Use this.env.uid as the safest fallback
                const userId = this.env.model.config.context.uid;
                const isAdmin = await this.orm.call(
                    "res.users",
                    "has_group",
                    [[userId], "quotation_type_customization.group_planning_screen_admin"]
                );
                if (ticketExists && !isAdmin && selectedValue === 'planned') {
                    this.notification.add("Hubspot Ticket Already Exists !!", {
                        type: "warning",
                        sticky: false,
                    });
                }
            }


            console.log('return', actionOrData);

            // if Python returned an action dict, open it
            if (actionOrData && actionOrData.type === 'ir.actions.act_window') {
                return this.action.doAction(actionOrData);
            }

            if (actionOrData && actionOrData.success) {
                this.notification.add(actionOrData.message, {
                    type: 'success',
                    sticky: false,
                });
            } else {
                this.notification.add(
                    (actionOrData && actionOrData.message)
                        ? actionOrData.message
                        : 'Error while creating Hubspot ticket.',
                    {
                        type: 'danger',
                        sticky: false,
                    }
                );
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
            this.notification.add(errorMsg, {type: "danger"});
            await this.fetchDoStages();
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

                    if (stage && (stage.value === 'draft' || stage.value === 'planned' || stage.value === 'new')) {
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


});