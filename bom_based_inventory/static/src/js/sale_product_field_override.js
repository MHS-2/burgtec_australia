/** @odoo-module **/

import { SaleOrderLineProductField, saleOrderLineProductField } from "@sale/js/sale_product_field";
import { registry } from "@web/core/registry";

console.log("BOM Module: Loading sale_product_field_override.js");

/**
 * Override of SaleOrderLineProductField to prevent focus shift to product field
 * when clicking on the description/label field.
 */
class SaleOrderLineProductFieldOverride extends SaleOrderLineProductField {
    static template = "bom_based_inventory.SaleProductFieldOverride";
    
    setup() {
        super.setup();
        console.log("BOM Module: Component setup complete");
    }

    onClick(ev) {
        console.log("BOM Module: onClick fired - Override is working!");
        // Check if the click is on the description/label field to prevent focus shift
        const target = ev.target;
        const isLabelOrTextarea = target.tagName === 'TEXTAREA' || 
                                   target.tagName === 'INPUT' ||
                                   target.classList?.contains('o_input') ||
                                   target.closest?.('textarea') ||
                                   target.closest?.('input[type="text"]');
        
        console.log("BOM Module: Target element:", target, "Is label/textarea:", isLabelOrTextarea);
        
        if (isLabelOrTextarea) {
            // Don't process product field click if clicking on description/label
            console.log("BOM Module: Preventing propagation - clicked on description field");
            ev.stopPropagation();
            return;
        }
        
        // Call parent implementation for normal product field clicks
        super.onClick(ev);
    }

    onTextareaClick(ev) {
        console.log("BOM Module: Textarea click intercepted - stopping propagation");
        ev.stopPropagation();
        ev.preventDefault();
    }
}

console.log("BOM Module: Creating custom field registration with override component");

// Create a new registration with our custom component
const customRegistration = {
    ...saleOrderLineProductField,
    component: SaleOrderLineProductFieldOverride,
};

// Override the field registration
registry.category("fields").add("sol_product_many2one", customRegistration, { force: true });

console.log("BOM Module: Override registered successfully");
