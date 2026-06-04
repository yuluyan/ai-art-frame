import base64
import copy
import requests

from io import BytesIO
from PIL import Image

from managers.config_manager import ConfigManager
from utils import get_openai_key


class ImageGenerator:
    def __init__(self) -> None:
        self.configs = {}

    def generate(self, prompt: str) -> Image.Image:
        raise NotImplementedError

    def configure(self, config_manager: ConfigManager):
        overrides = {}
        for key, _ in self.configs.items():
            new_value = config_manager.get_config_value(key)
            if new_value is not None:
                overrides[key] = new_value
        self.configs.update(overrides)

    def get_model(self) -> str:
        raise NotImplementedError


class OpenAIImageGenerator(ImageGenerator):
    """Image generation backed by OpenAI's gpt-image-2 model.

    The images endpoint always returns base64-encoded data for the gpt-image
    family (no `url` / `response_format`), so we decode `b64_json` directly.
    """

    MODEL = "gpt-image-2"
    # Size is LOCKED to the frame's exact 9:16 aspect. gpt-image-2 requires both
    # edges to be multiples of 16, so the frame's native 1080x1920 isn't a valid
    # request; 1152x2048 has the identical aspect (0.5625) and downscales to fill
    # 1080x1920 with no letterbox bars and no crop.
    SIZE = "1152x2048"

    def __init__(self) -> None:
        # Only the knobs that meaningfully affect a wall-frame image are kept;
        # size is fixed (see SIZE) and output_format/n/moderation stay internal.
        # Keys match the `gpt_image_configs` ConfigItems so the inherited
        # configure() picks them up from the user's settings.
        self.configs = {
            "quality": "auto",
            "background": "auto",
        }

    @staticmethod
    def get_url():
        return "https://api.openai.com/v1/images/generations"

    def generate(self, prompt: str) -> Image.Image:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {get_openai_key()}",
        }

        data = copy.deepcopy(self.configs)
        data["model"] = self.MODEL
        data["prompt"] = prompt
        data["n"] = 1
        data["size"] = self.SIZE
        data["output_format"] = "png"

        response = requests.post(self.get_url(), headers=headers, json=data, timeout=300)
        if response.status_code != 200:
            raise RuntimeError(f"OpenAI image generation {response.status_code}: {response.text.strip()}")

        b64_image = response.json()["data"][0]["b64_json"]
        image = Image.open(BytesIO(base64.b64decode(b64_image)))

        return image

    def get_model(self):
        return self.MODEL


if __name__ == "__main__":
    gen = OpenAIImageGenerator()
    gen.generate("a serene mountain landscape at dawn, soft oil painting").show()
