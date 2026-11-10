/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ProductTemplateAttributeLine } from "@sale/js/product_template_attribute_line/product_template_attribute_line";

patch(ProductTemplateAttributeLine.prototype, {
     setup() {
        console.log('ProductTemplateAttributeLine Patched ----->'); 
        console.log(this.props);
        super.setup();
     }


});

// patch(ProductTemplateAttributeLine, {
//    props() {
//             attribute_values: {
//             type: Array,
//             element: {
//                 type: Object,
//                 shape: {
//                     id: Number,
//                     name: String,
//                     html_color: [Boolean, String], // backend sends 'false' when there is no color
//                     image: [Boolean, String], // backend sends 'false' when there is no image set
//                     is_custom: Boolean,
//                     price_extra: Number,
//                     excluded: { type: Boolean, optional: true },
//                 },
//             },
//         },
//    },

// });