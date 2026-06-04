import logging
import socket
import threading

from PIL import Image, ImageOps
from flask import Flask, request

logger = logging.getLogger(__name__)

# Cap decoded pixels so a decompression-bomb upload can't OOM the Pi. Pillow
# raises DecompressionBombError past 2x this, which the upload handler catches.
Image.MAX_IMAGE_PIXELS = 50_000_000


UPLOAD_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Art Frame &mdash; Upload</title>
  <style>
    :root {{ color-scheme: dark; }}
    body {{ margin:0; background:#141414; color:#fff7e3;
            font-family:-apple-system,Segoe UI,Roboto,sans-serif;
            display:flex; min-height:100vh; align-items:center; justify-content:center; }}
    .card {{ width:min(92vw,440px); padding:28px; background:#1e1e1e; border-radius:16px;
             box-shadow:0 8px 40px rgba(0,0,0,.5); }}
    h1 {{ font-size:22px; margin:0 0 6px; letter-spacing:2px; }}
    p {{ color:#b9b29c; margin:0 0 22px; font-size:14px; }}
    input[type=file] {{ width:100%; box-sizing:border-box; padding:14px; background:#141414;
             border:1px dashed #555; border-radius:10px; color:#fff7e3; margin-bottom:18px; }}
    button {{ width:100%; padding:15px; font-size:16px; font-weight:700; border:0;
              border-radius:10px; background:#8df0ad; color:#141414; }}
    .msg {{ margin-top:18px; font-size:14px; color:#8df0ad; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>AI ART FRAME</h1>
    <p>Pick one or more images to send to the frame.</p>
    <form method="POST" action="/upload" enctype="multipart/form-data">
      <input type="file" name="images" accept="image/*" multiple required>
      <button type="submit">Upload</button>
    </form>
    {msg}
  </div>
</body>
</html>"""


class UploadServer:
    """Small LAN-only web server so a phone/browser can push images to the frame.

    `on_image(pil_image, title)` is invoked on the server's worker thread once
    per uploaded file. It must persist the image itself (ImageManager is
    thread-safe) and marshal any GUI work back onto the Tk main thread.
    """

    def __init__(self, on_image, port: int = 8080, max_mb: int = 32):
        self.on_image = on_image
        self.port = port

        self.app = Flask(__name__)
        self.app.config["MAX_CONTENT_LENGTH"] = max_mb * 1024 * 1024
        self.app.add_url_rule("/", "index", self._index, methods=["GET"])
        self.app.add_url_rule("/upload", "upload", self._upload, methods=["POST"])

        self._thread = None

    def _index(self):
        return UPLOAD_PAGE.format(msg="")

    def _upload(self):
        files = request.files.getlist("images")
        saved = 0
        for storage in files:
            if not storage or not storage.filename:
                continue
            try:
                image = Image.open(storage.stream)
                image = ImageOps.exif_transpose(image)
                image.load()  # fully read before the request stream closes
                image.thumbnail((2048, 2048), Image.LANCZOS)  # cap stored size / RAM
            except Exception as e:
                logger.warning(f"Skipping unreadable/oversized upload {storage.filename!r}: {e}")
                continue
            title = storage.filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
            try:
                self.on_image(image, title or "Uploaded")
                saved += 1
            except Exception as e:
                logger.exception(f"Upload ingest failed: {e}")

        if saved:
            msg = f'<div class="msg">Added {saved} image(s) to the frame.</div>'
        else:
            msg = '<div class="msg" style="color:#ff5447">No valid images found.</div>'
        return UPLOAD_PAGE.format(msg=msg)

    def get_url(self) -> str:
        return f"http://{get_lan_ip()}:{self.port}/"

    def start(self):
        def _run():
            self.app.run(host="0.0.0.0", port=self.port, threaded=True,
                         use_reloader=False, debug=False)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()


def get_lan_ip() -> str:
    """Best-effort LAN IP (the address a phone on the same network would use)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip
