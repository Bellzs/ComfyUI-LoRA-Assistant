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
    """
    A example node

    Class methods
    -------------
    INPUT_TYPES (dict):
        Tell the main program input parameters of nodes.
    IS_CHANGED:
        optional method to control when the node is re executed.

    Attributes
    ----------
    RETURN_TYPES (`tuple`):
        The type of each element in the output tuple.
    RETURN_NAMES (`tuple`):
        Optional: The name of each output in the output tuple.
    FUNCTION (`str`):
        The name of the entry-point method. For example, if `FUNCTION = "execute"` then it will run Example().execute()
    OUTPUT_NODE ([`bool`]):
        If this node is an output node that outputs a result/image from the graph. The SaveImage node is an example.
        The backend iterates on these output nodes and tries to execute all their parents if their parent graph is properly connected.
        Assumed to be False if not present.
    CATEGORY (`str`):
        The category the node should appear in the UI.
    DEPRECATED (`bool`):
        Indicates whether the node is deprecated. Deprecated nodes are hidden by default in the UI, but remain
        functional in existing workflows that use them.
    EXPERIMENTAL (`bool`):
        Indicates whether the node is experimental. Experimental nodes are marked as such in the UI and may be subject to
        significant changes or removal in future versions. Use with caution in production workflows.
    execute(s) -> tuple || None:
        The entry point method. The name of this method must be the same as the value of property `FUNCTION`.
        For example, if `FUNCTION = "execute"` then this method's name must be `execute`, if `FUNCTION = "foo"` then it must be `foo`.
    """
    def __init__(self):
        self.loaded_lora = None

    @classmethod
    def INPUT_TYPES(s):
        """
            Return a dictionary which contains config for all input fields.
            Some types (string): "MODEL", "VAE", "CLIP", "CONDITIONING", "LATENT", "IMAGE", "INT", "STRING", "FLOAT".
            Input types "INT", "STRING" or "FLOAT" are special values for fields on the node.
            The type can be a list for selection.

            Returns: `dict`:
                - Key input_fields_group (`string`): Can be either required, hidden or optional. A node class must have property `required`
                - Value input_fields (`dict`): Contains input fields config:
                    * Key field_name (`string`): Name of a entry-point method's argument
                    * Value field_config (`tuple`):
                        + First value is a string indicate the type of field or a list for selection.
                        + Second value is a config for type "INT", "STRING" or "FLOAT".
        """
        LORA_LIST = sorted(folder_paths.get_filename_list("loras"), key=str.lower)
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP", ),
                "lora_name": (LORA_LIST, ),
                "strength_model": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.1}),
                "strength_clip": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.1}),
                "save_trigger_local": ("BOOLEAN", {"default": True, "tooltip":"When 'trigger_word' is not empty, whether it is permanently set to the trigger word of this lora so that the trigger word is loaded automatically later"}),
                # "tags_out": ("BOOLEAN", {"default": True}),
                # "print_tags": ("BOOLEAN", {"default": False}),
                # "bypass": ("BOOLEAN", {"default": False}),
                # "force_fetch": ("BOOLEAN", {"default": False}),
                # "int_field": ("INT", {
                #     "default": 0, 
                #     "min": 0, #Minimum value
                #     "max": 4096, #Maximum value
                #     "step": 64, #Slider's step
                #     "display": "number", # Cosmetic only: display as "number" or "slider"
                #     "lazy": True # Will only be evaluated if check_lazy_status requires it
                # }),
                # "float_field": ("FLOAT", {
                #     "default": 1.0,
                #     "min": 0.0,
                #     "max": 10.0,
                #     "step": 0.01,
                #     "round": 0.001, #The value representing the precision to round to, will be set to the step value by default. Can be set to False to disable rounding.
                #     "display": "number",
                #     "lazy": True
                # }),
                # "print_to_screen": (["enable", "disable"],),
                # "string_field": ("STRING", {
                #     "multiline": False, #True if you want the field to look like the one on the ClipTextEncode node
                #     "default": "Hello World!",
                #     "lazy": True
                # }),
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

    RETURN_TYPES = ("MODEL", "CLIP", "STRING")
    #RETURN_NAMES = ("image_output_name",)

    FUNCTION = "execute"

    #OUTPUT_NODE = False

    CATEGORY = "loaders"

    def execute(self, model, clip, lora_name, strength_model, strength_clip,save_trigger_local,trigger_word,positive_prompt):
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
        if positive_prompt != "":
            trigger_word_result = trigger_word_result + ", " + positive_prompt
        return (model_lora, clip_lora, trigger_word_result,)

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
