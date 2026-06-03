import requests

from utils import get_openai_key

# A small, current chat model is plenty for turning a spoken idea into a vivid
# art-direction sentence. gpt-image-2 follows natural language well, so we no
# longer emit Stable-Diffusion-style comma "soup".
PROMPT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You are an art director who turns a short spoken idea into a single vivid, "
    "concrete prompt for an AI image generator (gpt-image-2). Write natural, "
    "descriptive English."
)

USER_TEMPLATE = """Turn the idea below into ONE image prompt for gpt-image-2.

Guidelines:
- Write 1-3 sentences of natural language (NOT a comma-separated tag list).
- Describe the subject, setting, composition, lighting, color palette, mood, and artistic medium/style.
- Be concrete and evocative; avoid brand names, real public figures, embedded text, and watermarks.
- Output ONLY the prompt, with no preamble, quotes, or extra commentary.

Idea: '{idea}'"""


def speech_to_prompt(short_idea: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_openai_key()}"
    }
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(idea=short_idea)},
    ]
    data = {
        "messages": messages,
        "model": PROMPT_MODEL,
        "max_tokens": 600,
        "n": 1,
        "temperature": 0.8,
    }

    response = requests.post(url, headers=headers, json=data, timeout=60)
    if response.status_code == 200:
        response_data = response.json()
        generated_text = response_data["choices"][0]["message"]["content"]
        return generated_text.strip()
    else:
        print(response.text)
        raise Exception(f"Request failed with status code {response.status_code}")


if __name__ == "__main__":
    print(speech_to_prompt("modern japanese architecture, detailed"))
