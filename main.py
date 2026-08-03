"""
The ONE script that runs the whole pipeline: idea -> script -> voice
-> images -> video -> upload.

Usage:
    python main.py                     # AI invents today's story
    python main.py --topic "Nova and the lost kite"   # give it a topic yourself
"""
import argparse
import os
import shutil
import yaml

from src.generate_script import generate_story
from src.generate_voice import generate_voiceover
from src.generate_images import generate_all_scene_images
from src.assemble_video import assemble_video
from src.upload_youtube import upload_video


def main(topic: str | None):
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    work_dir = "output"
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    print("1/5 Writing today's story...")
    if topic is None and config["video"]["topic_ideas"]:
        topic = config["video"]["topic_ideas"].pop(0)
        with open("config.yaml", "w") as f:
            yaml.safe_dump(config, f, sort_keys=False)
    story = generate_story(config, topic=topic)
    print("Title:", story["title"])

    config["video"].setdefault("used_titles", [])
    config["video"]["used_titles"].append(story["title"])
    config["video"]["used_titles"] = config["video"]["used_titles"][-30:]
    with open("config.yaml", "w") as f:
        yaml.safe_dump(config, f, sort_keys=False)

    print("2/5 Generating voiceover...")
    audio_path = generate_voiceover(story["narration"], os.path.join(work_dir, "voice.mp3"))

    print("3/5 Generating scene images (this can take a while)...")
    image_paths = generate_all_scene_images(story["scenes"], config, out_dir=os.path.join(work_dir, "scenes"))

    print("4/5 Assembling video...")
    video_path = assemble_video(image_paths, audio_path, os.path.join(work_dir, "final.mp4"))

    print("5/5 Uploading to YouTube...")
    upload_video(
        video_path=video_path,
        title=story["title"],
        description=story.get("description", ""),
        tags=story.get("tags", config["upload"]["default_tags"]),
        category_id=config["upload"]["category_id"],
        privacy_status=config["upload"]["privacy_status"],
    )

    print("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default=None)
    args = parser.parse_args()
    main(args.topic)
