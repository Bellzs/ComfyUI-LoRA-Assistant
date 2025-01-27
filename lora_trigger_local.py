import os
import folder_paths
from comfy.sd import load_lora_for_models
from comfy.utils import load_torch_file
from datetime import datetime
import hashlib
import json
TRIGGER_JSON_PATH = "./custom_nodes/ComfyUI-LoRA-Assistant/lora_trigger.json"

def load_json_from_file():
    file_path = TRIGGER_JSON_PATH
    try:
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
            return data
    except FileNotFoundError:
        print(f"LoRA Assistant==>>Json File not found: {file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"LoRA Assistant==>>Error decoding JSON in file: {file_path}")
        return {}

def calculate_sha256(lora_name):
    lora_path = folder_paths.get_full_path("loras", lora_name)
    sha256_hash = hashlib.sha256()
    with open(lora_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def save_dict_to_File(data_dict):
    try:
        with open(TRIGGER_JSON_PATH, 'w', encoding='utf-8') as json_file:
            json.dump(data_dict, json_file, indent=4, ensure_ascii=False)
            print(f"LoRA Assistant==>>Trigger saved to {TRIGGER_JSON_PATH}")
    except Exception as e:
        print(f"LoRA Assistant==>>Error saving JSON to file: {e}")

class LoRATriggerLocal:
    def __init__(self):
        self.loaded_lora = None

    @classmethod
    def INPUT_TYPES(s):
        # input_dir = folder_paths.get_input_directory()
        LORA_LIST = sorted(folder_paths.get_filename_list("loras"), key=str.lower)
        LORA_IMG_LIST = []
        for lora_name in LORA_LIST:
            lora_png_name = lora_name.replace("safetensors","png").replace("\\","%")
            # if os.path.exists(os.path.join(input_dir, lora_png_name)):
            LORA_IMG_LIST.append(lora_png_name)
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP", ),
                "lora_name": (LORA_LIST, ),
                "select_lora_by_png": (LORA_IMG_LIST, {"image_upload": False,"tooltip":"When you select a PNG image associated with LoRA, the lora_name will be updated synchronously. These images should be placed in the 'input' folder."}),
                "strength_model": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.1}),
                "strength_clip": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.1}),
                "save_trigger_local": ("BOOLEAN", {"default": True, "tooltip":"When 'trigger_word' is not empty, whether it is permanently set to the trigger word of this lora so that the trigger word is loaded automatically later"}),
            },
            "optional":{
                "trigger_word": ("STRING", {
                    "multiline": False, 
                    "tooltip":"Manually set the trigger word. If it is empty, the last saved trigger word is automatically loaded",
                    #"default": "Hello World!",
                    # "lazy": True
                }),
                "positive_prompt": ("STRING", {
                    "multiline": True, 
                    "tooltip":"positive prompt except trigger word",
                    #"default": "Hello World!",
                    # "lazy": True
                }),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("MODEL", "CLIP", "Full Prompt text", "Only Trigger text", "PNG name")
    #RETURN_NAMES = ("image_output_name",)

    FUNCTION = "execute"

    #OUTPUT_NODE = False

    CATEGORY = "loaders"

    def execute(self, model, clip, lora_name,select_lora_by_png, strength_model, strength_clip,save_trigger_local,trigger_word,positive_prompt):
        trigger_word_result = trigger_word
        if trigger_word == "":
            lora_sha256_value = calculate_sha256(lora_name)
            lora_triggers_json = load_json_from_file()
            if lora_triggers_json is None :
                trigger_word_result = ""
            elif lora_sha256_value in lora_triggers_json:
                trigger_word_result = lora_triggers_json[lora_sha256_value]["trigger_word"]
            else:
                trigger_word_result = ""
        else:
            if save_trigger_local:
                  lora_sha256_value = calculate_sha256(lora_name)
                  lora_triggers_json = load_json_from_file()
                  if lora_sha256_value not in lora_triggers_json:
                      lora_triggers_json[lora_sha256_value] = {"trigger_word":"","lora_name":"","update_time":"",}
                  if lora_triggers_json[lora_sha256_value]["trigger_word"] != trigger_word:
                    lora_triggers_json[lora_sha256_value]["trigger_word"] = trigger_word
                    lora_triggers_json[lora_sha256_value]["lora_name"] = lora_name
                    now = datetime.now()
                    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
                    lora_triggers_json[lora_sha256_value]["update_time"] = formatted_time
                    save_dict_to_File(lora_triggers_json)
        
        lora_path = folder_paths.get_full_path("loras", lora_name)
        lora = None
        if self.loaded_lora is not None:
            if self.loaded_lora[0] == lora_path:
                lora = self.loaded_lora[1]
            else:
                temp = self.loaded_lora
                self.loaded_lora = None
                del temp

        if lora is None:
            lora = load_torch_file(lora_path, safe_load=True)
            self.loaded_lora = (lora_path, lora)
        model_lora, clip_lora = load_lora_for_models(model, clip, lora, strength_model, strength_clip)
        if trigger_word_result is None:
            trigger_word_result = ""
        full_prompt_text = trigger_word_result
        if positive_prompt != "":
            full_prompt_text = trigger_word_result + ", " + positive_prompt
        return (model_lora, clip_lora, full_prompt_text, trigger_word_result,select_lora_by_png,)

    """
        The node will always be re executed if any of the inputs change but
        this method can be used to force the node to execute again even when the inputs don't change.
        You can make this node return a number or a string. This value will be compared to the one returned the last time the node was
        executed, if it is different the node will be executed again.
        This method is used in the core repo for the LoadImage node where they return the image hash as a string, if the image hash
        changes between executions the LoadImage node is executed again.
    """
    #@classmethod
    #def IS_CHANGED(s, image, string_field, int_field, float_field, print_to_screen):
    #    return ""

# Set the web directory, any .js file in that directory will be loaded by the frontend as a frontend extension
# WEB_DIRECTORY = "./somejs"

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_CLASS_MAPPINGS = {
    "LoRATriggerLocal": LoRATriggerLocal
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "LoRATriggerLocal": "LoRA Trigger Local"
}
