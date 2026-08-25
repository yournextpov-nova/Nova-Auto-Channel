"""
Generates today's story as a list of synced segments - each segment
pairs one line of narration with the matching image description, so
the visual on screen matches exactly what's being spoken at that
moment.

Uses Groq's free-tier API (OpenAI-compatible chat completions).
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
GROQ_MODEL = "openai/gpt-oss-120b"

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
                # openai/gpt-oss-120b's free tier caps at 8000 tokens PER
                # MINUTE total (prompt + completion combined) - not just
                # completion. The prompt has grown (style guidance, story
                # arc instructions, thumbnail_text field) to roughly
                # 1300-1600 tokens now, so this needs more headroom below
                # 8000 than before.
                "max_tokens": 6000,
                "reasoning_effort": "low",
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
        content = data["choices"][0]["message"]["content"]
        if not content or not content.strip():
            # Reasoning likely ate the whole budget - retry is unlikely to
            # help unless we back off max_tokens usage elsewhere, but a
            # retry occasionally succeeds due to response variance.
            print(f"Attempt {attempt + 1}: got empty content, retrying...")
            last_error = resp
            time.sleep(5)
            continue
        return content
    raise RuntimeError(f"Groq returned empty content after retries. Last response: {last_error.text[:500] if last_error is not None else 'none'}")


def generate_story(config: dict, topic: str | None = None) -> dict:
    """Returns {"title", "description", "tags", "segments": [{"narration","visual"}]}"""
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
You write scripts for a kids' animated YouTube channel. You are a warm,
skilled children's storyteller, not a generic AI narrator - your writing
should sound like a real person reading a beloved bedtime story aloud,
never stiff, robotic, or like a list of stage directions.

WRITING STYLE:
- Warm, natural, conversational language - contractions, varied sentence
  length, real sensory/emotional detail (not flat statements of fact).
- Each character's dialogue should sound like THEM: Nova is excited and
  curious, the cat is playful/mischievous, the panda is slow and thoughtful.
- No generic AI-story cliches ("little did they know", identical openings).
- Segments should flow into each other like one continuous read-aloud
  story, not disconnected captions - use natural connectors ("just then...",
  "but before she could answer...").

Main characters (always stay true to these descriptions):
- Nova: {chars['nova']}
- The cat: {chars['cat']}
- The panda: {chars['panda']}

Audience: {audience}
Target spoken length: This MUST total approximately {minutes * 130} words of
narration across all segments combined (this is a hard requirement, not a
suggestion - the previous story was too short at roughly half this length).
To hit this, write 20 to 30 segments, and make sure each segment's
narration is a FULL 1-2 sentences (roughly 25-40 words each) rather than
one short sentence - count your words as you go and keep writing segments
until the total narration across the whole story reaches {minutes * 130}
words.
{topic_line}
{avoid_line}
Write the story as a sequence of 20 to 30 SEGMENTS, following a clear
narrative arc: (1) establish the everyday setting and characters, (2) introduce
a specific problem, question, or goal early on, (3) build through a few
concrete attempts/events tied to that problem, (4) resolve it clearly by
the end with the characters learning or achieving something specific. Avoid
vague scene-hopping - every segment should clearly connect to the one before
it and move the SAME problem/goal forward, so a viewer always knows what is
happening and why.

Each segment is one short beat of the story - ONE OR TWO sentences of
narration or dialogue, paired with a description of exactly what should be
drawn on screen while that narration is spoken. Keep segments short and
granular so the image on screen always matches the specific action being
narrated at that exact moment. The visual must match the narration action
precisely (e.g. if the narration says "Nova ran from the tornado", the
visual for that same segment must show Nova running from a tornado - not an
earlier or later moment).

Each segment also needs a "speaker" field: use "narrator" for scene-setting/
descriptive lines, or the character's name ("nova", "cat", "panda") when
that segment is a line of DIALOGUE spoken directly by that character (in
quotes, first person). Mix narration and character dialogue naturally,
the way a storybook read-aloud does - this makes the story easier to follow
and more engaging than a single flat narrating voice throughout.

Return ONLY valid JSON, no markdown fences, no commentary, in this exact
shape:
{{
  "title": "an SEO-friendly YouTube title, 60-100 characters, keyword-rich "
            "(include words like 'Kids Story', 'Bedtime Story', 'Animated "
            "Story', 'Nova' where natural), specific and curiosity-driving, "
            "not generic",
  "thumbnail_text": "a SHORT, punchy phrase, 2-5 words max, that would look "
                     "great as big bold text on a YouTube thumbnail - "
                     "curiosity-driving, NOT the same as the title (too long "
                     "for a thumbnail), e.g. 'THE LOST STAR' or 'A BIG "
                     "SURPRISE!'",
  "description": "a detailed 4-6 sentence YouTube description summarizing "
                  "the story and characters, written for SEO with natural "
                  "keyword use, followed on a new line by 8-12 relevant "
                  "hashtags starting with #",
  "tags": ["15 to 20 relevant YouTube SEO tags/keywords as short strings, "
           "no # symbols, mix of broad and specific terms"],
  "segments": [
    {{
      "speaker": "narrator, or the exact character name (nova/cat/panda) if this line is that character's own spoken dialogue",
      "narration": "one or two sentences of the story, spoken aloud here - dialogue in quotes if speaker is a character",
      "visual": "exactly what the image should show during this narration - "
                "specific action, pose, and setting matching this exact line"
    }}
  ]
}}
"""
    raw = _call_groq(prompt)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("json", 1)[-1] if raw.lower().startswith("json") else raw
    try:
        story = json.loads(raw)
    except json.JSONDecodeError:
        from json_repair import repair_json
        story = json.loads(repair_json(raw))

    total_words = sum(len(seg.get("narration", "").split()) for seg in story.get("segments", []))
    target_words = minutes * 130
    print(f"Story length check: {total_words} words (target ~{target_words})")
    if total_words < target_words * 0.6:
        print(f"WARNING: story is well under the {minutes}-minute target - "
              f"final video will likely be much shorter than expected.")

    return story


if __name__ == "__main__":
    import yaml

    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)
    story = generate_story(cfg)
    print(json.dumps(story, indent=2))
