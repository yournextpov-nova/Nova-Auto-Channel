"""
Generates one image per scene using Pollinations.ai's free image API
(no API key required). Character consistency is approximated by
injecting the full character bible + art style into every prompt.

NOTE: this is a free/no-cost approach, so characters will look
"on-model" but not pixel-identical across videos. If/when the channel
starts earning, swapping this file for a paid consistent-character
tool (e.g. one that accepts reference images) is the natural upgrade.
"""
import os
import time
import urllib.parse
import requests

BASE_URL = "https://gen.pollinations.ai/image/{prompt}"


def build_prompt(scene_description: str, config: dict) -> str:
    chars = config["characters"]
    style = config["art_style"]
    return (
        f"{style}. Characters in scene: Nova ({chars['nova']}), "
        f"the cat ({chars['cat']}), the panda ({chars['panda']}). "
        f"Scene: {scene_description}"
    )


def generate_image(scene_description: str, config: dict, out_path: str,
                    width: int = 1344, height: int = 768, seed: int | None = None):
    prompt = build_prompt(scene_description, config)
    # Very long URLs can get rejected/timeout on some free hosts - keep it reasonable.
    if len(prompt) > 600:
        prompt = prompt[:600]
    encoded = urllib.parse.quote(prompt)
    url = BASE_URL.format(prompt=encoded)
    params = {"width": width, "height": height, "nologo": "true", "model": "flux"}
    if seed is not None:
        params["seed"] = seed

    last_status = None
    last_text = ""
    for attempt in range(6):
        try:
            r = requests.get(url, params=params, timeout=180)
        except requests.exceptions.RequestException as e:
            print(f"Request error on attempt {attempt + 1}: {e}")
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code == 200 and r.content:
            with open(out_path, "wb") as f:
                f.write(r.content)
            return out_path
        last_status = r.status_code
        last_text = r.text[:200] if r.text else ""
        print(f"Image attempt {attempt + 1} failed: status={last_status} body={last_text}")
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(
        f"Image generation failed for scene: {scene_description} "
        f"(last status={last_status}, body={last_text})"
    )


def generate_all_scene_images(scenes: list[str], config: dict, out_dir: str = "scenes"):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    # A shared seed keeps color/style palette closer across the batch.
    shared_seed = int(time.time()) % 100000
    for i, scene in enumerate(scenes):
        out_path = os.path.join(out_dir, f"scene_{i:02d}.png")
        generate_image(scene, config, out_path, seed=shared_seed)
        paths.append(out_path)
    return paths
