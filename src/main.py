import requests
from PIL import Image
from io import BytesIO
import os

def read_api_key():
    file_path = os.path.join(os.path.dirname(__file__), '..', 'key.secret')
    with open(file_path, 'r') as f:
        api_key = f.read().strip()
    return api_key

def get_dalle2_image(prompt):
    api_key = read_api_key()
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "response_format": "url"
    }

    # Send API request
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    print(response)

    # Get image URL from response
    image_url = response.json()["data"][0]["url"]

    # Download image from URL and return as PIL Image object
    image_data = requests.get(image_url).content
    image = Image.open(BytesIO(image_data))

    return image

if __name__ == "__main__":
    get_dalle2_image("cat").show() 