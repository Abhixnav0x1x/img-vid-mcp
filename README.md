# img-vid-mcp

A free, self-hosted MCP server that lets coding agents search the web for
images and videos, download them into a website project, and hand back
paste-ready HTML. No API keys, no accounts, no paid tiers.

Works with OpenCode, Claude Code, Cursor, Windsurf, or anything that speaks MCP.

## What it can do

* Search images, videos, and text through DuckDuckGo, Bing, and Google backends. No key needed. The agent sees thumbnail previews before it picks anything.
* Download a single file, a whole list, or an entire search result in one call. Files land in `public/assets/<topic>/`, sandboxed and size capped.
* Optimise every image losslessly the moment it finishes downloading, using the optional `imageoptimiser` companion project (pngquant, progressive JPEG, WebP, metadata stripped). There is a built-in Pillow fallback, so a fresh clone works with nothing extra. The agent never optimises anything itself. It only ever gets the finished file.
* Save video pages as direct `.mp4` files. YouTube, Vimeo, TikTok, X, Dailymotion, Twitch, Rumble, and more. One metadata pass, progressive stream preferred so there is usually no re-encode, fragments fetched in parallel. Your site serves a file instead of an iframe.
* Return `relative_path`, bytes saved, and an `<img>` or `<video>` snippet with every download, plus a `credits.json` attribution ledger and per-job manifests.

## Requirements

* Python 3.10 or newer (`python --version`), with pip.
* ffmpeg on PATH for video pages (`ffmpeg -version`). Windows: `choco install ffmpeg`. macOS: `brew install ffmpeg`.
* A coding agent. OpenCode (`npm install -g opencode-ai`) is tested, but any MCP client works.

## Install

Windows, one command:

```powershell
git clone https://github.com/Abhixnav0x1x/img-vid-mcp.git
cd img-vid-mcp
setup.cmd
```

`setup.cmd` checks Python and ffmpeg, installs dependencies, creates `.env`,
verifies the server, and wires the MCP into your global OpenCode config
(keeping a backup as `opencode.json.bak`). Then restart OpenCode if it is
already running. `setup.cmd --no-wire` skips the OpenCode step.

Manual install (any OS):

```powershell
pip install -r requirements.txt
copy .env.example .env
```

macOS and Linux use `cp .env.example .env` and `python3` where noted.

Optional extras:

```powershell
pip install "camoufox[geoip]"
python -m camoufox fetch
```

That enables the stealth browser fallback for JavaScript heavy or
Cloudflare protected pages. Set `ENABLE_CAMOUFOX=1` in `.env` after it.

For stronger image compression, clone the companion optimiser next to this
folder so the layout looks like this:

```
parent/
├── img-vid-mcp/
└── imageoptimiser/
```

The server finds it through `IMAGEOPTIMISER_PATH` (default
`../imageoptimiser`) and uses it on its own. Without it, the Pillow
fallback handles everything.

## Check it works

```powershell
python -c "import server, json; print(json.dumps(server.status(), indent=2))"
```

You want `"ddgs_available": true` and `"ytdlp_available": true`.
`"imgopt_available"` is true with the companion project, otherwise the
fallback covers it.

One full round trip (downloads a small test image, optimised automatically):

```powershell
python -c "import server, json; print(json.dumps(server.download_media('https://picsum.photos/seed/hello/640/400', dest_subfolder='hello'), indent=2))"
```

And the wiring:

```powershell
opencode mcp list
```

It should show `imagemcp connected`.

## Hooking up an agent

Copy `opencode.json.example` to `opencode.json` and put your real folder path
where `<ABSOLUTE_PATH_TO>` is. Run the agent from this folder and it picks the
file up. To make the server available in every project instead, copy the
`"imagemcp"` block into the global config (`%USERPROFILE%\.config\opencode\opencode.json`
on Windows, `~/.config/opencode/opencode.json` elsewhere). `mcp.json.example`
has the equivalent for Claude Code, Cursor, and Windsurf.

Prompts that work:

```
use the imagemcp tools to search for "hero coffee shop" images and download the best one into hero/
```

```
use imagemcp search_images with auto_download=true for "mountain lake", then show me the snippets
```

```
use imagemcp download_video to save this as a file: <youtube/vimeo/tiktok url>
```

## How a download flows

1. The agent searches (`search_images`, `search_videos`, or `search_web`), looks at the thumbnails, and picks winners.
2. It calls `download_media`, `download_video`, or `download_all` with the URLs.
3. The server validates each URL, downloads it sandboxed under `MEDIA_ROOT` (`./public/assets`), dedupes repeats, and enforces caps (15 MB images, 200 MB video).
4. Images get losslessly optimised in place right away. Video pages get saved as `.mp4`.
5. The agent gets back `local_path`, `relative_path`, bytes saved, and a snippet it can paste straight into the site.

## Tools

11 tools, all free.

| Tool | Input | Result |
|---|---|---|
| `status` | nothing | provider health (`ddgs`, `camoufox`, `imgopt`, `ytdlp`), caps, paths |
| `search_images` | query, count (max 30), license/size/color/layout filters, `auto_download` | metadata plus up to 3 vision thumbnails; with `auto_download`, also a `manifest_id` |
| `search_videos` | query, count (max 20) | title, page URL, duration, publisher. Every hit can go to `download_video` |
| `search_web` | query, count, backend | title, link, snippet from Google/Bing/DuckDuckGo |
| `camoufox_fetch` | URL or keywords, scroll pages | stealth fetch for JS and Cloudflare pages, needs `ENABLE_CAMOUFOX=1` |
| `download_media` | URL, subfolder, optional filename | optimised image or `.mp4` plus snippet and an `optimization` record |
| `download_video` | URL, subfolder, quality `360p/480p/720p/1080p/best` (default `720p`) | direct `.mp4` plus title, duration, snippet |
| `download_all` | list of URLs, subfolder | bulk run up to 100 files, returns `manifest_id` with per-file status |
| `optimize_image` | path under `MEDIA_ROOT`, quality | maintenance only. Downloads arrive optimised, so this is just for older files |
| `get_manifest` | job id | full per-file record of a bulk run, optimisation stats included |
| `get_credits` | limit | attribution ledger: source page for everything downloaded |

Default image filter is `ShareCommercially`. Use `Public` for commercial hero assets.

## Configuration

Everything lives in `.env`. See `.env.example` for the full list.

```ini
MEDIA_ROOT=./public/assets
STORAGE_DIR=./.storage
IMAGEOPTIMISER_PATH=../imageoptimiser
IMGOPT_ENABLED=1
IMGOPT_QUALITY=80
YT_DEFAULT_QUALITY=720p
ENABLE_CAMOUFOX=0
MAX_IMAGE_MB=15
MAX_VIDEO_MB=200
MAX_FILES=100
```

If a video site throws a bot check at your IP, set `YT_COOKIES_BROWSER=chrome`
or point `YT_COOKIES_FILE` at an exported cookies file and retry.

## Layout

```
img-vid-mcp/
├── setup.cmd            # one-command installer (Windows)
├── server.py            # the MCP server, all 11 tools
├── config.py            # settings loaded from .env
├── downloader.py        # sandboxed HTTP downloads, bulk runs, manifests
├── video.py             # fast video page downloads through yt-dlp
├── optimizer.py         # lossless bridge into imageoptimiser, Pillow fallback
├── license_guard.py     # license filters, domain blocklist, credits ledger
├── providers/
│   ├── ddg_provider.py  # free search with a 24 hour cache
│   └── camoufox_provider.py  # optional stealth browser
├── public/assets/       # downloaded site files and credits.json
├── .storage/            # search cache and job manifests
├── opencode.json.example
└── mcp.json.example
```

## Staying out of trouble

Scraping public result URLs is low risk. Reusing creative work is a separate
question, so the server bakes in a few guardrails: a commercial-use license
filter by default, no hotlinking (always download), blocked private and
login-walled hosts, and a source log for everything fetched. Only download
videos you hold rights to: your own uploads, Creative Commons, or explicit
permission. YouTube's terms restrict downloading, and that call is yours and
your agent's. This is practical guidance, not legal advice.

## Troubleshooting

* MCP missing from the agent: check project vs global config location, then restart the agent. `opencode mcp list` should show it connected.
* `ytdlp_available: false`: `pip install yt-dlp` and install ffmpeg, then re-check status.
* `imgopt_available: false`: fine on its own (Pillow fallback). Or check that `IMAGEOPTIMISER_PATH` points at the folder holding `optimiser/`.
* Bot check on a video site: set `YT_COOKIES_BROWSER` or `YT_COOKIES_FILE` in `.env`.
* Empty search results: usually rate limiting. Wait a minute. Backends fall back automatically and results cache for 24 hours under `.storage/cache`.
* Files in the wrong place: `MEDIA_ROOT` resolves relative to `cwd` in the MCP config. Keep `cwd` on this folder.
* `python` not found on Windows: use the full path in the command array, e.g. `C:\Python313\python.exe`, or fix PATH.

## History

* 1.4.0: `setup.cmd` one-command installer.
* 1.3.0: public release. Portable paths, MIT license, lean deps, optional optimiser.
* 1.2.0: optimisation made unconditional. No flags, no opt-out.
* 1.1.0: fast video files from any supported site.
* 1.0.0: free self-hostable core with auto lossless images.

## License

MIT, see LICENSE.
