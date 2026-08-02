"""
Generates today's story script + a matching list of scene image prompts,
using Google Gemini's free-tier API.

Get a free key at https://aistudio.google.com/apikey
Set it as the GEMINI_API_KEY environment variable / GitHub secret.
"""
import os
import json
import requests

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY
)


def _call_gemini(prompt: str) -> str:
    resp = requests.post(
        GEMINI_URL,
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def generate_story(config: dict, topic: str | None = None) -> dict:
    """Returns {"title": str, "narration": str, "scenes": [str, ...]}"""
    chars = config["characters"]
    minutes = config["video"]["target_length_minutes"]
    audience = config["video"]["audience"]

    topic_line = (
        f'Base today\'s story on this idea: "{topic}".'
        if topic
        else "Invent a brand new, original story idea today - do not repeat "
             "common cliches, make it fresh and fun."
    )

    prompt = f"""
You write scripts for a kids' animated YouTube channel.

Main characters (always stay true to these descriptions):
- Nova: {chars['nova']}
- The cat: {chars['cat']}
- The panda: {chars['panda']}

Audience: {audience}
Target spoken length: about {minutes} minutes (roughly {minutes * 130} words).
{topic_line}

Return ONLY valid JSON, no markdown fences, no commentary, in this exact
shape:
{{
  "title": "a short catchy YouTube title, under 70 characters",
  "description": "a 2-3 sentence YouTube video description",
  "narration": "the full story, written to be read aloud by a narrator, "
               "broken into natural paragraphs",
  "scenes": ["a visual description of scene 1", "scene 2", "... 8 to 14 scenes "
             "total, each describing one key visual moment of the story in "
             "1-2 sentences, in chronological order"]
}}
"""
    raw = _call_gemini(prompt)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("json", 1)[-1] if raw.lower().startswith("json") else raw
    return json.loads(raw)


if __name__ == "__main__":
    import yaml

    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)
    story = generate_story(cfg)
    print(json.dumps(story, indent=2))
