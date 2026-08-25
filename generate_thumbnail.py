"""
Builds a custom YouTube thumbnail: reuses one of the scene frames that
generate_clips.py already made (no extra image-generation call needed,
and it keeps the thumbnail visually consistent with the actual video),
then overlays bold, outlined title text - the classic bright,
high-contrast style used by most kids' YouTube channels.

Requires Pillow. Add this line to requirements.txt if it's not already
there:
    Pillow
"""
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

# DejaVu Sans Bold ships by default on GitHub Actions' ubuntu-latest
# runners. Falls back to Pillow's basic built-in font if not found,
# which will look plainer but won't crash the run.
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _load_font(size: int):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _draw_outlined_text(draw, xy, text, font, fill="white", outline="black", outline_width=6):
    x, y = xy
    for dx in range(-outline_width, outline_width + 1, 3):
        for dy in range(-outline_width, outline_width + 1, 3):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def generate_thumbnail(source_frame_path: str, thumb_text: str, out_path: str,
                        width: int = 1280, height: int = 720) -> str:
    """source_frame_path: one of the scene_XX_frame.png files already made
    during clip generation. thumb_text: a short, punchy phrase (a few
    words) - NOT the full SEO title, which is usually too long to read
    as thumbnail text."""
    img = Image.open(source_frame_path).convert("RGB")
    # Crop-to-fill so the thumbnail isn't stretched/distorted.
    src_ratio = img.width / img.height
    target_ratio = width / height
    if src_ratio > target_ratio:
        new_width = int(img.height * target_ratio)
        left = (img.width - new_width) // 2
        img = img.crop((left, 0, left + new_width, img.height))
    else:
        new_height = int(img.width / target_ratio)
        top = (img.height - new_height) // 2
        img = img.crop((0, top, img.width, top + new_height))
    img = img.resize((width, height))

    draw = ImageDraw.Draw(img)
    font = _load_font(100)
    wrapped = textwrap.fill(thumb_text.upper(), width=14)
    lines = wrapped.split("\n")[:3]  # cap at 3 lines so it never overflows

    line_heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]
    total_h = sum(line_heights) + 20 * (len(lines) - 1)
    y = height - total_h - 50  # bottom-anchored, standard thumbnail layout

    for line, line_h in zip(lines, line_heights):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (width - line_w) // 2
        _draw_outlined_text(draw, (x, y), line, font)
        y += line_h + 20

    img.save(out_path, quality=95)
    return out_path
