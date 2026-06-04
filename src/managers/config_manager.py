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
        self.configs_path = os.path.join(os.path.dirname(__file__), "..", "..", "configs.json")
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

    @staticmethod
    def _value_compatible(item: ConfigItem, old_value: typing.Any, old_type: str) -> bool:
        """Whether a previously-stored value can be carried over to a new schema item."""
        if old_type != item.type and not (old_type == "int" and item.type == "float"):
            return False
        # str dropdowns: the saved value must still be one of the offered choices,
        # otherwise CTkOptionMenu would show a stale out-of-range entry.
        if item.type == "str" and isinstance(item.range, list):
            return old_value in item.range
        return True

    def _initialize_configs(self, code_configs: typing.List[ConfigGroup], overwrite=False) -> None:
        """Reconcile the on-disk config with the code-defined schema.

        The code schema is authoritative for structure (label/type/range/order),
        while the user's previously-saved *values* are preserved for any item
        whose name still exists. Obsolete items/groups (e.g. the old Stable
        Diffusion settings) are dropped; brand-new items take their defaults.
        """
        if overwrite or (not os.path.exists(self.configs_path)):
            self.configs = copy.deepcopy(code_configs)
            self._save_configs()
            return

        existing = {}
        for group in self.configs:
            for item in group.items:
                existing[item.name] = (item.value, item.type)

        reconciled = copy.deepcopy(code_configs)
        for group in reconciled:
            for item in group.items:
                if item.name in existing:
                    old_value, old_type = existing[item.name]
                    if self._value_compatible(item, old_value, old_type):
                        if item.type == "float" and isinstance(old_value, int):
                            old_value = float(old_value)
                        item.value = old_value

        self.configs = reconciled
        self._save_configs()

    def initialize_configs(self, overwrite=False) -> None:
        config_group_general = ConfigGroup(
            name="general_configs",
            label="General Settings",
            items=[
                ConfigItem("current_image", "Current Image", "str", "", None, editable=False),
                ConfigItem("do_resize", "Resize to Fit", "bool", True, None),
                ConfigItem("enable_chatgpt", "Enable ChatGPT Prompt", "bool", True, None),
            ]
        )

        config_group_gpt_image = ConfigGroup(
            name="gpt_image_configs",
            label="Image Generation",
            items=[
                ConfigItem("quality", "Quality", "str", "auto",
                    [
                        "auto",
                        "high",
                        "medium",
                        "low",
                    ]
                ),
                ConfigItem("background", "Background", "str", "auto",
                    [
                        "auto",
                        "opaque",
                        "transparent",
                    ]
                ),
            ]
        )

        config_group_rotation = ConfigGroup(
            name="rotation_configs",
            label="Rotation",
            items=[
                ConfigItem("rotation_enabled", "Auto Rotate", "bool", False, None),
                ConfigItem("rotation_mode", "Rotate Mode", "str", "sequential",
                    [
                        "sequential",
                        "shuffle",
                        "newest",
                    ]
                ),
                ConfigItem("rotation_interval", "Interval (min)", "int", 10, (1, 240, 1)),
            ]
        )

        configs = [
            config_group_general,
            config_group_gpt_image,
            config_group_rotation,
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
                print(f"Error getting config item {item_name}. Returning None.")
                return None

        return self.configs[group_index].items[item_index]

    def get_config_value(self, item_name, do_raise=False) -> typing.Any:
        return self.get_config(item_name, do_raise=do_raise).value


if __name__ == "__main__":
    cm = ConfigManager(reinitialize=True)
