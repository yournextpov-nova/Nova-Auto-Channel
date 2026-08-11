"""
Assembles the final video from per-segment images + per-segment audio
clips using ffmpeg. Each image is shown for EXACTLY the duration of
its own narration line, so the visual always matches what's being
said - no more generic even-split slideshow timing.
"""
import subprocess
import os


def assemble_video(image_paths: list[str], audio_paths: list[str],
                    durations: list[float], out_path: str,
                    width: int = 1920, height: int = 1080):
    assert len(image_paths) == len(audio_paths) == len(durations)

    fade_dur = min(0.6, min(durations) / 4)

    filter_parts = []
    inputs = []
    for i, img in enumerate(image_paths):
        inputs += ["-loop", "1", "-t", str(durations[i] + fade_dur), "-i", img]
        zoompan = (
            f"[{i}:v]scale={width * 2}:{height * 2},"
            f"zoompan=z='min(zoom+0.0015,1.2)':d={int((durations[i] + fade_dur) * 25)}"
            f":s={width}x{height}:fps=25,setsar=1[v{i}]"
        )
        filter_parts.append(zoompan)

    # Video crossfade chain
    chain = "v0"
    offset = durations[0]
    for i in range(1, len(image_paths)):
        out_label = f"vx{i}"
        filter_parts.append(
            f"[{chain}][v{i}]xfade=transition=fade:duration={fade_dur}:"
            f"offset={offset:.2f}[{out_label}]"
        )
        chain = out_label
        offset += durations[i]

    video_filter_complex = ";".join(filter_parts)

    # Concatenate all the audio clips into a single track, in order.
    concat_list_path = os.path.join(os.path.dirname(out_path) or ".", "_audio_concat.txt")
    with open(concat_list_path, "w") as f:
        for a in audio_paths:
            f.write(f"file '{os.path.abspath(a)}'\n")
    concat_audio_path = os.path.join(os.path.dirname(out_path) or ".", "_full_audio.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_path, "-c", "copy", concat_audio_path,
    ], check=True)

    audio_input_index = len(image_paths)
    cmd = [
        "ffmpeg", "-y", *inputs,
        "-i", concat_audio_path,
        "-filter_complex", video_filter_complex,
        "-map", f"[{chain}]", "-map", f"{audio_input_index}:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        out_path,
    ]
    subprocess.run(cmd, check=True)
    return out_path
