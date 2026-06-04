import sys


def _init_x11_threads():
    """Make Xlib thread-safe before Tk opens a display (Linux/X11 only).

    The frame runs Tk alongside background threads (the voice listener and the
    web upload server). Without XInitThreads(), Xlib aborts at startup with
    "[xcb] Extra reply data still left in queue". This must run before the Tk
    root is created, i.e. before importing/instantiating the GUI.
    """
    if sys.platform.startswith("linux"):
        import ctypes
        for libname in ("libX11.so.6", "libX11.so"):
            try:
                ctypes.CDLL(libname).XInitThreads()
                return
            except OSError:
                continue
        print("Warning: could not call XInitThreads (libX11 not found).")


_init_x11_threads()

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
