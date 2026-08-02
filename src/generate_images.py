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

BASE_URL = "https://image.pollinations.ai/prompt/{prompt}"


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
    encoded = urllib.parse.quote(prompt)
    url = BASE_URL.format(prompt=encoded)
    params = {"width": width, "height": height, "nologo": "true"}
    if seed is not None:
        params["seed"] = seed

    for attempt in range(3):
        r = requests.get(url, params=params, timeout=120)
        if r.status_code == 200 and r.content:
            with open(out_path, "wb") as f:
                f.write(r.content)
            return out_path
        time.sleep(5)
    raise RuntimeError(f"Image generation failed for scene: {scene_description}")


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
