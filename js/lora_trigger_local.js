import { app } from "../../../scripts/app.js";


app.registerExtension({
    name: 'lora.trigger.local',
    async nodeCreated(node) {
        if(node?.comfyClass === "LoRATriggerLocal"){
            let lora_widget = node.widgets.find(w => w.name == 'lora_name')
            let select_lora_by_png_widget = node.widgets.find(w => w.name == 'select_lora_by_png')
            select_lora_by_png_widget.callback = value =>{
                console.info("LoRA Assistant==>>change select_lora_by_png: ", value);
                lora_widget.value = value.replace(/%/g, "\\").replace(/png/g, "safetensors")
            }
            lora_widget.callback = value =>{
                console.info("LoRA Assistant==>>change lora_name: ", value);
                select_lora_by_png_widget.value = value.replace(/\\/g, "%").replace(/safetensors/g, "png")
            }
        }
    }
})