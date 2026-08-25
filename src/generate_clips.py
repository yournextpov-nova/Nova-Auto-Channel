"""
Generates one short ANIMATED clip per scene, instead of a static image.

Pipeline per scene:
  1. Cloudflare Workers AI (FLUX.1 Schnell, free) makes a starting frame -
     reuses the same character-bible prompt trick as before, for consistency.
  2. That frame is uploaded to catbox.moe (free, no signup) just to get it
     a public URL, because Agnes's image-to-video endpoint requires one.
  3. Agnes AI's free agnes-video-v2.0 model animates that frame into a clip.

Agnes clips are capped at a maximum of ~441 frames per call (~18.4s at
24fps). If a segment's narration is longer than that, this file
automatically chains multiple Agnes calls - each new clip starts from
the last frame of the previous one, so the motion keeps flowing - then
concatenates them and trims/pads the result to match the narration's
exact duration.

Setup:
  - Everything from generate_images.py still applies (CF_ACCOUNT_ID,
    CF_API_TOKEN as GitHub secrets).
  - NEW: sign up free at https://agnes-ai.com, create an API key, and
    add it as a GitHub secret named AGNES_API_KEY.
"""
import os
import time
import base64
import subprocess
import requests

CF_ACCOUNT_ID = os.environ["CF_ACCOUNT_ID"]
CF_API_TOKEN = os.environ["CF_API_TOKEN"]
AGNES_API_KEY = os.environ["AGNES_API_KEY"]
IMGBB_API_KEY = os.environ["IMGBB_API_KEY"]

FLUX_MODEL = "@cf/black-forest-labs/flux-1-schnell"
FLUX_URL = (
    f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
    f"/ai/run/{FLUX_MODEL}"
)

AGNES_BASE = "https://apihub.agnes-ai.com/v1"
AGNES_MODEL = "agnes-video-v2.0"

# Agnes only accepts frame counts that satisfy 8n + 1, capped at 441.
FRAME_OPTIONS = [81, 121, 161, 241, 441]
FRAME_RATE = 24
MAX_CLIP_SECONDS = FRAME_OPTIONS[-1] / FRAME_RATE  # ~18.4s


def build_prompt(scene_description: str, config: dict) -> str:
    """Used for the FLUX starting image - needs full character detail
    since there's no prior frame to anchor appearance yet.

    Only includes a character's description if that character is
    actually named in this scene. Previously all three character bios
    were appended to every prompt regardless of relevance - if a scene
    already mentioned "the cat" and then the bible text described the
    cat again right after, that character effectively got named twice
    in one prompt, which is a known trigger for diffusion models to
    render two of that subject (mirrored/symmetric duplicates)."""
    chars = config["characters"]
    style = config["art_style"]
    lower_scene = scene_description.lower()

    char_lines = []
    if "nova" in lower_scene:
        char_lines.append(f"Nova: {chars['nova'][:180]}")
    if "cat" in lower_scene:
        char_lines.append(f"Cat: {chars['cat'][:120]}")
    if "panda" in lower_scene or "momo" in lower_scene:
        char_lines.append(f"Panda: {chars['panda'][:120]}")
    char_block = " ".join(char_lines)

    prompt = (
        f"{scene_description}. "
        f"{style}. "
        f"{char_block} "
        f"Exactly one of each character shown - solo individuals, "
        f"no duplicates, no twins, no mirrored copies."
    )
    return prompt[:900]


def build_motion_prompt(scene_description: str) -> str:
    """Used for Agnes image-to-video. Deliberately does NOT re-describe
    character appearance - the starting image already shows exactly who
    is in the scene, and re-describing them in detail here has caused
    Agnes to render duplicate characters (e.g. two cats), since a strong
    text description reads as an instruction to add that character
    rather than just animate the one already in frame."""
    return (
        f"Animate this exact scene with smooth, natural motion: {scene_description}. "
        f"Keep every character's appearance and count EXACTLY as shown in the "
        f"starting image - do not add, duplicate, mirror, or remove any "
        f"characters. If the image shows one cat, keep exactly one cat."
    )[:900]


def generate_frame_image(scene_description: str, config: dict, out_path: str,
                          width: int = 1344, height: int = 768, seed: int | None = None):
    """Produces the starting frame. NOTE: flux-1-schnell's schema does not
    accept a 'seed' field (unlike some other Workers AI image models), so
    it is intentionally not sent even though it's still accepted as an
    argument here for compatibility with the rest of the code."""
    prompt = build_prompt(scene_description, config)
    headers = {"Authorization": f"Bearer {CF_API_TOKEN}"}
    payload = {"prompt": prompt}

    last_status, last_text = None, ""
    for attempt in range(6):
        try:
            r = requests.post(FLUX_URL, headers=headers, json=payload, timeout=180)
        except requests.exceptions.RequestException as e:
            print(f"Image request error on attempt {attempt + 1}: {e}")
            time.sleep(15 * (attempt + 1))
            continue
        if r.status_code == 429:
            wait = 20 * (attempt + 1)
            print(f"Image rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue
        if r.status_code == 200:
            data = r.json()
            try:
                img_bytes = base64.b64decode(data["result"]["image"])
                with open(out_path, "wb") as f:
                    f.write(img_bytes)
                return out_path
            except (KeyError, TypeError) as e:
                print(f"Unexpected image response shape: {e} - {str(data)[:300]}")
        last_status, last_text = r.status_code, (r.text[:300] if r.text else "")
        print(f"Image attempt {attempt + 1} failed: status={last_status} body={last_text}")
        time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"Frame generation failed for: {scene_description} (status={last_status})")


def upload_to_public_url(local_path: str) -> str:
    """Agnes image-to-video needs a public image URL, not a raw file upload.
    Uses imgbb (free, key required) - catbox.moe was tried first but blocks
    GitHub Actions' datacenter IP range with a 412, so this replaced it."""
    with open(local_path, "rb") as f:
        r = requests.post(
            "https://api.imgbb.com/1/upload",
            params={"key": IMGBB_API_KEY},
            files={"image": f},
            timeout=60,
        )
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"imgbb upload failed: {data}")
    return data["data"]["url"]


def _frames_for(seconds: float) -> int:
    """Smallest Agnes-allowed frame count that covers `seconds`, capped at max."""
    needed = seconds * FRAME_RATE
    for f in FRAME_OPTIONS:
        if f >= needed:
            return f
    return FRAME_OPTIONS[-1]


def _submit_agnes_video(prompt: str, image_url: str, num_frames: int) -> str:
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": AGNES_MODEL,
        "prompt": prompt,
        "image": image_url,
        "width": 1152,
        "height": 768,
        "num_frames": num_frames,
        "frame_rate": FRAME_RATE,
    }
    r = requests.post(f"{AGNES_BASE}/videos", headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["id"]


def _extract_video_url(data: dict) -> str | None:
    """Agnes V2.0's docs say the URL lives at metadata.url, but other
    Agnes model versions/docs have shown video_url or url at the top
    level - check all of them so this doesn't break again if the API
    is inconsistent."""
    if data.get("video_url"):
        return data["video_url"]
    if data.get("url"):
        return data["url"]
    metadata = data.get("metadata") or {}
    if metadata.get("url"):
        return metadata["url"]
    return None


def _poll_agnes_video(task_id: str, timeout: int = 600) -> str:
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}"}
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{AGNES_BASE}/videos/{task_id}", headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        if status == "completed":
            video_url = _extract_video_url(data)
            if not video_url:
                raise RuntimeError(f"Agnes task {task_id} completed but no video URL found in response: {data}")
            return video_url
        if status == "failed":
            raise RuntimeError(f"Agnes video task {task_id} failed: {data}")
        time.sleep(10)
    raise RuntimeError(f"Agnes video task {task_id} timed out after {timeout}s")


def _animate_one_clip(prompt: str, image_url: str, seconds: float, out_path: str) -> float:
    """Submits + polls + downloads one Agnes clip. Returns the actual clip length."""
    num_frames = _frames_for(seconds)
    last_err = None
    for attempt in range(4):
        try:
            task_id = _submit_agnes_video(prompt, image_url, num_frames)
            video_url = _poll_agnes_video(task_id)
            r = requests.get(video_url, timeout=120)
            r.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(r.content)
            return num_frames / FRAME_RATE
        except requests.exceptions.HTTPError as e:
            last_err = e
            wait = 20 * (attempt + 1)
            print(f"Agnes attempt {attempt + 1} failed: {e}. Waiting {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"Agnes animation failed after retries: {last_err}")


def _extract_last_frame(video_path: str, out_path: str):
    subprocess.run(
        ["ffmpeg", "-y", "-sseof", "-0.1", "-i", video_path, "-frames:v", "1", out_path],
        check=True, capture_output=True,
    )


def _match_duration(clip_path: str, target_seconds: float, out_path: str):
    """Trims or freeze-pads a clip to exactly `target_seconds`."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", clip_path,
         "-vf", f"tpad=stop_mode=clone:stop_duration={max(target_seconds, 0.1)}",
         "-t", str(target_seconds), out_path],
        check=True, capture_output=True,
    )


def generate_clip_for_scene(scene_description: str, config: dict, duration: float,
                             out_dir: str, index: int, seed: int) -> str:
    """One segment's animated clip, chaining multiple Agnes calls if needed."""
    os.makedirs(out_dir, exist_ok=True)
    image_prompt = build_prompt(scene_description, config)
    motion_prompt = build_motion_prompt(scene_description)

    frame_path = os.path.join(out_dir, f"scene_{index:02d}_frame.png")
    generate_frame_image(scene_description, config, frame_path, seed=seed)
    image_url = upload_to_public_url(frame_path)

    remaining = duration
    part_paths = []
    part = 0
    while remaining > 0:
        this_len = min(remaining, MAX_CLIP_SECONDS)
        part_out = os.path.join(out_dir, f"scene_{index:02d}_part{part}.mp4")
        actual_len = _animate_one_clip(motion_prompt, image_url, this_len, part_out)
        part_paths.append(part_out)
        remaining -= actual_len
        part += 1
        if remaining > 0:
            next_frame = os.path.join(out_dir, f"scene_{index:02d}_frame{part}.png")
            _extract_last_frame(part_out, next_frame)
            image_url = upload_to_public_url(next_frame)
        if part > 5:  # safety valve against runaway segments
            break

    if len(part_paths) == 1:
        raw_clip = part_paths[0]
    else:
        concat_list = os.path.join(out_dir, f"scene_{index:02d}_concat.txt")
        with open(concat_list, "w") as f:
            for p in part_paths:
                f.write(f"file '{os.path.abspath(p)}'\n")
        raw_clip = os.path.join(out_dir, f"scene_{index:02d}_joined.mp4")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
             "-c", "copy", raw_clip],
            check=True, capture_output=True,
        )

    final_clip = os.path.join(out_dir, f"scene_{index:02d}.mp4")
    _match_duration(raw_clip, duration, final_clip)
    return final_clip


def generate_all_scene_clips(scenes: list[str], durations: list[float], config: dict,
                              out_dir: str = "scenes"):
    os.makedirs(out_dir, exist_ok=True)
    clip_paths = []
    base_seed = int(time.time()) % 100000
    for i, (scene, duration) in enumerate(zip(scenes, durations)):
        if i > 0:
            time.sleep(3)  # be polite to Agnes's free 20 RPM limit
        print(f"  scene {i + 1}/{len(scenes)} ({duration:.1f}s)...")
        clip_path = generate_clip_for_scene(scene, config, duration, out_dir, i, base_seed + i)
        clip_paths.append(clip_path)
    return clip_paths
