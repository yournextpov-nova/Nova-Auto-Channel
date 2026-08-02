"""
Assembles the final video from scene images + the voiceover mp3 using
ffmpeg (must be installed - it's pre-installed on GitHub Actions'
ubuntu-latest runners via `apt-get install ffmpeg`).

Each image gets an equal slice of the audio's total duration, with a
slow "Ken Burns" zoom/pan and a cross-fade into the next image.
"""
import subprocess
import json
import os


def get_audio_duration(audio_path: str) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", audio_path,
    ])
    return float(json.loads(out)["format"]["duration"])


def assemble_video(image_paths: list[str], audio_path: str, out_path: str,
                    width: int = 1920, height: int = 1080):
    duration = get_audio_duration(audio_path)
    per_image = duration / len(image_paths)
    fade_dur = min(1.0, per_image / 4)

    # Build one input per image, each shown for `per_image` seconds with
    # a slow zoom (Ken Burns), then concatenated with crossfades.
    filter_parts = []
    inputs = []
    for i, img in enumerate(image_paths):
        inputs += ["-loop", "1", "-t", str(per_image + fade_dur), "-i", img]
        zoompan = (
            f"[{i}:v]scale={width * 2}:{height * 2},"
            f"zoompan=z='min(zoom+0.0015,1.2)':d={int((per_image + fade_dur) * 25)}"
            f":s={width}x{height}:fps=25,setsar=1[v{i}]"
        )
        filter_parts.append(zoompan)

    # Chain crossfades between consecutive clips
    chain = "v0"
    offset = per_image
    for i in range(1, len(image_paths)):
        out_label = f"vx{i}"
        filter_parts.append(
            f"[{chain}][v{i}]xfade=transition=fade:duration={fade_dur}:"
            f"offset={offset:.2f}[{out_label}]"
        )
        chain = out_label
        offset += per_image

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", f"[{chain}]", "-map", f"{len(image_paths)}:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        out_path,
    ]
    subprocess.run(cmd, check=True)
    return out_path
