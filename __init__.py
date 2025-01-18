from .lora_trigger_local import LoRATriggerLocal
NODE_CLASS_MAPPINGS = {
    "LoRATriggerLocal": LoRATriggerLocal
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "LoRATriggerLocal": "LoRA Trigger Local"
}
__all__ = ["NODE_CLASS_MAPPINGS","NODE_DISPLAY_NAME_MAPPINGS"]
