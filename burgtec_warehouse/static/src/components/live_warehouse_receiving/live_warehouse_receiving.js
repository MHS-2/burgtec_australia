/** @odoo-module **/

import { App, Component, __info__, onPatched, onWillStart, onWillUpdateProps, useEffect, useRef, useState, xml } from '@odoo/owl';
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { rpc } from '@web/core/network/rpc';
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";

class PickingManageDialog extends Component {
    static props = { 
          warehouseId : Number,
          purchaseOrderId : Number,
          pickingData : Object,
          close: Function,
          onConfirmed: Function,
        }
    static components = { Dialog };
    static template = xml`
        <Dialog size="'xl'" title="'Picking Management For Back Order'">
            <t t-foreach="props.pickingData" t-as="pick" t-key="pick.picking_id">
                <div class="row mb-2">
                  <div class="col-6">
                      <span class="mb-2">
                        Picking Name: 
                        <strong>
                          <t t-out="pick.picking_name"/>
                        </strong>
                      </span>
                      <br/>
                      <span class="mb-2">
                        Picking Source:
                        <strong>
                          <t t-out="pick.picking_source"/>
                        </strong>
                      </span>
                      <br/>
                      <span class="mb-2">
                        Picking State:
                        <strong t-att-class="'badge rounded-pill ' + pick.state_badge_class">
                          <t t-out="pick.state"/>
                        </strong>
                      </span>
                  </div>
                </div>
                <div style="overflow-x: auto;">
                  <table class="product-table">
                      <thead>
                          <tr>
                              <th width="50%">Product</th>
                              <th width="15%">Demand Qty</th>
                              <th width="20%">Received Qty</th>
                              <th width="15%">State</th>
                          </tr>
                      </thead>
                      <tbody>
                          <t t-foreach="pick.stock_move_lines" t-as="move" t-key="move.id">
                              <tr>
                                  <td data-label="Product Name" style="white-space: break-spaces; text-align:left;"><t t-out="move.product_name"/></td>
                                  <td data-label="Product Code" style="white-space: break-spaces;"><t t-out="move.demanded_qty"/></td>
                                  <td data-label="Quantity" style="white-space: break-spaces;"><t t-out="move.warehouse_line_received_quantity"/></td>
                                  <td data-label="State">
                                    <span t-att-class="'badge rounded-pill ' + move.state_badge_class">
                                      <t t-out="move.state"/>
                                    </span>
                                  </td>

                              </tr>
                          </t>
                      </tbody>
                  </table>
              </div>
            </t>
            <t t-set-slot="footer">
                <button class="btn btn-primary" t-on-click="onConfirm">Confirm</button>
                <button class="btn btn-secondary" t-on-click="onCancel">Cancel</button>
            </t>
        </Dialog>
    `;

    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.state = useState({
              pickings_data: {
                    picking_id: false,
                    picking_name :'',
                    picking_source: '',
                    state:'',
                    stock_move_lines: [],
                },
        })

        this.state = this.props.pickingData;

    }

    async onConfirm() {
        await this.confirmCreateBackOrder(this.props.warehouseId,this.props.purchaseOrderId, this.props.pickingData);
        this.notification.add('Back Order Created Successfully!', {
                    type: "success",
                });
        await this.props.onConfirmed();
        this.props.close();
    }

    async onCancel() {
        this.notification.add('You canceled the dialog.');
        this.props.close();
    }

    async confirmCreateBackOrder(warehouseId,purchaseOrderId,pickingData) {
      const res = await this.orm.call("warehouse.receiving", "create_backorder", [warehouseId], {purchase_order_id: purchaseOrderId, picking_data : pickingData,});
    }
}
//#endregion

class QtyReceivedDialog extends Component {
    static props = {
      warehouseId: Number,
      lineId : Number,
      message: String,
      expectedQty : Number,
      receivedQty : Number,
      purchaseOrderId : Number,
      isZeroQty : Boolean,
      isFullReceived : Boolean,
      onConfirmOrCancel: Function,
      close: Function
    }
    static components = { Dialog };
    static template = xml`
        <Dialog size="'md'" title="'Quantity Receive Check'">
            <p>
            <t t-out="props.message"/>
            </p>
            <t t-set-slot="footer">
                <t t-if="!props.isZeroQty">
                  <button class="btn btn-primary" t-on-click="onConfirm">Confirm</button>
                </t>
                <!-- <t t-elif="!props.isZeroQty">
                  <button class="btn btn-primary" t-on-click="onCreateBackOrder">Create Back Order</button>
                </t> -->
                <button class="btn btn-secondary" t-on-click="onCancel">Cancel</button>
            </t>
        </Dialog>
    `;

    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
    }

    async onConfirm() {
        let isChecked = true;
        await this.ormUpdateIsReceivedField(this.props.lineId,isChecked)
        // This method will be executed to see if all demand is received to validate picking.
        const picking_res = await this.ormAutoValidatePicking(this.props.warehouseId,this.props.purchaseOrderId);
        if (picking_res){
                this.notification.add('All received products have been validated successfully!.',{
                    type: "success",
                });  
        }
        this.notification.add('You confirmed the dialog.',{
                    type: "success",
                });
        await this.props.onConfirmOrCancel();
        this.props.close();
    }

    async onCancel() {
        let isChecked = false;
        await this.ormUpdateIsReceivedField(this.props.lineId,isChecked)
        this.notification.add('You canceled the dialog.');
        await this.props.onConfirmOrCancel();
        this.props.close();
    }

    async ormAutoValidatePicking(warehouseId,purchaseOrderId){
      const res = await this.orm.call("warehouse.receiving", "auto_validate_picking", [Number(warehouseId)], { purchase_order_id: purchaseOrderId})
      return res
    }

    async ormUpdateIsReceivedField(lineId, isChecked) {
      const res = await this.orm.call("warehouse.receiving.line", "set_is_received", [Number(lineId)], { value: isChecked });
      // this.props.loadData();
    }
}
//#endregion

export class Live_warehouse_receiving extends Component {
    static template = "burgtec_warehouse.Live_warehouse_receiving";
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
      this.vidStream = null;  // Store video stream reference
      this.currentModal = null;  // Store current modal reference
      this._loadedWriteDate = null;
      this._isLoadingData = false;
      this.state = useState({
            warehouse_complete_data: {
                warehouse_id: false,
                purchase_id :false,
                delivery_quote: '',
                delivery_code:'',
                delivery_location:'',
                client_name: '',
                project_quote: '',
                complete_data: [],
            },
            cameraFacingMode: 'environment', // 'user' for front, 'environment' for back
            availableCameras: [],
        });

      onWillStart(async () => {
            this._loadData();
        });

      onWillUpdateProps(async () => {
            this._loadData();
        });

      // onPatched(() => {
      //       const rec = this.props.record;
      //       if (!rec || !rec.resId) return;
      //       const currentWriteDate = rec.data.write_date;
      //       if (currentWriteDate && currentWriteDate !== this._loadedWriteDate) {
      //           console.log('PATCHED!!');
      //           this._loadData();
      //       }
      //   });

    }

    async _loadData(props) {
        const record = (props && props.record) || this.props.record;
        const recordId = record.model.config.resId;

        try {
          const data = await rpc('/burgtec_warehouse/fetch_stage_items', {
                warehouse_receiving_id: recordId
            });

            if(data){
              this.state.warehouse_complete_data = data
            }
        } catch (error) {
            console.error("Error loading stage items data:", error);
        }
    }


    async onChangeReceive(event,line) {
        const warehouseId = line.warehouse_id;
        var message = ''
        const lineId = line.line_id;
        const isChecked = event.target.checked;
        let isZeroQty = false;
        let isFullReceived = false;

        if (isChecked && line.received_qty == 0){
          message = `Zero Quantity Received!`
          isZeroQty = true
        }

        else if (isChecked && line.received_qty === line.product_qty){
          isFullReceived = true
          message = `Full Quantity Is Received.`
        }

        else if(isChecked && line.received_qty < line.product_qty){
          message = `Partial Quantity Is Received. \n ${line.received_qty} quantity received from ${line.product_qty}.`
        }

        if (!isChecked){
          await this.ormUpdateIsReceivedField(lineId,isChecked);
        }

        if (isChecked){
          await this.qtyReceiveCheckingdialog(message,line,isZeroQty,isFullReceived,warehouseId);
        }
    }

    async qtyReceiveCheckingdialog(message,line,isZeroQty,isFullReceived,warehouseId){
        this.dialog.add(QtyReceivedDialog,  {
                warehouseId: Number(warehouseId),
                lineId : line.line_id,
                message: message || '',
                expectedQty : line.product_qty,
                receivedQty : line.received_qty,
                purchaseOrderId : line.purchase_order_id,
                isZeroQty : isZeroQty,
                isFullReceived : isFullReceived,
                onConfirmOrCancel: () => this._loadData(),
            });
    }

    async onChangeStage(event) {
      const lineId = event.target.dataset.lineId;
      const isChecked = event.target.checked;
      await this.ormUpdateIsStagedField(lineId,isChecked);
    }

    async onChangeDispatch(event) {
      const lineId = event.target.dataset.lineId;
      const isChecked = event.target.checked;
      await this.ormUpdateIsDispatchedField(lineId,isChecked);
    }

    async onChangeDeliver(event) {
      const lineId = event.target.dataset.lineId;
      const isChecked = event.target.checked;
      await this.ormUpdateIsDeliveredField(lineId,isChecked);
    }

    async onReceivedQtyChange(event,line){
      const lineId = line.line_id;
      const receivedQty = event.target.value;
      var alertBody= '';
      if(receivedQty < 0.0){
        alertBody = 'Received Qty should not be less than 0.'
        await this.dialogAlert(alertBody)
      }
      else if(receivedQty > line.product_qty){
        alertBody = 'Received Quantity should not be greater than the expected quantity.'
        await this.dialogAlert(alertBody)
      }
      else{
        await this.ormUpdateReceivedQtyField(lineId,receivedQty);
      }
    }

    async ormUpdateIsReceivedField(lineId, isChecked) {
      const res = await this.orm.call("warehouse.receiving.line", "set_is_received", [Number(lineId)], { value: isChecked });
      this._loadData();
    }

    async ormUpdateIsStagedField(lineId, isChecked) {
      const res = await this.orm.call("warehouse.receiving.line", "set_is_staged", [Number(lineId)], { value: isChecked });
      this._loadData();
    }

    async ormUpdateIsDispatchedField(lineId, isChecked) {
      const res = await this.orm.call("warehouse.receiving.line", "set_is_dispatched", [Number(lineId)], { value: isChecked });
      this._loadData();
    }

    async ormUpdateIsDeliveredField(lineId, isChecked) {
      const res = await this.orm.call("warehouse.receiving.line", "set_is_delivered", [Number(lineId)], { value: isChecked });
      this._loadData();
    }

    async ormUpdateReceivedQtyField(lineId, receivedQty) {
      const res = await this.orm.call("warehouse.receiving.line", "set_received_qty", [Number(lineId)], { value: Number(receivedQty) });
      await this._loadData();
    }

    async dialogAlert(alertBody){
          this.dialog.add(AlertDialog, {
              title: 'Alert',
              body: alertBody,
              contentClass: 'text-danger'
          });
      }

    
      onClickCamera(){
            // Find the closest modal to the clicked camera button
            const button = event.target.closest('#camera_button') || event.target.closest('button[id="camera_button"]');
            if (button) {
                // Find the modal in the parent product-section
                const productSection = button.closest('.product-section');
                if (productSection) {
                    this.currentModal = productSection.querySelector('.custom-modal');
                    if (this.currentModal) {
                        this.currentModal.style.display = "block";
                        this.startVideoStream();
                    }
                }
            }
      }

      async startVideoStream() {
            let All_mediaDevices = navigator.mediaDevices;
            try {
                const constraints = {
                    audio: false,
                    video: {
                        facingMode: this.state.cameraFacingMode,
                        width: { ideal: 1920 },
                        height: { ideal: 1440 },
                        aspectRatio: { ideal: 4/3 }
                    }
                };
                
                const vidStream = await All_mediaDevices.getUserMedia(constraints);
                this.vidStream = vidStream;
                
                // Get video element from currentModal
                const video = this.currentModal.querySelector('#videoCam');
                if ("srcObject" in video) {
                   video.srcObject = vidStream;
                } else {
                   video.src = window.URL.createObjectURL(vidStream);
                }
                
                video.onloadedmetadata = function(e) {
                   video.play();
                };
            } catch(e) {
                // console.log(e.name + ": " + e.message);
                this.dialogAlert(`Camera Error: ${e.message}`);
            }
      }

      toggleCamera() {
            // Switch between 'user' (front) and 'environment' (back)
            this.state.cameraFacingMode = this.state.cameraFacingMode === 'user' ? 'environment' : 'user';
            
            // Stop current stream
            if(this.vidStream) {
                this.vidStream.getTracks().forEach(function(track) {
                    track.stop();
                });
                this.vidStream = null;
            }
            
            // Start new stream with different camera
            this.startVideoStream();
      }

    stopVideoStream(){
        if(this.vidStream) {
            this.vidStream.getTracks().forEach(function(track) {
                track.stop();
            });
            this.vidStream = null;
        }
        if(this.currentModal) {
            this.currentModal.style.display = "none";
        }
    }
    /**
    Capture the image
    **/
    ImageCapture(){
        const warehouseId = event.target.dataset.warehouseId;
        const purchaseOrderId = event.target.dataset.purchaseId;
        
        // Get canvas element from currentModal
        const canvas = this.currentModal.querySelector('#canvas');
        const video = this.currentModal.querySelector('#videoCam');
        
        // Draw video to canvas with full resolution
        let ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Get base64 image data with high quality JPEG (0.95 = 95% quality)
        let image_data_url = canvas.toDataURL('image/jpeg', 0.95);
        // Extract only the base64 part (remove data:image/jpeg;base64, prefix)
        const base64Image = image_data_url.split(',')[1];

        this.ormCreateAndAttach(warehouseId, purchaseOrderId, base64Image);
        
        // Stop the video stream
        this.stopVideoStream();

        // Notify User That Image Was Successfully Uploaded.
        // this.notifSticky('Image Uploaded!')
        this.ormGetPurchaseOrderReference(purchaseOrderId).then((purchaseRef) => {

            this.notifSticky(
                `Image Uploaded To The Following Purchase Order ${purchaseRef}`
            );
        });

    }

    async ormCreateAndAttach(warehouseId, purchaseOrderId, base64Image) {
      const res = await this.orm.call("purchase.order", "create_and_set_attachments", [Number(purchaseOrderId)], { warehouse_id: Number(warehouseId), base64_image: base64Image });
    }

    async ormGetPurchaseOrderReference(purchaseOrderId) {
      const res = await this.orm.call("purchase.order", "get_po_reference", [Number(purchaseOrderId)]);
      return res
    }

    async dialogImageUploadedAlert(alertBody){
          this.dialog.add(AlertDialog, {
              title: 'Image Uploaded!',
              body: alertBody,
              contentClass: 'text-success'
          });
      }
    
    async notifSticky(message){
        this.notification.add(message, {
            title: 'Sticky Notification',
            type: 'success',
            sticky: true,
        });
    }

    async pickingManagingdialog(warehouseId,purchaseOrderId,pickingData){
        this.dialog.add(PickingManageDialog,  {
              warehouseId : Number(warehouseId),
              purchaseOrderId: Number(purchaseOrderId),
              pickingData : pickingData,
              close: Function,
              onConfirmed: () => this._loadData(),
            });
    }

    async createBackOrder() {
      const purchaseOrderId = event.target.dataset.purchaseOrderId;
      const warehouseId = event.target.dataset.warehouseId;
      await this.ormCheckLinesUnchecked(warehouseId,purchaseOrderId);

      // All Lines Are Checked Now.
      const pickingData = await this.ormOpenBackOrderDialog(warehouseId,purchaseOrderId);
      if(!pickingData || pickingData.length === 0){
        this.dialog.add(AlertDialog, {
              title: 'No Picking Found!',
              body: "There is NO Available Picking For This Purchase Order!",
              contentClass: 'text-danger'
          });
          return
      }
      if(pickingData){
        await this.pickingManagingdialog(warehouseId,purchaseOrderId,pickingData);
      }
    }

    async ormCheckLinesUnchecked(warehouseId,purchaseOrderId) {
      const res = await this.orm.call("warehouse.receiving", "unchecked_lines", [Number(warehouseId)], {purchase_order_id: Number(purchaseOrderId)});
      return res
    }

    async ormOpenBackOrderDialog(warehouseId,purchaseOrderId) {
      const res = await this.orm.call("warehouse.receiving", "open_create_backorder_dialog", [Number(warehouseId)], {purchase_order_id: Number(purchaseOrderId)});
      return res
    }

}

const liveWarehouseReceiving = {
  component: Live_warehouse_receiving,
};

registry.category("view_widgets").add("live_warehouse_receiving", liveWarehouseReceiving);
