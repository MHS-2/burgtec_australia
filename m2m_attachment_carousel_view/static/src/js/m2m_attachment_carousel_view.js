/** @odoo-module **/

import { Component, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class ImageCarouselWidget extends Component {
    static template = "m2m_attachment_carousel_view.ImageCarouselWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        console.log('Chal gya');
        this.state = useState({
            currentIndex: 0,
        });
        this.fileInputRef = useRef("fileInput");
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    get images() {
        const value = this.props.record.data[this.props.name];
        if (!value || !value.records) {
            return [];
        }
        return value.records.map(record => ({
            id: record.resId,
            name: record.data.name || 'Image',
            url: `/web/image/${record.resId}`,
            datas: record.data.datas
        }));
    }

    get currentImage() {
        return this.images[this.state.currentIndex] || null;
    }

    get hasImages() {
        return this.images.length > 0;
    }

    get isReadonly() {
        return this.props.readonly;
    }

    nextImage(ev) {
        ev.stopPropagation();
        if (this.state.currentIndex < this.images.length - 1) {
            this.state.currentIndex++;
        }
    }

    prevImage(ev) {
        ev.stopPropagation();
        if (this.state.currentIndex > 0) {
            this.state.currentIndex--;
        }
    }

    goToImage(index, ev) {
        ev.stopPropagation();
        this.state.currentIndex = index;
    }

    openImageGallery(ev) {
        ev.stopPropagation();
        if (this.currentImage) {
            window.open(this.currentImage.url, '_blank');
        }
    }

    onAddImageClick(ev) {
        ev.stopPropagation();
        if (this.fileInputRef.el) {
            this.fileInputRef.el.click();
        }
    }

    async onFileChange(ev) {
        const files = ev.target.files;
        if (!files || files.length === 0) {
            return;
        }

        for (let file of files) {
            try {
                // Convert file to base64
                const base64 = await this.fileToBase64(file);

                // Create attachment record
                const attachmentId = await this.orm.create("ir.attachment", [{
                    name: file.name,
                    datas: base64.split(',')[1], // Remove data:image/...;base64, prefix
                    res_model: this.props.record.resModel,
                    res_id: this.props.record.resId,
                    mimetype: file.type,
                }]);

                // Add to many2many field
                await this.props.record.update({
                    [this.props.name]: [[4, attachmentId[0]]]
                });

                this.notification.add("Image uploaded successfully", {
                    type: "success",
                });

            } catch (error) {
                console.error("Error uploading image:", error);
                this.notification.add("Failed to upload image", {
                    type: "danger",
                });
            }
        }

        // Reset file input
        ev.target.value = '';
    }

    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    async onDeleteImage(ev) {
        ev.stopPropagation();

        if (!this.currentImage) {
            return;
        }

        if (!confirm(`Are you sure you want to delete "${this.currentImage.name}"?`)) {
            return;
        }

        try {
            const imageId = this.currentImage.id;

            // Remove from many2many field
            await this.props.record.update({
                [this.props.name]: [[3, imageId]]
            });

            // Optionally delete the attachment record itself
             await this.orm.unlink("ir.attachment", [imageId]);

            // Adjust current index if needed
            if (this.state.currentIndex >= this.images.length - 1 && this.state.currentIndex > 0) {
                this.state.currentIndex--;
            }

            this.notification.add("Image deleted successfully", {
                type: "success",
            });

        } catch (error) {
            console.error("Error deleting image:", error);
            this.notification.add("Failed to delete image", {
                type: "danger",
            });
        }
    }
}

export const imageCarouselWidget = {
    component: ImageCarouselWidget,
    supportedTypes: ["many2many"],
    extractProps: ({ attrs }) => {
        return {
            readonly: attrs.readonly,
        };
    },
};

registry.category("fields").add("image_carousel", imageCarouselWidget);
