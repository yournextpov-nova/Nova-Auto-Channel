"""
Generates one image per scene using Google's Gemini 2.5 Flash Image
model ("Nano Banana"), which has a generous free tier. Uses the same
GEMINI_API_KEY you already created earlier.

Get a free key at https://aistudio.google.com/apikey
Set it as the GEMINI_API_KEY environment variable / GitHub secret.

NOTE: this is a free/no-cost approach, so characters will look
"on-model" but not pixel-identical across videos. If/when the channel
starts earning, swapping this file for a paid consistent-character
tool (e.g. one that accepts reference images) is the natural upgrade.
"""
import os
import time
import base64
import requests

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-2.5-flash-image"
API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{MODEL}:generateContent?key={GEMINI_API_KEY}"
)


def build_prompt(scene_description: str, config: dict) -> str:
    chars = config["characters"]
    style = config["art_style"]
    prompt = (
        f"{style}. Characters in scene: Nova ({chars['nova']}), "
        f"the cat ({chars['cat']}), the panda ({chars['panda']}). "
        f"Scene: {scene_description}"
    )
    return prompt[:900]


def generate_image(scene_description: str, config: dict, out_path: str,
                    width: int = 1344, height: int = 768, seed: int | None = None):
    prompt = build_prompt(scene_description, config)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }

    last_status = None
    last_text = ""
    for attempt in range(6):
        try:
            r = requests.post(API_URL, json=payload, timeout=180)
        except requests.exceptions.RequestException as e:
            print(f"Request error on attempt {attempt + 1}: {e}")
            time.sleep(15 * (attempt + 1))
            continue

        if r.status_code == 429:
            wait = 20 * (attempt + 1)
            print(f"Rate limited, waiting {wait}s before retry...")
            time.sleep(wait)
            continue

        if r.status_code == 200:
            data = r.json()
            try:
                parts = data["candidates"][0]["content"]["parts"]
                for part in parts:
                    if "inlineData" in part:
                        img_bytes = base64.b64decode(part["inlineData"]["data"])
                        with open(out_path, "wb") as f:
                            f.write(img_bytes)
                        return out_path
            except (KeyError, IndexError) as e:
                print(f"Unexpected response shape: {e} - {str(data)[:300]}")

        last_status = r.status_code
        last_text = r.text[:300] if r.text else ""
        print(f"Image attempt {attempt + 1} failed: status={last_status} body={last_text}")
        time.sleep(15 * (attempt + 1))

    raise RuntimeError(
        f"Image generation failed for scene: {scene_description} "
        f"(last status={last_status}, body={last_text})"
    )


def generate_all_scene_images(scenes: list[str], config: dict, out_dir: str = "scenes"):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    shared_seed = int(time.time()) % 100000
    for i, scene in enumerate(scenes):
        out_path = os.path.join(out_dir, f"scene_{i:02d}.png")
        generate_image(scene, config, out_path, seed=shared_seed)
        paths.append(out_path)
    return paths
