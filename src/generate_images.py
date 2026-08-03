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
   

def generate_thumbnail(story: dict, config: dict, out_path: str = "output/thumbnail.jpg"):
    """
    Generates a dedicated YouTube thumbnail: a more dramatic/close-up
    image than the in-video scenes, with the video title overlaid as
    bold, high-contrast text for readability at small sizes.
    """
    from PIL import Image, ImageDraw, ImageFont
    import textwrap

    chars = config["characters"]
    style = config["art_style"]

    # Use the first scene as the emotional anchor, but push for a more
    # eye-catching close-up composition than the in-video scenes use.
    first_scene = story["scenes"][0] if story.get("scenes") else story.get("title", "")
    thumb_prompt = (
        f"{style}. Extreme close-up, dramatic YouTube thumbnail composition, "
        f"expressive faces, high contrast, eye-catching. "
        f"Characters: Nova ({chars['nova']}), the cat ({chars['cat']}), "
        f"the panda ({chars['panda']}). Moment: {first_scene}"
    )[:600]

    # Reuse the existing image generation pipeline with the thumbnail prompt
    tmp_bg_path = out_path.replace(".jpg", "_bg.png")

    image = client.text_to_image(thumb_prompt, model=MODEL, width=1280, height=720)
    image.save(tmp_bg_path)

    # Overlay bold title text
    img = Image.open(tmp_bg_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    title = story.get("title", "")
    # Strip any " | category" suffix for the on-image text - keep just the hook
    display_text = title.split("|")[0].strip()

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
    except Exception:
        font = ImageFont.load_default()

    wrapped = textwrap.fill(display_text, width=18)
    lines = wrapped.split("\n")

    # Position text in the lower third with a semi-transparent bar behind it
    line_height = 95
    total_h = line_height * len(lines)
    y = img.height - total_h - 40

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [(0, y - 20), (img.width, img.height)],
        fill=(0, 0, 0, 140),
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (img.width - w) / 2
        # Stroke outline for readability over any background
        draw.text((x, y), line, font=font, fill="white",
                   stroke_width=4, stroke_fill="black")
        y += line_height

    img.save(out_path, quality=92)
    return out_path
