"""
Assembles the final video from per-segment ANIMATED CLIPS (from Agnes,
via generate_clips.py) + per-segment audio, using ffmpeg.

Each clip is already trimmed to the exact duration of its narration
line, so this step normalizes every clip to the same size/fps and
concatenates them with a hard cut (no crossfade dissolve) - clean
cuts are the natural choice now that clips have real motion, and this
also guarantees the video's total length exactly matches the audio's
total length with no drift, since nothing overlaps or shrinks the
timeline.
"""
import subprocess
import os


def assemble_video(clip_paths: list[str], audio_paths: list[str],
                    durations: list[float], out_path: str,
                    width: int = 1920, height: int = 1080):
    assert len(clip_paths) == len(audio_paths) == len(durations)

    filter_parts = []
    inputs = []
    for i, clip in enumerate(clip_paths):
        inputs += ["-i", clip]
        filter_parts.append(
            f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps=25,setsar=1[v{i}]"
        )

    concat_inputs = "".join(f"[v{i}]" for i in range(len(clip_paths)))
    filter_parts.append(f"{concat_inputs}concat=n={len(clip_paths)}:v=1:a=0[outv]")

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
        "-map", "[outv]", "-map", f"{audio_input_index}:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        out_path,
    ]
    subprocess.run(cmd, check=True)

    # Sanity check so a mismatch shows up immediately in the logs, not
    # discovered later after upload like last time.
    expected = sum(durations)
    actual = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", out_path,
    ]).strip())
    print(f"Assembled video: expected ~{expected:.1f}s, actual {actual:.1f}s")
    if abs(actual - expected) > 5:
        print(f"WARNING: final video duration is off by more than 5s from expected!")

    return out_path
