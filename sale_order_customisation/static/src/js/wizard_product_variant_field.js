/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, xml } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Dialog } from "@web/core/dialog/dialog";

async function applyProductToWizardLine(record, product, productQty) {
    
    // if (record && product && productTmpl &&  productName){}
    console.log('Apply Method!!');
    console.log(record.data);
    console.log(record.data.product_uom_qty);
    await record._update({
        product_id: [product],
        // product_template_id: [productTmpl,productName],
        product_uom_qty: productQty,
        is_select_optional_product: true,
    });
    console.log('------->  Final  <---------');
    console.log(record);
};

//#region custom dialog
class ProductVariantDialog extends Component {
    static components = { Dialog };
    static template = xml`
        <Dialog size="'md'" title="'Select Product From Optional Groups'">
            <t t-if="props.optionalGroups == false">
                <!-- <h3 class="alert alert-warning" role="alert">There are no optional groups found for this Product!</h3> -->
                <div class="empty-state-container">
                <div class="empty-state-content">
                    <i class="fa fa-inbox empty-icon"></i>
                    <h4 class="empty-title">No Optional Groups Available</h4>
                    <p class="empty-description">There are no optional groups found for this product.</p>
                </div>
            </div>
            </t>
            <t t-elif="props.optionalGroups">
                <div class="p-3">
                    <!-- Instructions Banner -->
                    <div class="instructions-banner">
                        <i class="fa fa-info-circle"></i>
                        <span>Select products from the optional groups below to customize your order</span>
                    </div>
                    <!-- <i class="fa fa-arrow-down" aria-hidden="true"></i> -->
                    <!-- <p class="fw-bold fa fa-arrow-down text-info mb-4" style="font-size:20px;">Select Product From The Optional Groups Below.</p> -->
                    <div class="optional-groups-container">
                        <t t-foreach="props.optionalGroups" t-as="group" t-key="group.optional_group_id.id">
                            <div class="group-section">
                            <!-- Group Header -->
                                <div class="group-header">
                                    <i class="fa fa-layer-group group-icon"></i>
                                    <h3 class="group-title">
                                        <t t-esc="group.optional_group_id.name"/>
                                    </h3>
                                </div>
                            <!-- <h2> -->
                                <!-- <i class="fa fa-hand-o-right" style="margin-right: 10px;" aria-hidden="true"></i> -->
                                <!-- <label class="form-check-label" t-att-for="'group_' + group.optional_group_id.id">
                                    <t t-esc="group.optional_group_id.name"/>
                                </label>
                            </h2> -->

                            <!-- #############################  CHECKBOX ############################# -->
                                <!-- <t t-foreach="group.optional_group_id.products" t-as="product" t-key="product">
                                    <div class="form-check mb-2">
                                        <input 
                                            class="form-check-input product-checkbox" 
                                            type="radio" 
                                            t-att-id="'group_product_' + product"
                                            t-att-value="product"
                                            t-on-change="(ev) => this.onToggleGroupProduct(product, ev.target.checked)"
                                        />
                                        <label class="form-check-label product-label" t-att-for="'group_product_' + product">
                                            <t t-esc="product"/>
                                        </label>
                                    </div>
                                </t> -->
                                <!-- ########################### CHECKBOX ############################## -->

                                <t t-foreach="group.optional_group_id.products" t-as="product" t-key="product">
                                    <div class="product-card">
                                        <div class="form-check">
                                            <input 
                                                class="form-check-input product-radio" 
                                                type="radio" 
                                                t-att-name="'group_' + group.optional_group_id.id"
                                                t-att-id="'group_product_' + product"
                                                t-att-value="product"
                                                t-on-change="(ev) => this.onToggleGroupProduct(group.optional_group_id.id, product, ev.target.checked)"
                                            />
                                            <label class="form-check-label product-label" t-att-for="'group_product_' + product">
                                                <span class="product-name"><t t-esc="product"/></span>
                                            </label>
                                        </div>
                                    </div>
                                </t>
                            </div>
                        </t>
                    </div>
                    <!-- Footer Buttons -->
                    <t t-set-slot="footer">
                        <div class="dialog-footer-actions">
                            <button class="btn btn-secondary btn-cancel" t-on-click="onCancel">
                                <i class="fa fa-times"></i>
                                Cancel
                            </button>
                            <button class="btn btn-primary btn-confirm" t-on-click="confirmSelection">
                                <i class="fa fa-check"></i>
                                Confirm Selection
                            </button>
                        </div>
                    </t>
                </div>
            </t>
             <!-- Embedded Styles -->
        <style>
            /* Instructions Banner */
            .instructions-banner {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 16px 20px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 24px;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            }

            .instructions-banner i {
                font-size: 20px;
                flex-shrink: 0;
            }

            .instructions-banner span {
                font-size: 15px;
                font-weight: 500;
                line-height: 1.5;
            }

            /* Empty State */
            .empty-state-container {
                padding: 60px 20px;
                text-align: center;
            }

            .empty-state-content {
                max-width: 400px;
                margin: 0 auto;
            }

            .empty-icon {
                font-size: 72px;
                color: #cbd5e1;
                margin-bottom: 20px;
                display: block;
            }

            .empty-title {
                color: #475569;
                font-size: 20px;
                font-weight: 600;
                margin-bottom: 8px;
            }

            .empty-description {
                color: #64748b;
                font-size: 15px;
                margin: 0;
            }

            /* Group Section */
            .group-section {
                background: #f8fafc;
                border-radius: 16px;
                padding: 30px;
                border: 2px solid #e2e8f0;
                transition: all 0.3s ease;
            }

            .group-section:hover {
                border-color: #cbd5e1;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            }

            /* Group Header */
            .group-header {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 16px;
                padding-bottom: 12px;
                border-bottom: 2px solid #e2e8f0;
            }

            .group-icon {
                font-size: 24px;
                color: #667eea;
                flex-shrink: 0;
            }

            .group-title {
                margin: 0;
                font-size: 20px;
                font-weight: 700;
                color: #1e293b;
                letter-spacing: -0.01em;
            }

            /* Checkbox Styling */
            .form-check {
                margin: 0;
                padding: 0;
                display: flex;
                align-items: center;
            }

            .product-checkbox {
                width: 20px;
                height: 20px;
                cursor: pointer;
                border: 2px solid #cbd5e1;
                margin: 0;
                flex-shrink: 0;
            }

            .product-checkbox:checked {
                background-color: #667eea;
                border-color: #667eea;
            }

            .product-checkbox:focus {
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
            }

            /* Product Label */
            .product-label {
                cursor: pointer;
                margin: 0;
                margin-left: 12px;
                flex: 1;
                user-select: none;
            }

            .product-name {
                font-size: 15px;
                font-weight: 500;
                color: #334155;
                line-height: 1.4;
            }

            .product-card:has(.product-checkbox:checked) .product-name {
                color: #4c1d95;
                font-weight: 600;
            }


            /* Footer Actions */
            .dialog-footer-actions {
                display: flex;
                gap: 12px;
                justify-content: flex-end;
                width: 100%;
            }

            .btn-cancel,
            .btn-confirm {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 10px 24px;
                font-size: 15px;
                font-weight: 600;
                border-radius: 8px;
                transition: all 0.2s ease;
                border: none;
            }

            .btn-cancel {
                background-color: #f1f5f9;
                color: #475569;
            }

            .btn-cancel:hover {
                background-color: #e2e8f0;
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }

            .btn-confirm {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }

            .btn-confirm:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
            }

            .btn-cancel i,
            .btn-confirm i {
                font-size: 16px;
            }
        </style>
        </Dialog>
    `;

    static props = {
        close: Function,
        optionalGroups: Array,
        productMap: Object,
        wizard: Object,
        productQty: Number,
        // onConfirm: { type: Function, optional: true },
    };

    setup() {
        this.state = useState({
            selectedGroupProducts: [],
        });
        this.notification = useService("notification");
    }

    onToggleGroupProduct(groupId, product, checked) {
        if (checked) {
            // When a radio button is selected, update the selection for this group
            // Remove any previous selection for this group and add the new one
            
            // First, remove any existing selection from this group
            const existingIndex = this.state.selectedGroupProducts.findIndex(
                item => item.groupId === groupId
            );
            
            if (existingIndex !== -1) {
                // Remove the old selection
                this.state.selectedGroupProducts.splice(existingIndex, 1);
            }
            
            // Add the new selection
            this.state.selectedGroupProducts.push({
                groupId: groupId,
                product: product
            });
        } else {
            // This case shouldn't typically happen with radio buttons,
            // but handle it for safety (e.g., if user clicks the same radio again)
            const index = this.state.selectedGroupProducts.findIndex(
                item => item.groupId === groupId && item.product === product
            );
            
            if (index !== -1) {
                this.state.selectedGroupProducts.splice(index, 1);
            }
        }

        console.log('Currently selected products:', this.state.selectedGroupProducts);

    }

    // ###################### CHECK BOX ################################

    // onToggleGroupProduct(groupId, product, isChecked) {
    //     if (isChecked) {
    //         // Add to selected products
    //         this.state.selectedGroupProducts.push(product);
    //     } else {
    //         // Remove from selected products
    //         const index = this.state.selectedGroupProducts.indexOf(product);
    //         if (index > -1) {
    //             this.state.selectedGroupProducts.splice(index, 1);
    //         }
    //     }
    //     console.log('Currently selected products:', this.state.selectedGroupProducts);
    // }

        // ###################### CHECK BOX ################################


    async confirmSelection() {
        let product_ids_array = [];
        console.log('DEBUG----->');
        console.log(this.state.selectedGroupProducts);
        if (this.state.selectedGroupProducts.length > 0) {
            for (const ele of this.state.selectedGroupProducts){
                console.log("Element");
                console.log(ele);
                // ele.product have the name of the product later to be used to fetch it's ID.
                product_ids_array.push(this.props.productMap[ele.product]);
            }
            // await applyProductToWizardLine(this.props.record, product_ids_array);
            for(const p of product_ids_array) {
                const newLine = await this.props.wizard.data.sale_order_product_line_wizard_ids.addNewRecord({position:'bottom', mode:'readonly'});
                await applyProductToWizardLine(newLine, p, this.props.productQty);
            }
            // for (const key in this.props.productMap) {
            //     console.log(`${key}: ${this.props.productMap[key]}`);
            //     const newLine = await this.props.wizard.data.sale_order_product_line_wizard_ids.addNewRecord({position:'bottom', mode:'readonly'});
            //     await applyProductToWizardLine(newLine, this.props.productMap[key], this.props.productTemplateMap[key], key);
            // }

            // this.props.onConfirm(this.state.selectedGroupProducts);
        }
        this.props.close();
    }

    onCancel() {
        this.notification.add('You canceled the dialog.');
        this.props.close();
    }
}
//#endregion

class WizardLineProductVariantField extends Component {
    static template = xml`
        <div>
            <button class="btn-confirm" 
                    t-on-click="openDialog"
                    title="Opens a POP Up, Select the optional products to add them.">
                    <i class="fa fa-plus"/>
                        Optional Group
            </button>
            <!-- <button class="btn btn-link fa fa-plus-square" t-on-click="openDialog" title="Opens a pop up, select the optional products to add them."></button> -->
        </div>

        <style>
            .btn-confirm {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 5px 8px;
                font-size: 12px;
                font-weight: 600;
                border-radius: 8px;
                transition: all 0.2s ease;
                border: none;
            }

            .btn-confirm {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }

            .btn-confirm:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
            }

            .btn-confirm i {
                font-size: 16px;
            }
        </style>
    `;
    
    static props = {
        ...standardFieldProps,
    };


    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({
            wizard : false,
            selectedProductId: false,
            selectedProductName: false,
            selectedProductQty: false,
            optionalGroups: [], 
            // productTemplateMap: {},
            productMap: {},
        });
    }

    // FIX: prevent Odoo renderer crash
    get label() {
        return "";
    }

    get displayValue() {
        const value = this.props.record.data[this.props.name];
        return value ? value[1] : "";
    }

    async openDialog() {
        console.log("Opening product variant dialog...");
        console.log('PROPS', this.props);
        
        this.state.selectedProductId = this.props.record.data?.product_id[0];
        this.state.selectedProductName = this.props.record.data?.product_id[1];
        this.state.selectedProductQty = this.props.record.data?.product_uom_qty;
        this.state.optionalGroups = await this.getOptionalGroups(this.state.selectedProductId);
        this.state.productMap = await this.getProductMap(this.state.selectedProductId);
        // this.state.productTemplateMap = await this.getProductTmplMap(this.state.selectedProductId);
        this.state.wizard = this.props.record.model.root;
        
        console.log('STATE', this.state);
        
        // Open your custom dialog and pass optionalGroups as a prop
        // Use { raw: true } to prevent serialization of complex objects
        this.dialog.add(
            ProductVariantDialog, 
            {
                wizard: this.state.wizard || false,
                optionalGroups: this.state.optionalGroups || [],
                productQty: this.state.selectedProductQty || 1.0,
                // productTemplateMap: this.state.productTemplateMap || [],
                productMap:this.state.productMap || {},
                close: () => {
                    // Handle dialog close and update field value if needed
                    this.notification.add("Product variant selected", {
                        type: "success",
                    });
                }
            },
            { raw: true }
        );
    }

    async getOptionalGroups(productId) {
        return await this.orm.call("product.product", "get_optional_groups", [productId]);
    }
    async getProductMap(productId) {
        return await this.orm.call("product.product", "get_optional_group_product_mapping", [productId]);
    }
    
}

export const wizardLineProductVariantField = {
    component: WizardLineProductVariantField,
};

registry.category("fields").add("wizard_product_variant_many2one", wizardLineProductVariantField);