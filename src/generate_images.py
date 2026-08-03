"""
Generates one image per scene using Hugging Face's free Inference API
(FLUX.1-schnell model). Character consistency is approximated by
injecting the full character bible + art style into every prompt.

Get a free token at https://huggingface.co/settings/tokens
(choose "Read" access - that's enough). Set it as the HF_TOKEN
environment variable / GitHub secret.

NOTE: this is a free/no-cost approach, so characters will look
"on-model" but not pixel-identical across videos. If/when the channel
starts earning, swapping this file for a paid consistent-character
tool (e.g. one that accepts reference images) is the natural upgrade.
"""
import os
import time
import requests

HF_TOKEN = os.environ["HF_TOKEN"]
MODEL = "black-forest-labs/FLUX.1-schnell"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"


def build_prompt(scene_description: str, config: dict) -> str:
    chars = config["characters"]
    style = config["art_style"]
    prompt = (
        f"{style}. Characters in scene: Nova ({chars['nova']}), "
        f"the cat ({chars['cat']}), the panda ({chars['panda']}). "
        f"Scene: {scene_description}"
    )
    return prompt[:600]


def generate_image(scene_description: str, config: dict, out_path: str,
                    width: int = 1344, height: int = 768, seed: int | None = None):
    prompt = build_prompt(scene_description, config)
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {"width": width, "height": height},
    }
    if seed is not None:
        payload["parameters"]["seed"] = seed

    last_status = None
    last_text = ""
    for attempt in range(8):
        try:
            r = requests.post(API_URL, headers=headers, json=payload, timeout=180)
        except requests.exceptions.RequestException as e:
            print(f"Request error on attempt {attempt + 1}: {e}")
            time.sleep(15 * (attempt + 1))
            continue

        content_type = r.headers.get("content-type", "")
        if r.status_code == 200 and content_type.startswith("image/"):
            with open(out_path, "wb") as f:
                f.write(r.content)
            return out_path

        if r.status_code == 503:
            try:
                wait = float(r.json().get("estimated_time", 20))
            except Exception:
                wait = 20
            print(f"Model loading, waiting {wait:.0f}s before retry...")
            time.sleep(wait + 2)
            continue

        last_status = r.status_code
        last_text = r.text[:200] if r.text else ""
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
