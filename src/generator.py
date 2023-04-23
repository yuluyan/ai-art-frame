import abc
import base64
import copy
import requests
import typing

from io import BytesIO
from PIL import Image

from managers.config_manager import ConfigManager
from utils import get_openai_key, get_sd_port


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

    @abc.abstractmethod
    def get_model(self) -> str:
        pass


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

    def get_model(self):
        return "DALL-E 2.0"


class LocalStableDiffusionImageGenerator(ImageGenerator):
    def __init__(self) -> None:
        self.configs = {
            "steps": 25,
            "cfg_scale": 7,
            "width": 512,
            "height": 512,
            "sampler_name": "DPM++ SDE Karras",
            "enable_hr": False,
            "denoising_strength": 0.7,
            "hr_upscaler": "ESRGAN_4x",
            "hr_second_pass_steps": 0,
            "hr_resize_x": 720,
            "hr_resize_y": 832,
        }
        self.model_mame = ""
    
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

    @staticmethod
    def get_option_url():
        return f"http://{get_sd_port()}/sdapi/v1/options"

    def switch_model(self, model_name):
        url = LocalStableDiffusionImageGenerator.get_option_url()

        options = requests.get(url=url).json()
        if model_name in options.get("sd_model_checkpoint", ""):
            self.model_mame = model_name
            return
        
        options = {
            "sd_model_checkpoint": model_name,
            "ldsr_cached": None,
            "sd_lora": None
        }

        headers = {
            "Content-Type": "application/json",
        }

        response = requests.post(url=url, headers=headers, json=options)
        if response.status_code != 200:
            raise Exception(f"Failed to switch model: {response.json()}")

        self.model_mame = model_name

    def configure(self, config_manager: ConfigManager):
        super().configure(config_manager)
        self.switch_model(config_manager.get_config_value("model"))

    def get_model(self):
        return self.model_mame

    @staticmethod
    def get_progress_url():
        return f"http://{get_sd_port()}/sdapi/v1/progress?skip_current_image=false"

    def get_progress(self):
        url = LocalStableDiffusionImageGenerator.get_progress_url()

        progress_json = requests.get(url=url).json()

        return progress_json.get("progress")


if __name__ == "__main__":
    gen = LocalStableDiffusionImageGenerator()
    # gen.generate("abstract art, art station").show()
    print(gen.get_progress())
