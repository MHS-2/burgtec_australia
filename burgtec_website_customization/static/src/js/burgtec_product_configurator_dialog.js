/** @odoo-module */
import { ProductConfiguratorDialog } from '@sale/js/product_configurator_dialog/product_configurator_dialog';
import { ProductTemplateAttributeLine } from '@sale/js/product_template_attribute_line/product_template_attribute_line';
import { rpc } from '@web/core/network/rpc';
import { useSubEnv } from '@odoo/owl';

// Keep a WeakMap of original base names so we don't add new enumerable keys
// to product objects (which would break OWL prop validation).
const _productBaseName = new WeakMap();

export class BurgtecProductConfiguratorDialog extends ProductConfiguratorDialog {
    static props = Object.assign({}, ProductConfiguratorDialog.props, {
        use_burgtec: { type: Boolean, optional: true },
        // initialSubSelection: optional mapping used to prefill product.sub_selection
        // shape: { <product_tmpl_id>: { <ptavId>: { <subAttrId>: <valueId>, ... }, ... }, ... }
        initialSubSelection: { type: Object, optional: true },
    });

    // Override setup to add sub-attribute handler to subEnv
    setup() {
        // call parent setup to initialize state and subEnv
        super.setup && super.setup();
        // register our handler into the sub environment so child components can call it
        useSubEnv({
            updateSubAttributeSelection: this._updateSubAttributeSelection.bind(this),
        });
    }

    // Override _loadData to use the custom burgtec endpoint when present
    async _loadData(onlyMainProduct) {
        // If use_burgtec prop is provided, call our endpoint
        if (this.props.use_burgtec) {
            const data = await rpc('/burgtec/product_configurator/get_values', {
                product_template_id: this.props.productTemplateId,
                quantity: this.props.quantity,
                currency_id: this.props.currencyId,
                so_date: this.props.soDate,
                product_uom_id: this.props.productUOMId,
                company_id: this.props.companyId,
                pricelist_id: this.props.pricelistId,
                ptav_ids: this.props.ptavIds,
                only_main_product: onlyMainProduct,
                ...this._getAdditionalRpcParams(),
            });
            // Normalize sub-attributes shape so nested PTALs will render single-value lines.
            try {
                const normalize = (product) => {
                    for (const ptal of product.attribute_lines || []) {
                        for (const ptav of ptal.attribute_values || []) {
                            for (const subAttr of ptav.sub_attributes || []) {
                                // ensure attribute_values array exists
                                subAttr.attribute_values = subAttr.attribute_values || [];
                                // default selected ids array
                                subAttr.selected_attribute_value_ids = subAttr.selected_attribute_value_ids || [];
                                // force create_variant for single-value sub-attributes
                                if ((subAttr.attribute_values || []).length === 1) {
                                    subAttr.create_variant = subAttr.create_variant || 'no_variant';
                                }
                            }
                        }
                    }
                };
                (data.products || []).forEach(normalize);
                (data.optional_products || []).forEach(normalize);
            } catch (e) {
                console.warn('burgtec: failed to normalize sub_attributes', e);
            }
            // If the caller provided an initialSubSelection mapping, apply it to the returned
            // products and optionalProducts so the dialog shows prior sub-attribute selections.
            try {
                const initial = this.props.initialSubSelection || {};
                const applyPrefill = (product) => {
                    const tmplId = product.product_tmpl_id || product.productTmplId || product.product_template_id;
                    if (!tmplId) return;
                    const pre = initial[tmplId];
                    if (pre) {
                        // assign a shallow clone to avoid mutating the original mapping
                        product.sub_selection = Object.assign({}, pre);
                        // also map sub_selection into nested sub_attr.selected_attribute_value_ids
                        try {
                            this._applySubSelectionToProduct(product);
                        } catch (err) {
                            console.warn('Failed to map initial sub_selection into product.sub_attributes', err);
                        }
                    }
                };
                (data.products || []).forEach(applyPrefill);
                (data.optional_products || []).forEach(applyPrefill);
            } catch (e) {
                console.warn('Failed to apply initialSubSelection to configurator data', e);
            }
                // Debug: dump sub_attributes info so we can confirm create_variant and counts
                try {
                    console.debug('burgtec: get_values response', (data.products || []).map(p => ({
                        product_tmpl_id: p.product_tmpl_id,
                        attribute_lines: (p.attribute_lines || []).map(al => ({
                            id: al.id,
                            attribute_values: (al.attribute_values || []).map(av => ({
                                id: av.id,
                                name: av.name,
                                sub_attributes: (av.sub_attributes || []).map(sa => ({
                                    id: sa.id,
                                    create_variant: sa.create_variant,
                                    attribute_values_len: (sa.attribute_values || []).length,
                                    display_type: sa.attribute && sa.attribute.display_type,
                                }))
                            }))
                        }))
                    })));
                } catch (e) {
                    console.debug('burgtec: debug dump failed', e);
                }
            return data;
        }
        // Fallback to original behavior
        return super._loadData(onlyMainProduct);
    }

    /**
     * Override _updateCombination to ensure we do not send nested sub-attribute
     * value ids to the server. Some payloads may accidentally include nested
     * selection ids which are not valid top-level PTAV ids for the product;
     * filter them out to avoid server-side Missing Record errors.
     */
    async _updateCombination(product, quantity) {
        // compute allowed (top-level) ptav ids for this product
        const allowed = new Set((product.attribute_lines || []).flatMap(ptal =>
            (ptal.attribute_values || []).map(av => av.id)
        ));
        const requested = this._getCombination(product) || [];
        const filtered = requested.filter(id => allowed.has(id));
        if (filtered.length !== requested.length) {
            console.warn('burgtec: filtering nested sub-attribute ids from ptav list', {
                product_tmpl_id: product.product_tmpl_id,
                requested,
                filtered,
            });
        }
        // Call the core RPC endpoint with sanitized ptav_ids
        return rpc(this.updateCombinationUrl, {
            product_template_id: product.product_tmpl_id,
            ptav_ids: filtered,
            currency_id: this.props.currencyId || (this.currency && this.currency.id),
            so_date: this.props.soDate,
            quantity: quantity,
            product_uom_id: this.props.productUOMId,
            company_id: this.props.companyId,
            pricelist_id: this.props.pricelistId,
            ...this._getAdditionalRpcParams(),
        });
    }

    /**
     * Update the in-memory selection of sub-attributes for a product/ptav/sub attribute.
     * productTmplId: id of template, ptavId: id of attribute value, subAttrId/valueId
     */
    _updateSubAttributeSelection(productTmplId, ptavId, subAttrId, subValueId) {
        const product = this.state.products.find(p => p.product_tmpl_id === productTmplId)
            || this.state.optionalProducts.find(p => p.product_tmpl_id === productTmplId);
        if (!product) return;
        product.sub_selection = product.sub_selection || {};
        product.sub_selection[ptavId] = product.sub_selection[ptavId] || {};
        const parsed = parseInt(subValueId) || false;
        product.sub_selection[ptavId][subAttrId] = parsed;
        // Also reflect the selection into the nested sub_attr object's selected_attribute_value_ids
        for (const parentPtal of product.attribute_lines || []) {
            for (const ptav of parentPtal.attribute_values || []) {
                if (ptav.id === ptavId) {
                    for (const subAttr of ptav.sub_attributes || []) {
                        if (subAttr.id === subAttrId) {
                            subAttr.selected_attribute_value_ids = parsed ? [parsed] : [];
                        }
                    }
                }
            }
        }
        // update product display name to include nested selections
        try { this._recomputeProductDisplayName(product); } catch (e) { console.debug(e); }
    }

    _getSubSelection(product) {
        if (!product.sub_selection) return [];
        return Object.entries(product.sub_selection).flatMap(([ptavId, subMap]) =>
            Object.entries(subMap).map(([subId, valueId]) => ({
                ptav_id: parseInt(ptavId, 10),
                sub_attribute_id: parseInt(subId, 10),
                value_id: parseInt(valueId, 10),
            }))
        );
    }

    /**
     * Build a nested, human-friendly display name for the product including
     * selected attribute values and their sub-attribute selections.
     * Example: "Alfie Chair (Black (White), No Upholstery (Baye, Tan))"
     */
    _recomputeProductDisplayName(product) {
        try {
            if (!product) return;
            // derive a stable base name to avoid repeated appending when called multiple times
            // store it in a WeakMap so we don't add enumerable keys to the product object
            if (!_productBaseName.has(product)) {
                _productBaseName.set(product, (product.name || product.display_name || '').replace(/\s*\([^)]*\)\s*$/, '').trim());
            }
            const base = _productBaseName.get(product);
            const parts = [];
            for (const ptal of product.attribute_lines || []) {
                const selectedIds = ptal.selected_attribute_value_ids || [];
                // for each selected value (multi or single) build name and nested sub names
                for (const selId of selectedIds) {
                    const ptav = (ptal.attribute_values || []).find(av => av.id === selId || String(av.id) === String(selId));
                    if (!ptav) continue;
                    // collect sub-values for this parent ptav
                    const subMap = (product.sub_selection && product.sub_selection[ptav.id]) || {};
                    const subNames = [];
                    for (const [subAttrId, subValId] of Object.entries(subMap || {})) {
                        const subAttr = (ptav.sub_attributes || []).find(sa => sa.id === parseInt(subAttrId, 10) || String(sa.id) === String(subAttrId));
                        if (!subAttr) continue;
                        const subVal = (subAttr.attribute_values || []).find(av => av.id === subValId || String(av.id) === String(subValId));
                        if (subVal && subVal.name) {
                            subNames.push(subVal.name);
                        }
                    }
                    const name = ptav.name || String(selId);
                    parts.push(subNames.length ? `${name} (${subNames.join(', ')})` : name);
                }
            }
            product.display_name = parts.length ? `${base} (${parts.join(', ')})` : base;
        } catch (e) {
            console.warn('Failed to recompute product display name', e);
        }
    }

    /**
     * Apply product.sub_selection into nested sub_attribute objects so nested PTAL
     * components receive `selected_attribute_value_ids` and render their selected state.
     */
    _applySubSelectionToProduct(product) {
        if (!product || !product.sub_selection) return;
        for (const parentPtal of product.attribute_lines || []) {
            for (const ptav of parentPtal.attribute_values || []) {
                const subMap = product.sub_selection[ptav.id] || {};
                for (const subAttr of ptav.sub_attributes || []) {
                    const val = subMap[subAttr.id];
                    // ensure the nested PTAL receives an array of selected ids (empty if none)
                    subAttr.selected_attribute_value_ids = val ? [val] : [];
                    // If a sub-attribute has only one possible value, the core PTAL
                    // hides the selector by default. Force it to be shown by marking
                    // its create_variant to 'no_variant' when there is a single value
                    // so the UI renders the single option for the user to select.
                    try {
                        if ((subAttr.attribute_values || []).length === 1 && !subAttr.create_variant) {
                            subAttr.create_variant = 'no_variant';
                        }
                    } catch (e) {
                        // defensive: if subAttr shape differs, ignore silently
                    }
                }
            }
        }
        // Recompute display name after applying sub-selection mapping
        try { this._recomputeProductDisplayName(product); } catch (e) { console.debug(e); }
    }

    /**
     * Override the core handler so that when a PTAL id cannot be found in the product
     * attribute_lines we attempt to resolve it as a sub-attribute (stored under a
     * PTAV's `sub_attributes`). If found, delegate to _updateSubAttributeSelection.
     */
    async _updateProductTemplateSelectedPTAV(productTmplId, ptalId, ptavId, isMulti) {
        // Find the product first
        const product = this.state.products.find(p => p.product_tmpl_id === productTmplId)
            || this.state.optionalProducts.find(p => p.product_tmpl_id === productTmplId);
        if (!product) return;

        // If the PTAL exists in product.attribute_lines, delegate to the parent implementation
        const ptal = (product.attribute_lines || []).find(line => line.id === ptalId);
        if (ptal) {
            if (super._updateProductTemplateSelectedPTAV) {
                const res = await super._updateProductTemplateSelectedPTAV(productTmplId, ptalId, ptavId, isMulti);
                // After parent selection changes, clean up any stale sub_selection entries
                // for ptav ids that are no longer selected so nested display updates replace
                // previous values instead of accumulating them.
                try {
                    const selectedPtavIds = new Set();
                    for (const line of product.attribute_lines || []) {
                        for (const sid of (line.selected_attribute_value_ids || [])) {
                            selectedPtavIds.add(typeof sid === 'number' ? sid : parseInt(sid, 10));
                        }
                    }
                    if (product.sub_selection) {
                        for (const key of Object.keys(product.sub_selection)) {
                            const idKey = parseInt(key, 10);
                            if (!selectedPtavIds.has(idKey)) {
                                // remove stale mapping for ptav that is no longer selected
                                delete product.sub_selection[key];
                            }
                        }
                    }
                } catch (e) {
                    console.debug('Failed to cleanup stale sub_selection entries', e);
                }
                // recompute display name after parent logic updated product state
                try { this._recomputeProductDisplayName(product); } catch (e) { console.debug(e); }
                return res;
            }
        }

        // Otherwise, try to resolve the ptalId as a sub-attribute id nested under some PTAV.
        for (const parentPtal of product.attribute_lines || []) {
            for (const ptav of parentPtal.attribute_values || []) {
                const subAttrs = ptav.sub_attributes || [];
                const found = subAttrs.find(sa => sa.id === ptalId);
                if (found) {
                    // ptalId here is actually the sub-attribute id; delegate update to sub-attribute handler
                    return this._updateSubAttributeSelection(productTmplId, ptav.id, ptalId, ptavId);
                }
            }
        }
        // If nothing found, log for debugging and bail
        console.warn('Could not resolve PTAL id in product.attribute_lines nor in nested sub_attributes', { productTmplId, ptalId, ptavId });
    }
}

// Extend the ProductTemplateAttributeLine prop validation to accept our augmented
// `sub_attributes` key on attribute_values so OWL doesn't reject the controller payload.
// We mutate the shape at runtime to avoid touching core sale files. This code lives
// outside the class body to avoid invalid syntax when transpiled.
try {
    const ptavShape = ProductTemplateAttributeLine.props.attribute_values.element.shape;
    // Accept any object shape for sub_attributes so we can support both the
    // simple value-list shape and a full PTAL-like shape returned by the server.
    ptavShape.sub_attributes = {
        type: Array,
        element: { type: Object },
        optional: true,
    };
} catch (e) {
    // Fail silently if the core component shape isn't available yet.
    // This file is loaded in assets, and ordering should make the core component
    // available first, but we keep this guard to avoid runtime crashes.
    console.warn('Could not extend ProductTemplateAttributeLine props for sub_attributes', e);
}

// Extend Product.props to accept sub_selection on the product object
try {
    const Product = require('@sale/js/product/product').Product;
    Product.props.sub_selection = { type: Object, optional: true };
} catch (e) {
    // Some asset load orders won't have the Product module available yet.
    // In that case, log and continue; the guard in runtime will keep the app working.
    console.warn('Could not extend Product.props for sub_selection', e);
}

// Register nested PTAL component on ProductTemplateAttributeLine so that our
// <PTAL t-props="..."/> calls in the QWeb extension resolve at runtime.
try {
    const PTAL = require('@sale/js/product_template_attribute_line/product_template_attribute_line').ProductTemplateAttributeLine;
    ProductTemplateAttributeLine.components = Object.assign({}, ProductTemplateAttributeLine.components, { PTAL });
} catch (e) {
    console.warn('Could not register nested PTAL component on ProductTemplateAttributeLine', e);
}

// Monkeypatch ProductConfiguratorDialog._checkExclusions to be defensive when the
// `exclusions` mapping contains non-iterable values (some payloads may send objects
// or other shapes). We sanitize the mapping into arrays before delegating to core.
try {
    const _orig_checkExclusions = ProductConfiguratorDialog.prototype._checkExclusions;
    ProductConfiguratorDialog.prototype._checkExclusions = function(product) {
        try {
            return _orig_checkExclusions.call(this, product);
        } catch (e) {
            // If core failed due to unexpected exclusions shape, sanitize and retry
            const sanitizeMap = (m) => {
                const out = {};
                if (!m || typeof m !== 'object') return out;
                for (const k of Object.keys(m)) {
                    const v = m[k];
                    if (Array.isArray(v)) {
                        out[k] = v;
                    } else if (v == null) {
                        out[k] = [];
                    } else if (typeof v === 'object') {
                        // Convert object keys to numeric ids when possible
                        out[k] = Object.keys(v).map(x => parseInt(x, 10)).filter(n => !Number.isNaN(n));
                    } else {
                        const nv = parseInt(v, 10);
                        out[k] = Number.isNaN(nv) ? [] : [nv];
                    }
                }
                return out;
            };
            const sanitized = Object.assign({}, product, {
                exclusions: sanitizeMap(product.exclusions),
                parent_exclusions: sanitizeMap(product.parent_exclusions),
                archived_combinations: Array.isArray(product.archived_combinations)
                    ? product.archived_combinations.map(ac => Array.isArray(ac) ? ac : (ac ? Object.keys(ac).map(x => parseInt(x, 10)).filter(n => !Number.isNaN(n)) : []))
                    : [],
            });
            try {
                return _orig_checkExclusions.call(this, sanitized);
            } catch (e2) {
                console.warn('burgtec: _checkExclusions failed even after sanitizing payload', e2);
            }
        }
    };
} catch (e) {
    console.warn('burgtec: failed to monkeypatch _checkExclusions', e);
}

// Runtime helper: if CSS asset isn't loaded or assets are stale, observe dialog insertions
// and apply inline sizing to keep the configurator within the viewport. This is a
// defensive fallback so users don't need to rebuild assets to get a usable dialog.
try {
    if (typeof window !== 'undefined' && typeof document !== 'undefined') {
        const applySizing = (dialogEl) => {
            try {
                const dlg = dialogEl.querySelector('.modal-dialog') || dialogEl;
                if (!dlg) return;
                dlg.style.maxWidth = '1000px';
                dlg.style.width = '90%';
                dlg.style.margin = '1.5vh auto';
                dlg.style.top = '2vh';
                dlg.style.position = 'fixed';
                dlg.style.left = '50%';
                dlg.style.transform = 'translateX(-50%)';

                const content = dlg.querySelector('.modal-content') || dlg;
                if (content) {
                    content.style.maxHeight = '90vh';
                    content.style.display = 'flex';
                    content.style.flexDirection = 'column';
                    content.style.overflow = 'hidden';
                    const body = content.querySelector('.modal-body');
                    if (body) {
                        body.style.overflow = 'auto';
                        body.style.maxHeight = 'calc(90vh - 120px)';
                        body.style.flex = '1 1 auto';
                    }
                }
            } catch (e) {
                console.debug('burgtec: applySizing failed', e);
            }
        };

        const observer = new MutationObserver((mutations) => {
            for (const m of mutations) {
                for (const node of m.addedNodes) {
                    if (node.nodeType !== 1) continue;
                    const el = node;
                    // target the Odoo dialog wrapper element
                    if (el.classList && el.classList.contains('o_dialog')) {
                        // Heuristic: check for known configurator markers (title text or class)
                        const isConfigurator = (el.innerText && el.innerText.includes('Configure your product'))
                            || !!el.querySelector('.o_sale_product_configurator_dialog')
                            || !!el.querySelector('.o_sale_product_configurator');
                        if (isConfigurator) {
                            applySizing(el);
                        }
                    }
                }
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }
} catch (e) {
    console.warn('burgtec: dialog sizing observer failed to initialize', e);
}
