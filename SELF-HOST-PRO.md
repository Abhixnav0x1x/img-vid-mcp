# SELF-HOSTING (all free)

`.env`:
```
ENABLE_CAMOUFOX=0   # set 1 only if you ran python -m camoufox fetch
MAX_FILES=100
MAX_IMAGE_MB=15
MAX_VIDEO_MB=200
IMAGEOPTIMISER_PATH=../imageoptimiser
IMGOPT_ENABLED=1
IMGOPT_QUALITY=80
```

No license keys. No tiers. Everything runs locally.

## Stealth (Camoufox, optional)
```powershell
pip install "camoufox[geoip]"
python -m camoufox fetch
```
`camoufox_fetch` launches headless humanized Firefox, scrolls, extracts `<img>` srcs, saves `camoufox-preview.png` screenshot for agent vision. Use behind proxy via `HTTP_PROXY/HTTPS_PROXY`.

## Lossless optimiser
`optimizer.py` uses the optional `imageoptimiser` companion project from
`IMAGEOPTIMISER_PATH` (PNG via pngquant, JPG progressive + EXIF strip, WebP
method=6), with a built-in Pillow metadata-strip fallback when it's absent.
Runs automatically in `download_one`/`download_many`; re-runnable via the
`optimize_image` tool (skips if not smaller).

## Videos (fast, direct files)
`download_video` / auto-routing in `download_media` / `download_all` save video
pages as `.mp4` via yt-dlp — no embeds. Speed design: one metadata pass,
progressive-mp4-first (no re-encode), 8 parallel fragments, early live/>3h
rejects, `MAX_VIDEO_MB` cap. Direct `.mp4` URLs use plain HTTP (fastest).
If a site bot-blocks your IP: `YT_COOKIES_BROWSER=chrome` or `YT_COOKIES_FILE`.
Enforce per-run quota via `MAX_FILES` + `MAX_VIDEO_MB`.

## Hosting as remote MCP
Stdio is default (`mcp.run()`). For HTTP/SSE wrap with your gateway
(e.g. `fastmcp run server.py --transport sse --port 8000`).
Cache lives in `.storage/cache` (TTL 24h). Manifests in `.storage/manifests`.

## Hardening checklist
- Keep `MEDIA_ROOT` inside project (`public/assets`), serve `/assets`.
- Set `MAX_FILES` + disk alert; `download_all` dedupes by URL hash.
- Rotate UA/proxy if you see 202/403 from DDG; `backend="auto"` already falls back bing->duckduckgo.
- Pin deps: `ddgs`, `camoufox` break on upstream HTML changes — keep `CACHE_TTL_HOURS=24`.
