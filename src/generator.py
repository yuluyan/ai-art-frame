import abc
import requests
import typing
import uuid
import os

from io import BytesIO
from PIL import Image

from utils import get_openai_key

class ImageGenerator:
    def __init__(self) -> None:
        pass
    
    @abc.abstractmethod
    def generate(self, prompt: str) -> Image:
        pass

    def save(self, image: Image) -> None:
        image_uuid = uuid.uuid4()
        image_path = os.path.join(os.path.dirname(__file__), '..', 'imgs', f"{image_uuid}.png")
        image.save(image_path, "PNG")
        return image_uuid


class OpenAIImageGenerator(ImageGenerator):
    def __init__(self) -> None:
        pass
    
    def generate(self, prompt: str) -> typing.Any:
        image = self.get_dalle2_image(prompt)
        return self.save(image)

    @staticmethod
    def get_url():
        return "https://api.openai.com/v1/images/generations"

    def get_dalle2_image(self, prompt):
        url = OpenAIImageGenerator.get_url()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {get_openai_key()}"
        }

        data = {
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "url"
        }

        response = requests.post(url, headers=headers, json=data)

        response.raise_for_status()

        image_url = response.json()["data"][0]["url"]

        image_data = requests.get(image_url).content
        image = Image.open(BytesIO(image_data))

        return image


if __name__ == "__main__":
    gen = OpenAIImageGenerator()
    gen.generate("abstract art, art station")