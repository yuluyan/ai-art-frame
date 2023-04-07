from PIL import Image
import os

def get_openai_key():
    file_path = os.path.join(os.path.dirname(__file__), '..', 'key.secret')
    with open(file_path, 'r') as f:
        api_key = f.read().strip()
    return api_key

def resize_image(image, width, height):
    return image.resize((width, height), Image.ANTIALIAS)