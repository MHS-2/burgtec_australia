/** @odoo-module **/
import {
    ProductLabelSectionAndNoteField,
    productLabelSectionAndNoteField,
} from "@account/components/product_label_section_and_note_field/product_label_section_and_note_field";
import { BurgtecProductConfiguratorDialog } from '../../../../burgtec_website_customization/static/src/js/burgtec_product_configurator_dialog';
import { x2ManyCommands } from '@web/core/orm_service';
import { useService } from '@web/core/utils/hooks';
import { getLinkedSaleOrderLines, serializeComboItem, getSelectedCustomPtav } from "@sale/js/sale_utils";
import { registry } from "@web/core/registry";
import { serializeDateTime } from "@web/core/l10n/dates";
import { useEffect } from '@odoo/owl';

async function applyProductToWizardLine(record, product) {
    // handle custom values & no variants
    const customAttributesCommands = [
        x2ManyCommands.set([]),  // Command.clear isn't supported in static_list/_applyCommands
    ];
    // for (const ptal of product.attribute_lines) {
    //     const selectedCustomPTAV = getSelectedCustomPtav(ptal);
    //     if (selectedCustomPTAV) {
    //         customAttributesCommands.push(
    //             x2ManyCommands.create(undefined, {
    //                 custom_product_template_attribute_value_id: [selectedCustomPTAV.id, "we don't care"],
    //                 custom_value: ptal.customValue,
    //             })
    //         );
    //     };
    // }

    // const noVariantPTAVIds = product.attribute_lines.filter(
    //     ptal => ptal.create_variant === "no_variant"
    // ).flatMap(ptal => ptal.selected_attribute_value_ids);

    // We use `_update` (not locked) instead of `update` (locked) so that multiple records can be
    // updated in parallel (for performance).
    await record._update({
        product_id: [product.id, product.display_name],
        product_uom_qty: product.quantity,
        // product_no_variant_attribute_value_ids: [x2ManyCommands.set(noVariantPTAVIds)],
        // product_custom_attribute_value_ids: customAttributesCommands,
        // store sub attribute selection as JSON if provided
        ...(product.sub_selection ? { 
            sub_selection_json: JSON.stringify(product.sub_selection),
            sub_selection_display: product.display_name,
        } : {}),
    });

    
};

export class WizardLineProductField extends ProductLabelSectionAndNoteField {
    // static template = 'sale_order_customisation.WizardLineProductField';
    setup() {
        console.log('---------------- Custom Widget Executed!!!! ------------------');    
        super.setup();
        this.dialog = useService('dialog');
        this.orm = useService('orm');
        let isMounted = false;
        let isInternalUpdate = false;
        let wasCombo = false;
        const { updateRecord } = this;
        this.updateRecord = (value) => {
            isInternalUpdate = true;
            wasCombo = this.isCombo;
            return updateRecord.call(this, value);
        };
        useEffect(value => {
            if (!isMounted) {
                isMounted = true;
            } else if (value && isInternalUpdate) {
                // we don't want to trigger product update when update comes from an external sources,
                // such as an onchange, or the product configuration dialog itself
                if (wasCombo) {
                    // If the previously selected product was a combo, delete its selected combo
                    // items before changing the product.
                    this.props.record.update({ selected_combo_items: JSON.stringify([]) });
                }
                if (this.relation === "product.template" || this.isCombo) {
                    this._onProductTemplateUpdate();
                } else {
                    this._onProductUpdate();
                }
            }
            isInternalUpdate = false;
        }, () => [Array.isArray(this.value) && this.value[0]]);
    }

        // Try overriding both activeActions and Many2XAutocompleteProps
        get activeActions() {
            const actions = super.activeActions;
            const options = this.props.options || {};
            
            console.log('activeActions called, options:', options); // Debug log
            
            return {
                ...actions,
                create: options.no_create ? false : actions.create,
                write: options.no_open ? false : actions.write,
            };
        }

    //     get Many2XAutocompleteProps() {
    //     const props = super.Many2XAutocompleteProps;
    //     const options = this.props.options || {};
        
    //     console.log('Original props:', JSON.stringify(Object.keys(props)));
        
    //     // Try different possible prop names
    //     const result = {
    //         ...props,
    //     };
        
    //     // Remove or modify any create-related props
    //     if (options.no_create) {
    //         delete result.canCreate;
    //         delete result.canCreateEdit;
    //         delete result.canQuickCreate;
    //         delete result.quickCreate;
            
    //         if (result.activeActions) {
    //             result.activeActions = {
    //                 ...result.activeActions,
    //                 create: false,
    //             };
    //         }
    //     }
        
    //     console.log('Modified props:', JSON.stringify(Object.keys(result)));
        
    //     return result;
    // }

    get Many2XAutocompleteProps() {
        const props = super.Many2XAutocompleteProps;
        const options = this.props.options || {};
        
        // console.log('Original activeActions:', props.activeActions);
        // console.log('Original quickCreate:', props.quickCreate);
        // console.log('Options from props:', options);
        // console.log('Props.options:', this.props.options);

        // console.log('Domain from props:', this.props.domain);
        // console.log('getDomain function result:', props.getDomain ? props.getDomain() : 'no getDomain');
        
        const result = { ...props };

        result.activeActions = {
                ...props.activeActions,
                create: false,
                write: false,
                createEdit: false, // This is the correct property name
            };
            result.quickCreate = null; // Must be null, not false
    
        
        // console.log('Modified activeActions:', result.activeActions);
        
        return result;
    }

    async _onProductTemplateUpdate() {
        console.log('Product Template id',this.props.record.data);
        // if (this.props.record.data){

        // }
        const result = await this.orm.call(
            'product.template',
            'get_single_product_variant',
            [this.props.record.data.product_template_id[0]],
            {
                context: this.context,
            }
        );
        console.log(result);
        if(result && result.product_id) {
            if (this.props.record.data.product_id != result.product_id.id) {
                if (result.is_combo) {
                    await this.props.record.update({
                        product_id: [result.product_id, result.product_name],
                    });
                    this._openComboConfigurator();
                } else if (result.has_optional_products) {
                    this._openProductConfigurator();
                } else {
                    await this.props.record.update({
                        product_id: [result.product_id, result.product_name],
                    });
                    this._onProductUpdate();
                }
            }
        } else {
            // if (result && result.sale_warning) {
            //     const {type, title, message} = result.sale_warning
            //     if (type === 'block') {
            //         // display warning block, and remove blocking product
            //         this.dialog.add(WarningDialog, { title, message });
            //         this.props.record.update({'product_template_id': false})
            //         return
            //     } else if (type == 'warning') {
            //         // show the warning but proceed with the configurator opening
            //         this.notification.add(message, {
            //             title,
            //             type: "warning",
            //         });
            //     }
            // }
            if (!result.mode || result.mode === 'configurator') {
                this._openProductConfigurator();
            } else {
                // only triggered when sale_product_matrix is installed.
                // this._openGridConfigurator();
            }
        }
    }

    async _onProductUpdate() {} // event_booth_sale, event_sale, sale_renting

    async _openProductConfigurator(edit=false) {
        const wizard = this.props.record.model.root;
        const line = this.props.record.data;
        // prepare initial state: ptavIds, custom values, quantity, uom, company, pricelist, date...
        let ptavIds = this._getVariantPtavIds(line);
        let customPtavs = [];
        this.dialog.add(BurgtecProductConfiguratorDialog, {
            productTemplateId: line.product_template_id[0],
            ptavIds,
            customPtavs,
            quantity: line.product_uom_qty,
            productUOMId: line.product_uom ? line.product_uom[0]: undefined,
            companyId: wizard.data.company_id ? wizard.data.company_id[0]: undefined,
            pricelistId: wizard.data.pricelist_id ? wizard.data.pricelist_id[0] : undefined,
            currencyId: line.currency_id ? line.currency_id[0] : undefined,
            soDate: serializeDateTime(wizard.data.date_order),
            edit,
            use_burgtec: true,
                // prefill sub_attribute selections from the wizard line if available
                initialSubSelection: (function(){
                    try {
                        return line.sub_selection_json ? JSON.parse(line.sub_selection_json) : undefined;
                    } catch (e) {
                        console.warn('Invalid sub_selection_json on wizard line', e);
                        return undefined;
                    }
                })(),
            save: async (mainProduct, optionalProducts) => {
                await applyProductToWizardLine(this.props.record, mainProduct);
                console.log('OG ->');
                console.log(this.props.record.model.root);
                await this.props.record.model.root.update({product_model_type:'product_variant'});
                for(const p of optionalProducts) {
                    const newLine = await wizard.data.sale_order_product_line_wizard_ids.addNewRecord({position:'bottom', mode:'readonly'});
                    await applyProductToWizardLine(newLine, p);
                }
            },
            discard: () => {
                wizard.data.sale_order_product_line_wizard_ids.delete(this.props.record);
            },
    });
}

    /**
     * Return the PTAV ids of the provided wizard line.
     *
     * @param line The wizard line
     * @return {Number[]} The wizard line's PTAV ids.
     */
    _getVariantPtavIds(line) {
        return line.product_template_attribute_value_ids.records.map(
            record => record.resId
        );
    }

    /**
     * Return the custom PTAVs of the provided sale order line.
     *
     * @param line Wwizard line
     * @return {Promise<CustomPtav[]>} The line's custom PTAVs.
     */
    async _getCustomPtavs(line) {
        // `product.attribute.custom.value` records are not loaded in the view because sub templates
        // are not loaded in list views. Therefore, we fetch them from the server if the record was
        // saved. Otherwise, we use the value stored on the line.
        const customPtavIds = line.product_custom_attribute_value_ids;
        const customPtavs = customPtavIds.records[0]?.isNew
            ? customPtavIds.records.map(record => record.data)
            : customPtavIds.currentIds.length
                ? await this.orm.read(
                    'product.attribute.custom.value',
                    customPtavIds.currentIds,
                    ['custom_product_template_attribute_value_id', 'custom_value'],
                )
                : [];
        return customPtavs.map(customPtav => ({
            id: customPtav.custom_product_template_attribute_value_id[0],
            value: customPtav.custom_value,
        }));
    }

}

export const wizardLineProductField = {
    component: WizardLineProductField,
};

registry.category("fields").add("wizard_product_many2one", wizardLineProductField);


