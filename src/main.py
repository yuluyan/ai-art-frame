import os

from gui import App
from generator import OpenAIImageGenerator, LocalStableDiffusionImageGenerator
from image_manager import ImageManager
from config_manager import ConfigManager


def main():
    image_manager = ImageManager(os.path.join(os.path.dirname(__file__), '..', 'imgs'), LocalStableDiffusionImageGenerator())
    config_manager = ConfigManager()

    app = App()
    app.set_managers(image_manager, config_manager)
    app.mainloop()


if __name__ == "__main__":
    main()