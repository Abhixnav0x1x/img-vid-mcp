# imagemcp — free self-hostable media MCP for coding agents

Give any coding agent (OpenCode, Claude Code, Cursor, Windsurf) the ability to
**search the web for images and videos, download them into your website, and get
back paste-ready HTML** — with images losslessly optimised and videos saved as
real files. No API keys, no accounts, no paid tiers, no embeds required.

## What it does

- **Search the web** — images, videos, and text via DuckDuckGo / Bing / Google
  backends (`ddgs`, no key). The agent *sees* up to 3 thumbnails per image search.
- **Download everything the agent picks** — single file, bulk list, or
  auto-download a whole search in one call. Files land in
  `public/assets/<topic>/`, sandboxed and size-capped.
- **Lossless images, automatically** — every image is optimised instantly after
  download via your local `../imageoptimiser` (pngquant / progressive JPEG /
  WebP, metadata stripped). The agent never optimises; it only ever receives
  the already-optimised file. No flag, no extra step, no opt-out.
- **Real video files, fast** — YouTube, Vimeo, TikTok, X, Dailymotion, Twitch,
  Rumble and more save as direct `.mp4` (one metadata pass, progressive-first
  so usually no re-encode, 8 parallel fragments). Your site serves a file, not
  an iframe.
- **Website-ready output** — every download returns `relative_path`,
  `bytes_saved`, and a `<img>` / `<video>` snippet, plus a `credits.json`
  attribution ledger and per-job manifests.

## Quick start

```powershell
git clone https://github.com/<you>/imagemcp.git
cd imagemcp
pip install -r requirements.txt
copy .env.example .env   # macOS/Linux: cp .env.example .env
python -c "import server, json; print(json.dumps(server.status(), indent=2))"
opencode mcp list   # must show: ✓ imagemcp connected
```

Full walkthrough: **[INSTALL.md](INSTALL.md)**.

Then prompt an agent (from this folder):

```
use the imagemcp tools to search for "hero coffee shop" images and download the best one into hero/
```

## How a download flows (all automatic)

1. Agent calls `search_images` / `search_videos` / `search_web`, sees thumbnails, picks winners.
2. Agent calls `download_media(url)` / `download_video(url)` / `download_all([urls])`.
3. Server validates, downloads sandboxed to `MEDIA_ROOT` (`./public/assets`), dedupes, enforces caps (15MB image / 200MB video).
4. Images are **losslessly optimised in-place instantly**; video pages are saved as `.mp4`.
5. Agent gets `local_path` + `relative_path` + `bytes_saved` + snippet + manifest id.

## Tools (11)

| Tool | What the agent gets |
|---|---|
| `status` | provider health (`ddgs` / `camoufox` / `imgopt` / `ytdlp`), caps, paths |
| `search_images` | metadata + 3 vision thumbnails; `auto_download=true` fetches everything |
| `search_videos` | title, page URL, duration, publisher — every hit downloadable |
| `search_web` | text results across Google/Bing/DuckDuckGo |
| `camoufox_fetch` | stealth fetch for JS/Cloudflare pages (needs `ENABLE_CAMOUFOX=1`) |
| `download_media` | one URL → optimised image or `.mp4` + snippet |
| `download_video` | video page → `.mp4` (`360p`–`1080p`/`best`, default `720p`) |
| `download_all` | bulk list → files + `manifest_id` (cap 100) |
| `optimize_image` | maintenance re-optimise of older files (never needed after downloads) |
| `get_manifest` | full per-file job record incl. optimisation stats |
| `get_credits` | attribution ledger (source pages for everything downloaded) |

Schemas and examples: **[TOOLS.md](TOOLS.md)**.

## Project layout

```
imagemcp/
├── server.py            # MCP server — all 11 tools
├── config.py            # .env-driven settings (all free, no keys)
├── downloader.py        # sandboxed HTTP downloads + bulk + manifests
├── video.py             # fast yt-dlp path (progressive-first, parallel fragments)
├── optimizer.py         # lossless bridge into ../imageoptimiser (+ Pillow fallback)
├── license_guard.py     # CC filters, domain blocklist, credits ledger
├── providers/
│   ├── ddg_provider.py  # free ddgs search + 24h cache
│   └── camoufox_provider.py  # optional stealth browser
├── public/assets/       # downloaded website files (+ credits.json)
├── .storage/            # search cache + job manifests
├── opencode.json        # ready-made OpenCode wiring
├── INSTALL.md / TOOLS.md / QUICKSTART.md / SELF-HOST-PRO.md / COMPLIANCE.md / CHANGELOG.md
```

Needs ffmpeg on PATH for video pages, and Python 3.10+.

Image optimisation works out of the box (built-in Pillow pass). For
stronger lossless compression, clone the optional companion project next
to this folder (`../imageoptimiser`) — the server detects and uses it
automatically.

## Configuration

Everything lives in `.env` (see `.env.example`):

```ini
MEDIA_ROOT=./public/assets
IMAGEOPTIMISER_PATH=../imageoptimiser
IMGOPT_ENABLED=1
YT_DEFAULT_QUALITY=720p
# YT_COOKIES_BROWSER=chrome      # only if a site bot-blocks your IP
# ENABLE_CAMOUFOX=1             # only with `python -m camoufox fetch` done
```

## Rules that keep you safe

- Default image filter is `ShareCommercially`; use `Public` for commercial hero assets.
- Never hotlink — always download; sources are logged to `credits.json`.
- Only download videos you hold rights to (own / CC / licensed). YouTube's ToS
  restricts downloading — that decision is yours and your agent's.
- Details: **[COMPLIANCE.md](COMPLIANCE.md)**. Informational, not legal advice.

## Docs

- **[INSTALL.md](INSTALL.md)** — setup from zero, wiring, troubleshooting
- **[QUICKSTART.md](QUICKSTART.md)** — copy-paste agent prompts
- **[TOOLS.md](TOOLS.md)** — every tool, parameters, return shapes
- **[SELF-HOST-PRO.md](SELF-HOST-PRO.md)** — remote hosting, quotas, hardening
- **[COMPLIANCE.md](COMPLIANCE.md)** — scraping vs using, license rules
- **[CHANGELOG.md](CHANGELOG.md)** — version history (current: v1.3.0)

## License

MIT — see [LICENSE](LICENSE). If you build on it, a star is appreciated.
