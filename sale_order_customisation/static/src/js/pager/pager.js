// import {patch} from "@web/core/utils/patch";
// import {Pager} from "@web/core/pager/pager";
// import { Component, EventBus, useEffect, useExternalListener, useState } from "@odoo/owl";
// import { useService } from "@web/core/utils/hooks";

// // odoo\addons\web\static\src\core\pager\pager.js

// patch(Pager.prototype, {

//     setup() {
//         console.log('Pager Patched ----->'); 
//         console.log(this.props);
//         super.setup();
//         this.orm = useService("orm");
//         this.state = useState({
//             isEditing: false,
//             isDisabled: false,
//             minLimit: false,
//             maxLimit: false,
//             resModel: false,
//             resId: false,
//         });
//         this.state.resModel = this.__owl__?.childEnv?.model?.config?.resModel
//         this.state.resId = this.__owl__?.childEnv?.model?.config?.resId

//         if (this.state.resModel === 'sale.order.bom.component' && this.state.resId){
//             this.ormWrite(1,50);
//             this.ormSearchRead();
//         }

//      },

//     async ormSearchRead() {
//         console.log('------------->',String(this.state.resModel));
//         console.log('------------->',this.state.resId);
//         // const res = await this.orm.searchRead("sale.order.bom.component", [['id', '=', this.state.resId]], ["min_limit","max_limit"]);
//         const res = await this.orm.searchRead(
//             "sale.order.bom.component", 
//             [['id', '=', this.state.resId]], 
//             ["min_limit", "max_limit"],
//             { limit: 1, order: "id" }
//         );
//         console.log('------------------->',res);
//         this.state.minLimit = res[0].minLimit;
//         this.state.maxLimit = res[0].maxLimit;
//         console.log('-------> search <--------------')
        
//     },

//     async ormWrite(minimum,maximum) {
//         console.log('-------> WRITE <--------------')
//         // const ids = await this.orm.search("sale.order.bom.component", [['id', '=', this.state.resId]]);
//         if (this.state.resId) {
//             await this.orm.write('sale.order.bom.component', [this.state.resId],
//                 {
//                     'min_limit': minimum,
//                     'max_limit':maximum
//                 }
//             );
//             this.state.minLimit = minimum;
//             this.state.maxLimit = maximum;
//         }
//     },

//         /**
//      * @param {string} value
//      */
//     async setValue(value) {
//         const { minimum, maximum } = await this.parse(value);
//         console.log('---> MINIMUM <-----',minimum);
//         console.log('---> MINIMUM <-----',maximum);
//         let min = minimum;
//         min = min+1
//         this.state.minLimit = minimum;
//         this.state.maxLimit = maximum;
//         // minimum = minimum + 1
//         this.ormWrite(minimum,maximum);
//         if (!isNaN(minimum) && !isNaN(maximum) && minimum < maximum) {
//             this.update(minimum, maximum - minimum);
//         }
//     },

//         /**
//      * @returns {string}
//      */
//     get value() {
//         console.log('-----> GET VALUE <-------');
//         if (this.state.resModel === 'sale.order.bom.component'){
//             const parts = [this.state.minLimit];
//             if (this.state.maxLimit > 1) {
//                 parts.push(this.state.maxLimit);
//             }
//             return parts.join("-");
//         }
//         else{
//             const parts = [this.minimum];
//             if (this.props.limit > 1) {
//                 parts.push(this.maximum);
//             }
//             return parts.join("-");
//         }
//     }




// });