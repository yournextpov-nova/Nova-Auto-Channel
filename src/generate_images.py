"""
Generates one image per scene using Hugging Face Inference Providers
(FLUX.1-schnell, auto-routed to whichever provider currently serves it —
e.g. fal-ai, together, etc.). Character consistency is approximated by
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
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

HF_TOKEN = os.environ["HF_TOKEN"]
MODEL = "black-forest-labs/FLUX.1-schnell"

client = InferenceClient(provider="auto", api_key=HF_TOKEN)


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

    kwargs = {"width": width, "height": height}
    if seed is not None:
        kwargs["seed"] = seed

    last_error = None
    for attempt in range(8):
        try:
            image = client.text_to_image(prompt, model=MODEL, **kwargs)
            image.save(out_path)
            return out_path
        except HfHubHTTPError as e:
            last_error = e
            status = getattr(e.response, "status_code", None)
            print(f"Image attempt {attempt + 1} failed: status={status} error={e}")
            time.sleep(15 * (attempt + 1))
        except Exception as e:
            last_error = e
            print(f"Image attempt {attempt + 1} failed: {e}")
            time.sleep(15 * (attempt + 1))

    raise RuntimeError(
        f"Image generation failed for scene: {scene_description} (last error={last_error})"
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
