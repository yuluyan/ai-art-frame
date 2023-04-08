import os

from gui import App
from generator import OpenAIImageGenerator, LocalStableDiffusionImageGenerator
from image_manager import ImageManager


def main():
    generator = LocalStableDiffusionImageGenerator()
    
    image_manager = ImageManager(
        os.path.join(os.path.dirname(__file__), '..', 'imgs'), 
        generator
    )

    app = App()
    app.set_image_manager(image_manager)

    app.mainloop()


if __name__ == "__main__":
    main()