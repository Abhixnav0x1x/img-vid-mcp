# QUICKSTART (free, self-hosted)

Full setup: **[INSTALL.md](INSTALL.md)**. This page is the 2-minute version.

## 1. Install
```powershell
git clone https://github.com/<you>/imagemcp.git
cd imagemcp
pip install -r requirements.txt
copy .env.example .env   # macOS/Linux: cp .env.example .env
```

## 2. Run (stdio, for Claude Desktop / Cursor / OpenCode)
Point your client at:
```
command: python
args: ["<ABSOLUTE_PATH_TO>/imagemcp/server.py"]
```
Example configs (see `mcp.json.example` / `opencode.json.example`):
- Claude Desktop: `%APPDATA%\Claude\claude_desktop_config.json`
- Cursor: Settings > MCP > Add server
- OpenCode: copy `opencode.json.example` to `opencode.json`, fill in your path

## 3. Try it (in agent chat)
```
> search_images "hero coffee shop" max_results=6
> download_media <image url> dest_subfolder="hero"
  -> validate -> download -> optimise instantly -> optimised path + bytes_saved + <img> snippet
> search_videos "city timelapse" max_results=4
> download_video <video page url> dest_subfolder="videos" quality="720p"
  -> probe -> download direct .mp4 -> <video> snippet (no embed)
> download_all [<url1>, <url2>] dest_subfolder="gallery"
  -> same steps per URL, manifest_id for the full job
> search_images "mountain" auto_download=true dest_subfolder="mountains"
> status   # check imgopt_available:true, ytdlp_available:true
```
The agent never optimises — every path it receives is already optimised.

## 4. Lossless optimiser + video (both automatic)
Images: optimised instantly after every download — via the optional
`../imageoptimiser` companion project if present, otherwise a built-in
Pillow pass. No agent step, no opt-out.
Videos: `yt-dlp` + `ffmpeg` (both already in requirements).
Tune in `.env`: `IMAGEOPTIMISER_PATH`, `IMGOPT_ENABLED=1`, `YT_DEFAULT_QUALITY=720p`.

## 5. Optional stealth
```powershell
pip install "camoufox[geoip]"
python -m camoufox fetch
# .env: ENABLE_CAMOUFOX=1
```

## 6. Where files go
`MEDIA_ROOT/public/assets/<slug>/` (optimised in-place) + `credits.json` ledger + `.storage/manifests/<job>.json`.
Paste returned `snippet` straight into your site. Serve `/assets/...` from `MEDIA_ROOT`.
