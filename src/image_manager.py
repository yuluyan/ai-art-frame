import dataclasses
import json
import uuid
import os
import typing

from generator import ImageGenerator, OpenAIImageGenerator
from config_manager import ConfigManager


@dataclasses.dataclass
class ImageRecord:
    uuid: str
    prompt: str

class ImageManager:
    def __init__(self, folder: str, generator: typing.Optional[ImageGenerator]=None):
        self.folder = folder
        self.generator = generator
        
        self.records_path = os.path.join(self.folder, "records.json")

    def uuid_to_path(self, uuid: str) -> str:
        return os.path.join(self.folder, f"{uuid}.png")

    def _read_records(self) -> typing.List[ImageRecord]:
        if not os.path.exists(self.records_path):
            return []
        else:
            with open(self.records_path, 'r') as f:
                records = json.load(f)
            return records

    def _save_records(self, records: typing.List[ImageRecord]) -> None:
        with open(self.records_path, 'w') as f:
            json.dump(records, f)

    def generate(self, prompt: str) -> ImageRecord:
        if self.generator is None:
            raise ValueError("No generator provided for image manager.")
        image = self.generator.generate(prompt)
        image_uuid = str(uuid.uuid4())
        image_path = self.uuid_to_path(image_uuid)
        image.save(image_path, "PNG")

        record = ImageRecord(image_uuid, prompt)
        records = self._read_records()
        records.append(dataclasses.asdict(record))
        self._save_records(records)

        return record

    def get_all_records(self) -> typing.List[ImageRecord]:
        records = self._read_records()
        return [ImageRecord(**record) for record in records]

    def delete_record(self, target_uuid) -> None:
        records = self._read_records()
        records = [record for record in records if record["uuid"] != target_uuid]
        self._save_records(records)

        image_path = self.uuid_to_path(str(target_uuid))
        if os.path.exists(image_path):
            os.remove(image_path)
    
    def get_last_record(self) -> ImageRecord:
        records = self._read_records()
        if len(records) == 0:
            return None
        else:
            return ImageRecord(**records[-1])

    def get_record_count(self) -> int:
        return len(self._read_records())

    def update_generator_config(self, config_manager: ConfigManager) -> None:
        if self.generator is None:
            raise ValueError("No generator provided for image manager.")
        self.generator.configure(config_manager)


if __name__ == "__main__":
    im = ImageManager(
        os.path.join(os.path.dirname(__file__), '..', 'imgs'),
        OpenAIImageGenerator()
    )
    # im.generate("Hello world")
    # im.generate("Abstract art, art station")
    # im.generate("Trees, nature, forest")

    print(im.get_all_records())
    print(im.delete_record("ed919b32-8f0d-46cf-9023-c1873ad26f7b"))