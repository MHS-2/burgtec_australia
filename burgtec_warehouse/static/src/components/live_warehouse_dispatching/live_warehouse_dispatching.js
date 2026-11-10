/** @odoo-module **/

import { App, Component, __info__, onPatched, onWillStart, onWillUpdateProps, useEffect, useRef, useState, xml } from '@odoo/owl';
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { rpc } from '@web/core/network/rpc';
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";

class DispatchingDialog extends Component {
    static props = {
    //   dispatchingId: Number,
      lineId : Number,
      message: String,
      onConfirmOrCancel: Function,
      close: Function
    }
    static components = { Dialog };
    static template = xml`
        <Dialog size="'md'" title="'Dispatching Check'">
            <p>
            <t t-out="props.message"/>
            </p>
            <t t-set-slot="footer">
                <button class="btn btn-secondary" t-on-click="onCancel">Cancel</button>
            </t>
        </Dialog>
    `;

    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
    }

    async onCancel() {
        let isChecked = false;
        this.notification.add('You canceled the dialog.');
        await this.props.onConfirmOrCancel();
        this.props.close();
    }
}

export class Live_warehouse_dispatching extends Component {
    static template = "burgtec_warehouse.Live_warehouse_dispatching";
    static components = {};
    static props = {
        ...standardFieldProps,
        name: { type: String, optional: true  },
        record: { type: Object, optional: true },
        "*": true,
    };

    setup() {
      this.notification = useService("notification");
      this.dialog = useService("dialog");
      this.orm = useService("orm");
      this._loadedWriteDate = null;
      this._isLoadingData = false;
      this.state = useState({
            dispatching_complete_data: {
                complete_data: [],
            },
        });

      onWillStart(async () => {
            this._loadData();
        });

      onWillUpdateProps(async () => {
            this._loadData();
        });

    }

    async _loadData(props) {
        const record = (props && props.record) || this.props.record;
        const recordId = record.model.config.resId;

        try {
          const data = await rpc('/burgtec_warehouse/fetch_dispatch_data', {
                warehouse_dispatching_id: recordId
            });

            if(data){
              this.state.dispatching_complete_data = data
            }
        } catch (error) {
            console.error("Error loading stage items data:", error);
        }
    }

    async onChangeDispatch(event) {
      const lineId = event.target.dataset.lineId;
      const isChecked = event.target.checked;
      await this.ormUpdateIsDispatchedField(lineId,isChecked);
    }

    async onChangeDeliver(event) {
      const lineId = event.target.dataset.lineId;
      const isChecked = event.target.checked;
      const message = 'A product cannot be delivered until it is dispatched!';
      const response = await this.ormUpdateIsDeliveredField(lineId,isChecked);
      if (isChecked && !response){
          await this.dispatchingCheckdialog(message,Number(lineId));
        }
      
    }

    async dispatchingCheckdialog(message,lineId){
        this.dialog.add(DispatchingDialog,  {
                // dispatchingId: Number(dispatchingId),
                lineId : lineId,
                message: message || '',
                onConfirmOrCancel: () => this._loadData(),
            });
    }

    async ormUpdateIsDispatchedField(lineId, isChecked) {
      const res = await this.orm.call("warehouse.dispatching.line", "set_is_dispatched", [Number(lineId)], { value: isChecked });
      this._loadData();
    }

    async ormUpdateIsDeliveredField(lineId, isChecked) {
      const res = await this.orm.call("warehouse.dispatching.line", "set_is_delivered", [Number(lineId)], { value: isChecked });
      this._loadData();
      return res
    }
}

const liveWarehouseDispatching = {
  component: Live_warehouse_dispatching,
};

registry.category("view_widgets").add("live_warehouse_dispatching", liveWarehouseDispatching);