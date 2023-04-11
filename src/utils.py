import os
import re

from datetime import date
from PIL import Image

def get_openai_key():
    file_path = os.path.join(os.path.dirname(__file__), '..', 'key.secret')
    with open(file_path, 'r') as f:
        api_key = f.read().strip()
    return api_key

def get_sd_port():
    file_path = os.path.join(os.path.dirname(__file__), '..', 'sdport.secret')
    with open(file_path, 'r') as f:
        api_key = f.read().strip()
    return api_key

def resize_image(image, width, height):
    return image.resize((width, height), Image.ANTIALIAS)

def date_serializer(obj):
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError("Type not serializable")

def date_deserializer(obj):
    for key, value in obj.items():
        if isinstance(value, str) and re.match(r'\d{4}-\d{2}-\d{2}', value):
            obj[key] = date.fromisoformat(value)
    return obj