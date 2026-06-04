import logging
import os

from logging.handlers import RotatingFileHandler

_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
_LOG_PATH = os.path.join(_LOG_DIR, "app.log")


def setup_logging(level=logging.INFO):
    """Configure root logging once at startup: a rotating file handler plus the
    console, with timestamps and levels.

    A wall-mounted, headless frame has no visible stdout, so failures need to
    land in a durable, rotated log. Other modules just use
    ``logging.getLogger(__name__)``; only the entrypoint calls this.
    """
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
    except OSError:
        pass

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handlers = [logging.StreamHandler()]
    try:
        handlers.append(RotatingFileHandler(_LOG_PATH, maxBytes=1_000_000, backupCount=3))
    except OSError as e:
        print(f"Could not open log file {_LOG_PATH}: {e}")

    for h in handlers:
        h.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    for existing in list(root.handlers):
        root.removeHandler(existing)
    for h in handlers:
        root.addHandler(h)
