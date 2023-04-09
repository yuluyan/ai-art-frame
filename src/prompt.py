import requests

from utils import get_openai_key

EXAMPLE_PROMPTS = [
    "portait of a homer simpson archer shooting arrow at forest monster, front game card, drark, marvel comics, dark, intricate, highly detailed, smooth, artstation, digital illustration",
    "ghost inside a hunted room, art by lois van baarle and loish and ross tran and rossdraws and sam yang and samdoesarts and artgerm, digital art, highly detailed, intricate, sharp focus, Trending on Artstation HQ, deviantart, unreal engine 5, 4K UHD image",
    "red dead redemption 2, cinematic view, epic sky, detailed, concept art, low angle, high detail, warm lighting, volumetric, godrays, vivid, beautiful, trending on artstation",
    "athena, greek goddess, claudia black, art by artgerm and greg rutkowski and magali villeneuve, bronze greek armor, owl crown, d & d, fantasy, intricate, portrait, highly detailed, headshot, digital painting, trending on artstation, concept art, sharp focus, illustration",
    "portrait of beautiful happy young ana de armas, ethereal, realistic anime, trending on pixiv, detailed, clean lines, sharp lines, crisp lines, award winning illustration, masterpiece, 4k, eugene de blaas and ross tran, vibrant color scheme, intricately detailed",
    "A highly detailed and hyper realistic portrait of a gorgeous young ana de armas, lisa frank, trending on artstation, butterflies, floral, sharp focus, studio photo, intricate details, highly detailed, alberto seveso and geo2099 style",
    "cabela’s tent futuristic pop up family pod, cabin, modular, person in foreground, mountainous forested wilderness open fields, beautiful views, painterly concept art, joanna gaines, environmental concept art, farmhouse, magnolia, concept art illustration by ross tran, by james gurney, by craig mullins, by greg rutkowski trending on artstation",
    "a cute magical flying dog, fantasy art drawn by disney concept artists, golden colour, high quality, highly detailed, elegant, sharp focus, concept art, character concepts, digital painting, mystery, adventure",
    "Residential home high end futuristic interior, olson kundig::1 Interior Design by Dorothy Draper, maison de verre, axel vervoordt::2 award winning photography of an indoor-outdoor living library space, minimalist modern designs::1 high end indoor/outdoor residential living space, rendered in vray, rendered in octane, rendered in unreal engine, architectural photography, photorealism, featured in dezeen, cristobal palma::2.5 chaparral landscape outside, black surfaces/textures for furnishings in outdoor space",
    "interior design, open plan, kitchen and living room, modular furniture with cotton textiles, wooden floor, high ceiling, large steel windows viewing a city",
    "Realistic architectural rendering of a capsule multiple house within concrete giant blocks with moss and tall rounded windows with lights in the interior, human scales, fog like london, in the middle of a contemporary city of Tokyo, stylish, generative design, nest, spiderweb structure, silkworm thread patterns, realistic, Designed based on Kengo Kuma, Sou Fujimoto, cinematic, unreal engine, 8K, HD, volume twilight",
    "the living room of a cozy wooden house with a fireplace, at night, interior design, d & d concept art, d & d wallpaper, warm, digital art. art by james gurney and larry elmore.",
]

SUFFIXES =[w.strip().lower() for w in """
photograph, high quality, f 1.8, soft focus, 8k, national geographic, award - winning photograph by nick nichols, home, interior, octane render, deviantart, cinematic, key art, hyperrealism, sun light, sunrays, canon eos c 300, ƒ 1.8, 35 mm, 8k, medium-format print	,
shot 35 mm, realism, octane render, 8k, trending on artstation, 35 mm camera, unreal engine, hyper detailed, photo - realistic maximum detail, volumetric light, realistic matte painting, hyper photorealistic, trending on artstation, ultra - detailed, realistic	,
anthro, very cute kid's film character, disney pixar zootopia character concept artwork, 3d concept, detailed fur, high detail iconic character for upcoming film, trending on artstation, character design, 3d artistic render, highly detailed, octane, blender, cartoon, shadows, lighting	,
character sheet, concept design, contrast, style by kim jung gi, zabrocki, karlkka, jayison devadas, trending on artstation, 8k, ultra wide angle, pincushion lens effect,	
cyberpunk, in heavy raining futuristic tokyo rooftop cyberpunk night, sci-fi, fantasy, intricate, very very beautiful, elegant, neon light, highly detailed, digital painting, artstation, concept art, soft light, hdri, smooth, sharp focus, illustration, art by tian zi and craig mullins and wlop and alphonse much	,
ultra realistic, concept art, intricate details, highly detailed, photorealistic, octane render, 8k, unreal engine, sharp focus, volumetric lighting unreal engine. art by artgerm and alphonse mucha	,
epic concept art by barlowe wayne, ruan jia, light effect, volumetric light, 3d, ultra clear detailed, octane render, 8k, dark green, colour scheme	,
cute, funny, centered, award winning watercolor pen illustration, detailed, disney, isometric illustration, drawing, by Stephen Hillenburg, Matt Groening, Albert Uderzo	,
full body, highly detailed and intricate, golden ratio, vibrant colors, hyper maximalist, futuristic, city background, luxury, elite, cinematic, fashion, depth of field, colorful, glow, trending on artstation, ultra high detail, ultra realistic, cinematic lighting, focused, 8k,	
birds in the sky, waterfall close shot 35 mm, realism, octane render, 8 k, exploration, cinematic, trending on artstation, 35 mm camera, unreal engine, hyper detailed, photo - realistic maximum detail, volumetric light, moody cinematic epic concept art, realistic matte painting, hyper photorealistic, epic, trending on artstation, movie concept art, cinematic composition, ultra-detailed, realistic	,
depth of field. bokeh. soft light. by Yasmin Albatoul, Harry Fayt. centered. extremely detailed. Nikon D850, (35mm|50mm|85mm). award winning photography.	,
photograph, highly detailed face, depth of field, moody light, golden hour, style by Dan Winters, Russell James, Steve McCurry, centered, extremely detailed, Nikon D850, award winning photography	,
fog, animals, birds, deer, bunny, postapocalyptic, overgrown with plant life and ivy, artgerm, yoshitaka amano, gothic interior, 8k, octane render, unreal engine	,
blueprint, hyperdetailed vector technical documents, callouts, legend, patent registry	,
sketch, drawing, detailed, pencil, black and white by Adonna Khare, Paul Cadden, Pierre-Yves Riveau	,
by Andrew McCarthy, Navaneeth Unnikrishnan, Manuel Dietrich, photo realistic, 8 k, cinematic lighting, hd, atmospheric, hyperdetailed, trending on artstation, deviantart, photography, glow effect	,
icons, 2d icons, rpg skills icons, world of warcraft, league of legends, ability icon, fantasy, potions, spells, objects, flowers, gems, swords, axe, hammer, fire, ice, arcane, shiny object, graphic design, high contrast, artstation	,
steampunk cybernetic biomechanical, 3d model, very coherent symmetrical artwork, unreal engine realistic render, 8k, micro detail, intricate, elegant, highly detailed, centered, digital painting, artstation, smooth, sharp focus, illustration, artgerm, Caio Fantini, wlop	,
photorealistic, vivid, sharp focus, reflection, refraction, sunrays, very detailed, intricate, intense cinematic composition,
""".split(",") if w.strip() != ""]

def speech_to_prompt(short_idea: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_openai_key()}"
    }
    nl = "\n"
    messages = [
        {
            "role": "system",
            "content": 'You are a prompt engineer to help to create prompt for stable diffusion artworks.'
        },
        {
            "role": "user",
            "content": 
f"""You are an expert AI image prompt generator. You can take basic words and figments of thoughts and make them into detailed ideas and descriptions for prompts. 
Prompts should be written in English, each prompt is comma separated list of short phrases that contains a description of the scene and modifiers. Each prompt should contain at leat 30 phrases.
Here is a list of modifies: {", ".join(SUFFIXES)}. You can use any of these, or make up your own.
Here are some examples of prompts, separated by semicolon:
Examples:
{nl.join(["- " + ex for ex in EXAMPLE_PROMPTS])}
Based on the idea of '{short_idea}', generate one prompt. Do not include any other text or special characters when returning the prompt.
"""
        },
    ]
    data = {
        "messages": messages,
        "model": "gpt-3.5-turbo",
        "max_tokens": 2000,
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
        print(response.text)
        raise Exception(f"Request failed with status code {response.status_code}")


if __name__ == "__main__":
    short_idea = "modern japanese architecture, detailed"
    generated_text = speech_to_prompt(short_idea)
    print(generated_text)