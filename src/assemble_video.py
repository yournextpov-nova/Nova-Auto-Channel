"""
Assembles the final video from per-segment ANIMATED CLIPS (from Agnes,
via generate_clips.py) + per-segment audio, using ffmpeg.

Each clip is already trimmed to the exact duration of its narration
line, so this step just normalizes every clip to the same size/fps,
crossfades them together, and lays the stitched audio track on top.
No more zoompan - the clips already have their own motion.
"""
import subprocess
import os


def assemble_video(clip_paths: list[str], audio_paths: list[str],
                    durations: list[float], out_path: str,
                    width: int = 1920, height: int = 1080):
    assert len(clip_paths) == len(audio_paths) == len(durations)
    fade_dur = min(0.6, min(durations) / 4)

    filter_parts = []
    inputs = []
    for i, clip in enumerate(clip_paths):
        inputs += ["-i", clip]
        filter_parts.append(
            f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps=25,setsar=1[v{i}]"
        )

    # Video crossfade chain
    chain = "v0"
    offset = durations[0]
    for i in range(1, len(clip_paths)):
        out_label = f"vx{i}"
        filter_parts.append(
            f"[{chain}][v{i}]xfade=transition=fade:duration={fade_dur}:"
            f"offset={offset:.2f}[{out_label}]"
        )
        chain = out_label
        offset += durations[i]

    video_filter_complex = ";".join(filter_parts)

    # Concatenate all the audio clips into a single track, in order (unchanged).
    concat_list_path = os.path.join(os.path.dirname(out_path) or ".", "_audio_concat.txt")
    with open(concat_list_path, "w") as f:
        for a in audio_paths:
            f.write(f"file '{os.path.abspath(a)}'\n")
    concat_audio_path = os.path.join(os.path.dirname(out_path) or ".", "_full_audio.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_path, "-c", "copy", concat_audio_path,
    ], check=True)

    audio_input_index = len(clip_paths)
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
