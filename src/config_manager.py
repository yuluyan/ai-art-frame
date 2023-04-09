import copy
import dataclasses
import json
import os
import typing


@dataclasses.dataclass
class ConfigItem:
    name: str
    label: str
    type: str
    value: typing.Any
    range: typing.Any
    editable: bool = True

@dataclasses.dataclass
class ConfigGroup:
    name: str
    label: str
    items: typing.List[ConfigItem]


def serialize_config_group(config_group: ConfigGroup) -> dict:
    return dataclasses.asdict(config_group)

def deserialize_config_group(config_group_dict: dict) -> ConfigGroup:
    config_items = [ConfigItem(**item_data) for item_data in config_group_dict["items"]]
    return ConfigGroup(config_group_dict["name"], config_group_dict["label"], config_items)


class ConfigManager:
    def __init__(self, reinitialize=False) -> None:
        self.configs_path = os.path.join(os.path.dirname(__file__), '..', "configs.json")
        self.configs = self._read_configs()

        self.initialize_configs(overwrite=reinitialize)
        
    def _read_configs(self) -> typing.List[ConfigGroup]:
        if not os.path.exists(self.configs_path):
            return []
        else:
            with open(self.configs_path, 'r') as f:
                configs = json.load(f)
            return [deserialize_config_group(g) for g in configs]

    def _save_configs(self) -> None:
        with open(self.configs_path, 'w') as f:
            json.dump([serialize_config_group(g) for g in self.configs], f, indent=2)

    def _initialize_configs(self, configs: typing.List[ConfigGroup], overwrite=False) -> None:
        if overwrite or (not os.path.exists(self.configs_path)):
            self.configs = copy.deepcopy(configs)
            self._save_configs()

    def initialize_configs(self, overwrite=False) -> None:
        config_group_general = ConfigGroup(
            name="general_configs",
            label="General Settings",
            items=[
                ConfigItem("current_image", "Current Image", "str", "", None, editable=False),
                ConfigItem("do_resize", "Resize to Fit", "bool", True, None),
            ]
        )

        config_group_generator = ConfigGroup(
            name="stable_diffusion_configs", 
            label="Stable Diffusion Settings", 
            items=[
                ConfigItem("steps", "Steps", "int", 40, (1, 150, 1)),
                ConfigItem("cfg_scale", "CFG", "float", 7.0, (1.0, 30.0, 0.1)),
                ConfigItem("width", "Width", "int", 1280, (64, 2048, 64)),
                ConfigItem("height", "Height", "int", 720, (64, 2048, 64)),
                ConfigItem("restore_faces", "Restore Faces", "bool", False, None),
                ConfigItem("sampler_index", "Sampler", "str", "DPM++ SDE Karras", 
                    [
                        "Euler a", 
                        "Euler", 
                        "LMS", 
                        "Heun", 
                        "DPM2", 
                        "DPM2 a", 
                        "DPM++ 2S a", 
                        "DPM++ 2M", 
                        "DPM++ SDE", 
                        "DPM fast", 
                        "DPM adaptive", 
                        "LMS Karras",
                        "DPM2 Karras",
                        "DPM2 a Karras",
                        "DPM++ 2S a Karras",
                        "DPM++ 2M Karras", 
                        "DPM++ SDE Karras",
                        "DDIM",
                        "PLMS",
                        "UniPC",
                    ]
                ),
            ]
        )

        configs = [
            config_group_general,
            config_group_generator,
        ]
        
        self._initialize_configs(configs, overwrite=overwrite)

    def find_config_group_index(self, group_name: str) -> int:
        for i, config_group in enumerate(self.configs):
            if config_group.name == group_name:
                return i
        return -1

    def find_config_item_index(self, item_name: str) -> typing.Tuple[int, int]:
        for i, config_group in enumerate(self.configs):
            for j, config_item in enumerate(config_group.items):
                if config_item.name == item_name:
                    return i, j
        return -1, -1

    def _modify_config_item(self, item_name: str, value: typing.Any) -> None:
        group_index, item_index = self.find_config_item_index(item_name)

        if group_index == -1 or item_index == -1:
            raise ValueError(f"Config item {item_name} not found")

        value_type = type(value).__name__
        target_type = self.configs[group_index].items[item_index].type
        if value_type != target_type:
            if not (value_type == "int" and target_type == "float"):
                raise ValueError(f"Config item {item_name} has type {target_type}, but value has type {value_type}")

        if self.configs[group_index].items[item_index].value != value:
            self.configs[group_index].items[item_index].value = value
            self._save_configs()

    def set_config_value(self, item_name: str, value: typing.Any) -> None:
        try:
            self._modify_config_item(item_name, value)
        except ValueError as e:
            print(f"Error modifying config item {item_name}: {e}. Leaving unchanged.")

    def get_all_configs(self) -> typing.List[ConfigGroup]:
        return self.configs
    
    def get_config(self, item_name, do_raise=False) -> typing.Optional[ConfigItem]:
        group_index, item_index = self.find_config_item_index(item_name)

        if group_index == -1 or item_index == -1:
            if do_raise:
                raise ValueError(f"Config item {item_name} not found")
            else:
                print(f"Error getting config item {item_name}: {e}. Returning None.")
                return None

        return self.configs[group_index].items[item_index]

    def get_config_value(self, item_name, do_raise=False) -> typing.Any:
        return self.get_config(item_name, do_raise=do_raise).value


if __name__ == "__main__":
    cm = ConfigManager(reinitialize=True)