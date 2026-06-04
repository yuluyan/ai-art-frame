import dataclasses
import datetime
import json
import logging
import uuid
import os
import threading
import typing

from PIL import Image

from generator import ImageGenerator, OpenAIImageGenerator
from managers.config_manager import ConfigManager
from utils import date_serializer, date_deserializer

logger = logging.getLogger(__name__)


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

        self.is_generating = False
        # Generation (voice thread) and uploads (web-server thread) can both
        # append records, so the read-modify-write of records.json is guarded.
        self._records_lock = threading.RLock()

    def uuid_to_path(self, uuid: str) -> str:
        return os.path.join(self.folder, f"{uuid}.png")

    def _read_records(self) -> typing.List[ImageRecord]:
        if not os.path.exists(self.records_path):
            return []
        try:
            with open(self.records_path, 'r') as f:
                return json.load(f, object_hook=date_deserializer)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"records.json unreadable ({e}); starting with no history")
            return []

    def _save_records(self, records: typing.List[ImageRecord]) -> None:
        # Write atomically so a crash/power-loss mid-write can't truncate the
        # file and brick the gallery on next start.
        tmp = self.records_path + ".tmp"
        with open(tmp, 'w') as f:
            json.dump(records, f, indent=2, default=date_serializer)
        os.replace(tmp, self.records_path)

    def _store_image(self, image: Image.Image, title: str, prompt: str, model: str) -> ImageRecord:
        """Persist a PIL image as a PNG on disk and append its record. Thread-safe.

        Images are always stored as PNG regardless of how they were produced, so
        `uuid_to_path` and every consumer can assume a single on-disk format.
        """
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")

        image_uuid = str(uuid.uuid4())
        image_path = self.uuid_to_path(image_uuid)
        image.save(image_path, "PNG")

        record = ImageRecord(image_uuid, prompt, title, datetime.date.today(), model)
        with self._records_lock:
            records = self._read_records()
            records.append(dataclasses.asdict(record))
            self._save_records(records)

        return record

    def generate(self, title: str, prompt: str) -> ImageRecord:
        if self.generator is None:
            raise ValueError("No generator provided for image manager.")

        self.is_generating = True
        try:
            image = self.generator.generate(prompt)
        finally:
            self.is_generating = False

        return self._store_image(image, title, prompt, self.generator.get_model())

    def save_uploaded_image(self, image: Image.Image, title: str) -> ImageRecord:
        """Ingest a user-uploaded image as a new gallery entry."""
        return self._store_image(image, title, title, "Upload")

    def get_all_records(self) -> typing.List[ImageRecord]:
        with self._records_lock:
            records = self._read_records()
        return [ImageRecord(**record) for record in records]

    def delete_record(self, target_uuid) -> None:
        with self._records_lock:
            records = self._read_records()
            records = [record for record in records if record["uuid"] != target_uuid]
            self._save_records(records)

        image_path = self.uuid_to_path(str(target_uuid))
        if os.path.exists(image_path):
            os.remove(image_path)

    def get_last_record(self) -> ImageRecord:
        with self._records_lock:
            records = self._read_records()
        if len(records) == 0:
            return None
        else:
            return ImageRecord(**records[-1])

    def get_record_count(self) -> int:
        with self._records_lock:
            return len(self._read_records())

    def update_generator_config(self, config_manager: ConfigManager) -> None:
        if self.generator is None:
            raise ValueError("No generator provided for image manager.")
        self.generator.configure(config_manager)

    def get_record(self, uuid: str) -> typing.Optional[ImageRecord]:
        with self._records_lock:
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
    print(im.get_all_records())
