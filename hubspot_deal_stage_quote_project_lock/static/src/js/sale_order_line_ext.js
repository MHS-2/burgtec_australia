/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";


patch(ListRenderer.prototype, {

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.bus = useService("bus_service");

    },

    updateDropdowns(stageData) {

    document.querySelectorAll('.o_custom_header_dropdown').forEach(container => {
        const draftPlannedDropdown = container.querySelector('.draft-planned-dropdown');
        const confirmedDropdown = container.querySelector('.confirmed-dropdown');

        if (draftPlannedDropdown && confirmedDropdown) {
            const fieldName = draftPlannedDropdown.dataset.fieldname;
            const stage = stageData[fieldName];
            const frozen = stage.frozen;


            if(frozen) {
                draftPlannedDropdown.value = stage.value;
                draftPlannedDropdown.disabled = stage.frozen
            }

            if (!frozen){


                if (stage && stage.value === 'confirmed') {
                    draftPlannedDropdown.style.display = 'none';
                    confirmedDropdown.style.display = 'block';
                    confirmedDropdown.value = 'confirmed';
                } else {
                    draftPlannedDropdown.style.display = 'block';
                    confirmedDropdown.style.display = 'none';

                     if (stage && (stage.value === 'draft' || stage.value === 'planned' || stage.value === 'new') ) {
                        draftPlannedDropdown.value = stage.value;

                        // Use the disabled flag from backend data
                        draftPlannedDropdown.disabled = stage.disabled || false;
                    } else {
                        draftPlannedDropdown.value = 'draft';
                        draftPlannedDropdown.disabled = false;
                    }
                }

            }

        }
    });
},



});