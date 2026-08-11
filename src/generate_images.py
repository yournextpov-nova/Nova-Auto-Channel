"""
Generates one image per scene using Cloudflare Workers AI's free tier
(FLUX.1 Schnell model). Character consistency is approximated by
injecting the full character bible + art style into every prompt.

Setup (free, no credit card):
1. Sign up at https://dash.cloudflare.com/sign-up
2. Find your Account ID on the right side of the Workers & Pages
   dashboard overview page.
3. Go to "My Profile" -> "API Tokens" -> "Create Token" -> use the
   "Workers AI" template (or a custom token with "Workers AI - Read"
   and "Workers AI - Edit" permissions).
4. Set two GitHub secrets: CF_ACCOUNT_ID and CF_API_TOKEN.

NOTE: this is a free/no-cost approach, so characters will look
"on-model" but not pixel-identical across videos. If/when the channel
starts earning, swapping this file for a paid consistent-character
tool (e.g. one that accepts reference images) is the natural upgrade.
"""
import os
import time
import base64
import requests

CF_ACCOUNT_ID = os.environ["CF_ACCOUNT_ID"]
CF_API_TOKEN = os.environ["CF_API_TOKEN"]
MODEL = "@cf/black-forest-labs/flux-1-schnell"
API_URL = (
    f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
    f"/ai/run/{MODEL}"
)


def build_prompt(scene_description: str, config: dict) -> str:
    chars = config["characters"]
    style = config["art_style"]
    # Scene action goes FIRST so it never gets cut off by truncation -
    # this is the most important part of the prompt.
    prompt = (
        f"{scene_description}. "
        f"{style}. "
        f"Nova: {chars['nova'][:180]} "
        f"Cat: {chars['cat'][:120]} "
        f"Panda: {chars['panda'][:120]}"
    )
    return prompt[:900]


def generate_image(scene_description: str, config: dict, out_path: str,
                    width: int = 1344, height: int = 768, seed: int | None = None):
    prompt = build_prompt(scene_description, config)
    headers = {"Authorization": f"Bearer {CF_API_TOKEN}"}
    payload = {"prompt": prompt}
    if seed is not None:
        payload["seed"] = seed

    last_status = None
    last_text = ""
    for attempt in range(6):
        try:
            r = requests.post(API_URL, headers=headers, json=payload, timeout=180)
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
                b64_img = data["result"]["image"]
                img_bytes = base64.b64decode(b64_img)
                with open(out_path, "wb") as f:
                    f.write(img_bytes)
                return out_path
            except (KeyError, TypeError) as e:
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
    base_seed = int(time.time()) % 100000
    for i, scene in enumerate(scenes):
        if i > 0:
            time.sleep(5)
        out_path = os.path.join(out_dir, f"scene_{i:02d}.png")
        generate_image(scene, config, out_path, seed=base_seed + i)
        paths.append(out_path)
    return paths
