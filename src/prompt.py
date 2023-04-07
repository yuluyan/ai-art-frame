import requests

from utils import get_openai_key

def speech_to_prompt(short_idea: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_openai_key()}"
    }

    messages = [
        {
            "role": "system",
            "content": 'You are a prompt engineer to help to create prompt for stable diffusion artworks.'
        },
        {
            "role": "user",
            "content": 
f"""You are an expert AI image prompt generator. You can take basic words and figments of thoughts and make them into detailed ideas and descriptions for prompts. I will be copy pasting these prompts into an AI image generator (Midjourney). Please provide the prompts in a code box so I can copy and paste it. Use the following examples I’ve written as the format:
Example 1: 
street style photo of an elderly french woman with deep wrinkles and a warm smile, walking down the streets of soho, wearing a white gucci blazer made of cotton & black eyeglasses, natural morning lighting, shot on Agfa Vista 200, 4k

Example 2:
french woman w/ deep wrinkles & a warm smile, sitting in a charming soho cafe filled w/ plants, looking out the window, wearing a bright pastel linen blazer & floral silk blouse, natural light shining through the window & reflecting off her eyeglass, golden hour, shot on Kodak Portra 400

Based on the idea of {short_idea}, generate one prompt, and prompt only with no other text.
"""
        },
    ]

    data = {
        "messages": messages,
        "model": "gpt-3.5-turbo",
        "max_tokens": 200,
        "n": 1,
        "stop": None,
        "temperature": 0.8
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        response_data = response.json()
        generated_text = response_data["choices"][0]["message"]["content"]
        return generated_text
    else:
        raise Exception(f"Request failed with status code {response.status_code}")


if __name__ == "__main__":
    short_idea = "tree"
    generated_text = speech_to_prompt(short_idea)
    print(generated_text)