import {patch} from "@web/core/utils/patch";
import {ImageField} from "@web/views/fields/image/image_field";

patch(ImageField.prototype, {

    onFilePaste(ev) {
        const items = ev.clipboardData.items;
        for (let item of items) {
            if (item.kind === 'file' && item.type.startsWith('image/')) {
                const file = item.getAsFile();
                const reader = new FileReader();
                reader.onload = (e) => {
                    const base64String = e.target.result;
                    this.onFileUploaded({
                        data: base64String.split(',')[1],
                        name: file.name || 'pasted-image.png', // Provide a default filename
                        type: file.type
                    });
                };
                reader.readAsDataURL(file);
            }
        }
    },

    cleanPaste(ev) {
        const pasteArea = document.querySelector('.o_input_paste_area');
        if (pasteArea) {
            pasteArea.innerHTML = '<i class="fa fa-copy fa-fw"></i>';
        }
    },

});