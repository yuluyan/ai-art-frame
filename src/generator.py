import abc
import base64
import copy
import requests
import typing
import uuid
import os

from io import BytesIO
from PIL import Image

from utils import get_openai_key, get_sd_port
from config_manager import ConfigManager


class ImageGenerator:
    def __init__(self) -> None:
        pass
    
    @abc.abstractmethod
    def generate(self, prompt: str) -> Image:
        pass
        
    def configure(self, config_manager: ConfigManager):
        overrides = {}
        for key, _ in self.configs.items():
            new_value = config_manager.get_config_value(key)
            if new_value is not None:
                overrides[key] = new_value
        self.configs.update(overrides)


class OpenAIImageGenerator(ImageGenerator):
    def __init__(self) -> None:
        self.configs = {
            "n": 1,
            "size": "1024x1024",
            "response_format": "url"
        }
    
    def generate(self, prompt: str) -> typing.Any:
        return self.get_dalle2_image(prompt)

    @staticmethod
    def get_url():
        return "https://api.openai.com/v1/images/generations"

    def get_dalle2_image(self, prompt):
        url = OpenAIImageGenerator.get_url()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {get_openai_key()}"
        }

        data = copy.deepcopy(self.configs)
        data["prompt"] = prompt

        response = requests.post(url, headers=headers, json=data)

        response.raise_for_status()

        image_url = response.json()["data"][0]["url"]

        image_data = requests.get(image_url).content
        image = Image.open(BytesIO(image_data))

        return image


class LocalStableDiffusionImageGenerator(ImageGenerator):
    def __init__(self) -> None:
        self.configs = {
            "steps": 40,
            "cfg_scale": 7,
            "width": 1280,
            "height": 720,
            "sampler_index": "DPM++ SDE Karras",
            "restore_faces": False
        }
    
    def generate(self, prompt: str) -> typing.Any:
        return self.get_image(prompt)

    @staticmethod
    def get_url():
        return f"http://{get_sd_port()}/sdapi/v1/txt2img"

    def get_image(self, prompt):
        url = LocalStableDiffusionImageGenerator.get_url()

        headers = {
            "Content-Type": "application/json",
        }

        data = copy.deepcopy(self.configs)
        data["prompt"] = prompt

        response = requests.post(url=url, headers=headers, json=data)

        image_raw_data = response.json()['images'][0]

        image = Image.open(BytesIO(base64.b64decode(image_raw_data.split(",", 1)[0])))

        return image


if __name__ == "__main__":
    gen = LocalStableDiffusionImageGenerator()
    gen.generate("abstract art, art station").show()
    