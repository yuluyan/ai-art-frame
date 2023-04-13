import dataclasses
import datetime
import json
import uuid
import os
import typing

from generator import ImageGenerator, OpenAIImageGenerator
from managers.config_manager import ConfigManager
from utils import date_serializer, date_deserializer


@dataclasses.dataclass
class ImageRecord:
    uuid: str
    prompt: str
    title: typing.Optional[str] = None
    date: typing.Optional[datetime.date] = None
    model: typing.Optional[str] = None

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
                records = json.load(f, object_hook=date_deserializer)
            return records

    def _save_records(self, records: typing.List[ImageRecord]) -> None:
        with open(self.records_path, 'w') as f:
            json.dump(records, f, indent=2, default=date_serializer)

    def generate(self, title: str, prompt: str) -> ImageRecord:
        if self.generator is None:
            raise ValueError("No generator provided for image manager.")
        image = self.generator.generate(prompt)
        image_uuid = str(uuid.uuid4())
        image_path = self.uuid_to_path(image_uuid)
        image.save(image_path, "PNG")

        record = ImageRecord(image_uuid, prompt, title, datetime.date.today(), self.generator.get_model())
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

    def get_record(self, uuid: str) -> typing.Optional[ImageRecord]:
        records = self._read_records()
        for record in records:
            if record["uuid"] == uuid:
                return ImageRecord(**record)
        return None

if __name__ == "__main__":
    im = ImageManager(
        os.path.join(os.path.dirname(__file__), '..', 'imgs'),
        OpenAIImageGenerator()
    )
    # im.generate("Hello world")
    # im.generate("Abstract art, art station")
    # im.generate("Trees, nature, forest")

    print(im.get_all_records())
