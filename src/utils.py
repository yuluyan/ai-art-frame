import os
import re

from datetime import date
from PIL import Image

def get_openai_key():
    file_path = os.path.join(os.path.dirname(__file__), '..', 'key.secret')
    with open(file_path, 'r') as f:
        api_key = f.read().strip()
    return api_key

def fit_image(image, width, height, background=(0, 0, 0)):
    """Scale `image` to fit within (width, height) preserving its aspect ratio,
    centered on a solid `background` (letterbox). Returns an RGB image exactly
    (width, height) in size, so the source is never stretched/distorted."""
    src_w, src_h = image.size
    scale = min(width / src_w, height / src_h)
    new_w = max(1, round(src_w * scale))
    new_h = max(1, round(src_h * scale))
    fitted = image.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGB", (width, height), background)
    offset = ((width - new_w) // 2, (height - new_h) // 2)
    if fitted.mode in ("RGBA", "LA", "P"):
        fitted = fitted.convert("RGBA")
        canvas.paste(fitted, offset, fitted)
    else:
        canvas.paste(fitted, offset)
    return canvas

def date_serializer(obj):
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError("Type not serializable")

def date_deserializer(obj):
    for key, value in obj.items():
        if isinstance(value, str) and re.match(r'\d{4}-\d{2}-\d{2}', value):
            obj[key] = date.fromisoformat(value)
    return obj