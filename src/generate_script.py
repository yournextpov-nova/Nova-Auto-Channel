"""
Generates today's story script + a matching list of scene image prompts,
using Groq's free-tier API (OpenAI-compatible chat completions).

Get a free key at https://console.groq.com/keys
Set it as the GROQ_API_KEY environment variable / GitHub secret.
"""
import os
import json
import time
import random
import requests

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

THEME_SEEDS = [
    "a rainy day", "a birthday surprise", "a lost object", "a new friend",
    "a silly misunderstanding", "a small act of courage", "a game gone wrong",
    "a mysterious noise", "helping a neighbor", "a treasure hunt",
    "learning to share", "overcoming a fear", "a picnic", "a snow day",
    "a broken toy", "a garden project", "a talent show", "a camping trip",
    "a market day", "a costume party", "a science experiment",
    "a music lesson", "a boat trip", "a mountain hike", "a cooking mishap",
]


def _call_groq(prompt: str) -> str:
    last_error = None
    for attempt in range(5):
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 1.0,
            },
            timeout=120,
        )
        if resp.status_code == 429:
            wait = 15 * (attempt + 1)
            print(f"Rate limited, waiting {wait}s before retry...")
            time.sleep(wait)
            last_error = resp
            continue
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    last_error.raise_for_status()


def generate_story(config: dict, topic: str | None = None) -> dict:
    """Returns {"title", "description", "narration", "scenes", "tags"}"""
    chars = config["characters"]
    minutes = config["video"]["target_length_minutes"]
    audience = config["video"]["audience"]
    recent_titles = config["video"].get("recent_titles", [])

    theme_seed = random.choice(THEME_SEEDS)

    if topic:
        topic_line = f'Base today\'s story on this idea: "{topic}".'
    else:
        topic_line = (
            f"Invent a brand new, original story idea today loosely inspired by "
            f"the theme '{theme_seed}' - do not repeat common cliches, make it "
            f"fresh and fun."
        )

    avoid_line = ""
    if recent_titles:
        recent_list = "; ".join(recent_titles[-10:])
        avoid_line = (
            f"\nIMPORTANT: Do NOT repeat these recently used story titles or "
            f"their plots - write something genuinely different: {recent_list}\n"
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
{avoid_line}
Return ONLY valid JSON, no markdown fences, no commentary, in this exact
shape:
{{
  "title": "an SEO-friendly YouTube title, 60-100 characters, keyword-rich "
            "(include words like 'Kids Story', 'Bedtime Story', 'Animated "
            "Story', 'Nova' where natural), specific and curiosity-driving, "
            "not generic",
  "description": "a detailed 4-6 sentence YouTube description summarizing "
                  "the story and characters, written for SEO with natural "
                  "keyword use, followed on a new line by 8-12 relevant "
                  "hashtags starting with #",
  "narration": "the full story, written to be read aloud by a narrator, "
               "broken into natural paragraphs",
  "scenes": ["a visual description of scene 1", "scene 2", "... 5 to 6 scenes "
             "total, each describing one key visual moment of the story in "
             "1-2 sentences, in chronological order"],
  "tags": ["10 to 15 relevant YouTube SEO tags/keywords as short strings, "
           "no # symbols, mix of broad and specific terms"]
}}
"""
    raw = _call_groq(prompt)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("json", 1)[-1] if raw.lower().startswith("json") else raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        from json_repair import repair_json
        return json.loads(repair_json(raw))


if __name__ == "__main__":
    import yaml

    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)
    story = generate_story(cfg)
    print(json.dumps(story, indent=2))
