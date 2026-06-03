import os

from gui import App
from generator import OpenAIImageGenerator
from managers.image_manager import ImageManager
from managers.config_manager import ConfigManager
from managers.upload_manager import UploadServer


def main():
    image_manager = ImageManager(os.path.join(os.path.dirname(__file__), '..', 'imgs'), OpenAIImageGenerator())
    config_manager = ConfigManager()

    app = App()
    app.set_managers(image_manager, config_manager)

    # Web upload server: a phone/browser on the same Wi-Fi can push images
    # straight to the frame's gallery.
    upload_server = UploadServer(on_image=app.handle_uploaded_image, port=8080)
    upload_server.start()
    app.set_upload_server(upload_server)

    app.mainloop()


if __name__ == "__main__":
    main()
