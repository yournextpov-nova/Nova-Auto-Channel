"""
The ONE script that runs the whole pipeline: idea -> synced script ->
per-line voice -> matching ANIMATED clips -> video -> upload.

Usage:
    python main.py                     # AI invents today's story (long-form)
    python main.py --topic "Nova and the lost kite"   # give it a topic yourself
    python main.py --short             # generate a vertical YouTube Short instead
    python main.py --short --topic "..."               # short with your own topic
"""
import argparse
import os
import shutil
import yaml
from src.generate_script import generate_story
from src.generate_voice import generate_segment_voiceovers
from src.generate_clips import generate_all_scene_clips
from src.generate_thumbnail import generate_thumbnail
from src.assemble_video import assemble_video
from src.upload_youtube import upload_video


def main(topic: str | None, short: bool = False):
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    work_dir = "output"
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    print("1/5 Writing today's synced story...")
    # Shorts don't draw from the long-form topic_ideas queue - that queue is
    # meant for the daily long-form video, sharing it would drain it faster
    # than intended.
    if not short and topic is None and config["video"]["topic_ideas"]:
        topic = config["video"]["topic_ideas"].pop(0)
        with open("config.yaml", "w") as f:
            yaml.safe_dump(config, f, sort_keys=False)

    story = generate_story(config, topic=topic, short=short)
    print("Title:", story["title"])
    segments = story["segments"]
    print(f"{len(segments)} segments in this story")

    # Remember this title so tomorrow's story avoids repeating it (shared
    # between long-form and Shorts, which also avoids the two overlapping).
    recent = config["video"].get("recent_titles", [])
    recent.append(story["title"])
    config["video"]["recent_titles"] = recent[-15:]
    with open("config.yaml", "w") as f:
        yaml.safe_dump(config, f, sort_keys=False)

    print("2/5 Generating per-line voiceovers...")
    voice_results = generate_segment_voiceovers(segments, os.path.join(work_dir, "audio"))
    audio_paths = [r["audio_path"] for r in voice_results]
    durations = [r["duration"] for r in voice_results]

    print("3/5 Generating animated scene clips (this takes a while - Agnes is async)...")
    visuals = [seg["visual"] for seg in segments]
    clip_paths = generate_all_scene_clips(
        visuals, durations, config, out_dir=os.path.join(work_dir, "scenes"), portrait=short
    )

    print("4/5 Assembling synced video...")
    if short:
        video_path = assemble_video(clip_paths, audio_paths, durations, os.path.join(work_dir, "final.mp4"),
                                     width=1080, height=1920)
    else:
        video_path = assemble_video(clip_paths, audio_paths, durations, os.path.join(work_dir, "final.mp4"))

    thumbnail_path = None
    if not short:
        # Custom thumbnails aren't really shown in the Shorts feed the way
        # they are for long-form videos, so skip this step for Shorts.
        print("Generating thumbnail...")
        try:
            first_frame = os.path.join(work_dir, "scenes", "scene_00_frame.png")
            thumbnail_path = generate_thumbnail(
                source_frame_path=first_frame,
                thumb_text=story.get("thumbnail_text") or story["title"][:20],
                out_path=os.path.join(work_dir, "thumbnail.jpg"),
            )
        except Exception as e:
            # Don't let a thumbnail problem stop the whole video from uploading.
            print(f"Thumbnail generation failed, continuing without one: {e}")

    print("5/5 Uploading to YouTube...")
    ai_tags = story.get("tags") or []
    tags = list(dict.fromkeys(ai_tags + config["upload"]["default_tags"]))[:30]
    title = story["title"]
    if short and "#shorts" not in title.lower():
        title = title[:95] + " #Shorts"  # helps YouTube classify it correctly
    upload_video(
        video_path=video_path,
        title=title,
        description=story.get("description", ""),
        tags=tags,
        category_id=config["upload"]["category_id"],
        privacy_status=config["upload"]["privacy_status"],
        thumbnail_path=thumbnail_path,
    )
    print("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default=None)
    parser.add_argument("--short", action="store_true",
                         help="Generate a vertical YouTube Short (under 60s) instead of a long-form video.")
    args = parser.parse_args()
    main(args.topic, short=args.short)
