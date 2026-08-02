# Nova Auto-Channel

Fully automated pipeline for your "Next POV" channel: every day it
invents a new Nova / cat / panda story, writes the script, generates
the voiceover and images, edits the video, and uploads it to YouTube
— with no manual work once it's set up.

**Cost: $0/month** at the free tiers used here (Gemini free tier,
Pollinations.ai free images, Edge TTS free voice, GitHub Actions free
scheduler, YouTube Data API free quota). Free tiers have limits — see
"Limits to know" below.

## One-time setup (about 20-30 minutes)

### 1. Get a free Gemini API key (writes the stories)
- Go to https://aistudio.google.com/apikey
- Click "Create API key" and copy it.

### 2. Set up YouTube upload access
- Go to https://console.cloud.google.com/ and create a new project.
- Search for "YouTube Data API v3" and click **Enable**.
- Go to "APIs & Services" -> "Credentials" -> "Create Credentials" ->
  "OAuth client ID" -> Application type **Desktop app**.
- Download the JSON file, rename it `client_secret.json`, and put it
  in this project's main folder (on your own computer, not GitHub).
- On your own computer (with Python installed), run:
  ```
  pip install -r requirements.txt
  python get_youtube_token.py
  ```
  A browser window opens — log into the Google account that owns
  your "Next POV" channel and approve access. The script will print
  three values in your terminal.

### 3. Put your project on GitHub
- Create a new **private** GitHub repository and push this folder to it.
  (Private is important — your secrets stay safe either way, but
  it keeps your code/config private too.)

### 4. Add your secrets to GitHub
In your repo: **Settings -> Secrets and variables -> Actions -> New
repository secret**. Add these four, using the values from steps 1 & 2:
- `GEMINI_API_KEY`
- `YT_CLIENT_ID`
- `YT_CLIENT_SECRET`
- `YT_REFRESH_TOKEN`

### 5. Customize your channel (optional)
Open `config.yaml` and edit the character descriptions, art style,
video length, or add specific story ideas to `topic_ideas`. Leave
`topic_ideas` empty to let it invent a new story every day by itself.

### That's it
The workflow in `.github/workflows/daily_upload.yml` runs automatically
every day at 14:00 UTC and uploads a new video with zero input from
you. You can also trigger it manually any time from your repo's
"Actions" tab -> "Daily YouTube Auto-Upload" -> "Run workflow".

## Running it yourself, once, before going fully automatic
It's worth testing locally first:
```
pip install -r requirements.txt
export GEMINI_API_KEY=your_key
export YT_CLIENT_ID=... 
export YT_CLIENT_SECRET=...
export YT_REFRESH_TOKEN=...
python main.py --topic "Nova and the lost kite"
```

## Limits to know (free tiers)
- **YouTube Data API**: default free quota allows a handful of uploads
  per day (each upload costs ~1600 of your 10,000 daily quota units) —
  one video/day is comfortably within this.
- **Gemini free tier**: generous but rate-limited; fine for 1 video/day.
- **Pollinations.ai**: free, no key, but can be slow/rate-limited at
  peak times — the script retries automatically.
- **Character consistency**: free image generation won't make Nova,
  the cat, and the panda pixel-identical in every video — only
  recognizably on-model (same colors/features/style). Paid
  character-reference tools fix this later if the channel grows.

## Upgrading later (once the channel earns something)
- Swap `generate_images.py` for a paid tool with character-reference
  support for tighter visual consistency.
- Swap the Edge TTS voice for a paid, more expressive voice (e.g.
  ElevenLabs).
- Add background music and on-screen captions to `assemble_video.py`.
