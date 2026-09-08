# INSTALL — imagemcp

Full setup from zero to a working MCP in any coding agent. ~10 minutes.

## 0. Clone

```powershell
git clone https://github.com/<you>/imagemcp.git
cd imagemcp
```

## 1. Prerequisites

| Need | Check | Install if missing |
|---|---|---|
| Python 3.10+ | `python --version` | https://www.python.org/downloads/ (tick **Add to PATH**). macOS/Linux can use `python3` |
| pip | `pip --version` | ships with Python |
| ffmpeg (for video pages) | `ffmpeg -version` | Windows: `choco install ffmpeg` · macOS: `brew install ffmpeg` · or https://ffmpeg.org/download.html |
| A coding agent | `opencode --version` | `npm install -g opencode-ai` (or Claude Code / Cursor / Windsurf — any MCP client works) |

No API keys. No accounts. No paid tiers.

## 2. Install dependencies

```powershell
pip install -r requirements.txt
```

This installs: `fastmcp`, `mcp`, `httpx`, `python-dotenv`,
`pillow`, `ddgs` (free search), `yt-dlp` (fast video files).

Optional stealth browser (only if you need JS-heavy / Cloudflare sites):

```powershell
pip install "camoufox[geoip]"
python -m camoufox fetch
```

### Optional: better image compression

Out of the box, images are optimised with a built-in Pillow pass
(metadata strip + re-encode). For stronger lossless compression
(pngquant / progressive JPEG tuning), clone the companion project next
to this folder so the layout looks like:

```
parent/
├── imagemcp/
└── imageoptimiser/
```

The server auto-detects it via `IMAGEOPTIMISER_PATH` (default
`../imageoptimiser`) and uses it automatically — check
`status` → `"imgopt_available": true`. Without it, everything still
works on the Pillow fallback.

## 3. Configure

```powershell
copy .env.example .env
```

macOS/Linux: `cp .env.example .env`.

Open `.env` and check the things that matter:

```ini
MEDIA_ROOT=./public/assets          # where website files land
IMGOPT_ENABLED=1                    # lossless images, always on
IMAGEOPTIMISER_PATH=../imageoptimiser
YT_DEFAULT_QUALITY=720p             # 360p|480p|720p|1080p|best
ENABLE_CAMOUFOX=0                   # set 1 only if you did the optional step
```

Full reference for every variable is in `.env.example`.

## 4. Smoke test (before wiring anything)

```powershell
python -c "import server, json; print(json.dumps(server.status(), indent=2))"
```

You must see `"ddgs_available": true` and `"ytdlp_available": true`.
(`imgopt_available` is true with the companion project, otherwise the
Pillow fallback handles optimisation.) If `ytdlp_available` is false,
install ffmpeg / `pip install yt-dlp` and re-run.

Quick end-to-end check (downloads one small image, optimised automatically):

```powershell
python -c "import server, json; print(json.dumps(server.download_media('https://picsum.photos/seed/hello/640/400', dest_subfolder='hello'), indent=2))"
```

## 5. Wire into your agent

Copy `opencode.json.example` to `opencode.json` and replace
`<ABSOLUTE_PATH_TO>` with the folder you cloned into
(or `mcp.json.example` for Claude Code / Cursor / Windsurf):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "imagemcp": {
      "type": "local",
      "command": ["python", "<ABSOLUTE_PATH_TO>/imagemcp/server.py"],
      "cwd": "<ABSOLUTE_PATH_TO>/imagemcp",
      "enabled": true,
      "timeout": 30000,
      "environment": {
        "MEDIA_ROOT": "./public/assets",
        "STORAGE_DIR": "./.storage",
        "IMAGEOPTIMISER_PATH": "../imageoptimiser",
        "IMGOPT_ENABLED": "1",
        "IMGOPT_QUALITY": "80",
        "ENABLE_CAMOUFOX": "0",
        "MAX_FILES": "100"
      }
    }
  }
}
```

- Project-local `opencode.json`: works when you run the agent from this folder.
- Global (`%USERPROFILE%\.config\opencode\opencode.json` on Windows,
  `~/.config/opencode/opencode.json` elsewhere): works in every project.
- If the agent was already running, restart it.

Verify the wiring:

```powershell
opencode mcp list
```

You must see `✓ imagemcp connected`.

## 6. Ask an agent to use it

```
use the imagemcp tools to search for "hero coffee shop" images and download the best one into hero/
```

```
use imagemcp search_images with auto_download=true for "mountain lake", then show me the snippets
```

```
use imagemcp download_video to save this as a file: <youtube/vimeo/tiktok url>
```

The agent receives optimised file paths + paste-ready `<img>` / `<video>` snippets.

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `opencode mcp list` doesn't show imagemcp | check the config file location (project vs global); restart the agent after editing config |
| `ytdlp_available: false` | `pip install yt-dlp` + install ffmpeg, re-run status |
| `imgopt_available: false` | fine without the companion project (Pillow fallback); or check `IMAGEOPTIMISER_PATH` points at the folder containing `optimiser/` |
| Video error "bot-check / Sign in to confirm" | set `YT_COOKIES_BROWSER=chrome` or `YT_COOKIES_FILE=/path/cookies.txt` in `.env` |
| Search returns 403 / empty | wait a minute (rate limit), it falls back across backends automatically; results cache 24h in `.storage/cache` |
| `ffmpeg not found` on video pages | install ffmpeg; direct `.mp4` URLs and progressive streams still work without it |
| Files land in the wrong place | `MEDIA_ROOT` is relative to `cwd` in the MCP config — keep `cwd` pointed at this folder |
| `python` not found (Windows) | use the full path, e.g. `"command": ["C:\\Python313\\python.exe", ...]`, or ensure Python is on PATH |

More detail: `QUICKSTART.md` (agent prompts), `TOOLS.md` (every tool + schema),
`SELF-HOST-PRO.md` (hosting/hardening), `COMPLIANCE.md` (license rules).
