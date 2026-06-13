import requests

from utils import get_openai_key

# A small, current chat model is plenty for turning a spoken idea into a vivid
# art-direction sentence. gpt-image-2 follows natural language well, so we no
# longer emit Stable-Diffusion-style comma "soup".
PROMPT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You are an art director who expands a short spoken idea into a single vivid, "
    "concrete prompt for an AI image generator (gpt-image-2). Stay strictly "
    "faithful to what the user asked for: keep their exact subject and every "
    "detail they named, and enrich it only with setting, light, and mood. Never "
    "drop or replace the subject. Write natural, descriptive English."
)

# Neutral rewrite — honors any medium/style the user happens to speak ("Plain").
USER_TEMPLATE = """Turn the idea below into ONE image prompt for gpt-image-2.

Guidelines:
- Keep the idea's exact subject and every specific detail it names (objects, counts, colors, actions, relationships). These are hard requirements: never omit, swap, generalize, or invent over them — build the scene around them.
- Write 1-3 sentences of natural language (NOT a comma-separated tag list).
- Describe the subject, setting, composition, lighting, color palette, mood, and artistic medium/style.
- Be concrete and evocative; avoid brand names, real public figures, embedded text, and watermarks.
- Output ONLY the prompt, with no preamble, quotes, or extra commentary.

Idea: '{idea}'"""

# Styled rewrite — the per-style {directive} replaces the open-ended medium/style
# line so the rewritten prompt always renders the idea in the chosen style.
USER_TEMPLATE_STYLED = """Turn the idea below into ONE image prompt for gpt-image-2.

Guidelines:
- Keep the idea's exact subject and every specific detail it names (objects, counts, colors, actions, relationships). These are hard requirements: never omit, swap, generalize, or invent over them — build the scene around them.
- Write 1-3 sentences of natural language (NOT a comma-separated tag list).
- Describe the subject, setting, composition, lighting, color palette, and mood.
- {directive}
- Be concrete and evocative; avoid brand names, real public figures, embedded text, and watermarks.
- Output ONLY the prompt, with no preamble, quotes, or extra commentary.

Idea: '{idea}'"""

STYLE_PLAIN = "plain"

# Style presets for the NEW style picker. Each entry's `directive` is injected
# into USER_TEMPLATE_STYLED to steer the gpt-4o-mini rewrite toward that medium.
# "plain" has no directive and uses the neutral template above. The styling lives
# entirely in the rewrite, so a `verbose` / chatgpt-off prompt (which skips the
# rewrite) is unstyled by design.
STYLE_PRESETS = {
    "plain": {
        "label": "Plain",
        "directive": None,
    },
    "realistic": {
        "label": "Realistic Photo",
        "directive": "Render the scene as a photorealistic photograph — natural lighting, lifelike textures, true-to-life color, and realistic depth of field, as if captured on a high-quality camera.",
    },
    "oil": {
        "label": "Oil Painting",
        "directive": "Render the scene as a traditional oil painting — visible brushwork, rich impasto texture, layered pigments, and a classical painted-canvas feel.",
    },
    "watercolor": {
        "label": "Watercolor",
        "directive": "Render the scene as a delicate watercolor painting — soft translucent washes, bleeding pigments, gentle gradients, and visible paper texture.",
    },
    "anime": {
        "label": "Anime",
        "directive": "Render the scene in a modern anime / cel-shaded illustration style — clean linework, expressive characters, vibrant flat colors, and dynamic composition.",
    },
    "popart": {
        "label": "Pop Art",
        "directive": "Render the scene as bold pop art — flat saturated colors, heavy black outlines, halftone dot shading, and a graphic comic-book sensibility.",
    },
    "impressionist": {
        "label": "Impressionist",
        "directive": "Render the scene as an impressionist painting — loose visible brushstrokes, emphasis on shifting light and atmosphere, soft edges, and vibrant broken color.",
    },
    "pixel": {
        "label": "Pixel Art",
        "directive": "Render the scene as detailed retro pixel art — a limited color palette, crisp aligned pixels, and a 16-bit video-game aesthetic with clear, readable shapes.",
    },
    "minimalist": {
        "label": "Minimalist",
        "directive": "Render the scene in a minimalist style — simple clean composition, a limited palette, generous negative space, and bold flat shapes.",
    },
}

# Row-major display order for the 3x3 picker grid (Plain in the center cell).
STYLE_ORDER = [
    "realistic", "oil", "watercolor",
    "anime", "plain", "impressionist",
    "pixel", "popart", "minimalist",
]


def speech_to_prompt(short_idea: str, style: str = STYLE_PLAIN) -> str:
    preset = STYLE_PRESETS.get(style) or STYLE_PRESETS[STYLE_PLAIN]
    directive = preset.get("directive")
    if directive:
        user_content = USER_TEMPLATE_STYLED.format(idea=short_idea, directive=directive)
    else:
        user_content = USER_TEMPLATE.format(idea=short_idea)

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_openai_key()}"
    }
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    data = {
        "messages": messages,
        "model": PROMPT_MODEL,
        "max_tokens": 600,
        "n": 1,
        # Lower than a typical "be creative" setting: the rewrite should enrich
        # the idea, not drift off it and lose the user's named subject.
        "temperature": 0.6,
    }

    response = requests.post(url, headers=headers, json=data, timeout=60)
    if response.status_code == 200:
        response_data = response.json()
        generated_text = response_data["choices"][0]["message"]["content"]
        return generated_text.strip()
    else:
        raise RuntimeError(f"Prompt generation {response.status_code}: {response.text.strip()}")


if __name__ == "__main__":
    print(speech_to_prompt("modern japanese architecture, detailed"))
