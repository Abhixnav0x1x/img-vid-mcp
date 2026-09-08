# CHANGELOG

## 1.3.0 — Public release
- Portablized for GitHub: no hardcoded paths (`opencode.json.example` /
  `mcp.json.example` use placeholders), `opencode.json` gitignored,
  MIT LICENSE, lean deps (dropped unused `beautifulsoup4`, dev-only `pytest`).
- Image optimiser companion project now optional — built-in Pillow fallback
  covers fresh clones; docs explain the optional stronger compression.
- New INSTALL.md paths use `git clone` + cross-platform notes.

## 1.2.0 — Optimisation fully automatic
- Optimisation is now unconditional: `download_media` / `download_all` /
  `search_images(auto_download)` always optimise instantly after download and
  only then return paths to the agent. No `optimize` flag, no opt-out.
- `optimize_image` kept as maintenance-only for older files; agent never calls it.
- Docs now spell out the automatic download pipeline steps.

## 1.1.0 — Fast video files, any site
- New `download_video` tool: YouTube/Vimeo/TikTok/X/Dailymotion/Twitch/Rumble... -> direct `.mp4`.
- Speed: single metadata pass (process_video_result), progressive-mp4-first (no re-encode),
  8 parallel fragments, early live/>3h rejects. Direct .mp4 URLs use plain HTTP.
- `download_media`/`download_all` auto-route video pages to files — embeds no longer needed.
- `status` reports `ytdlp_available` + `yt_default_quality`. yt-dlp now a core dep.
- Docs: README/TOOLS/QUICKSTART/SELF-HOST-PRO/COMPLIANCE updated.

## 1.0.0 — Free + self-hostable + auto lossless
- Removed all premium tiers/gates. Everything free: search, camoufox, bulk (cap 100).
- Auto lossless optimisation via local `../imageoptimiser` (pngquant / progressive JPG / WebP,
  metadata stripped) in `download_one` + `optimize_manifest` safety net.
- New `optimize_image` tool (re-optimise any file under MEDIA_ROOT in-place).
- `status` reports `imgopt_available`; snippets point at optimised files with `bytes_saved`.
- Docs updated: README/QUICKSTART/TOOLS/SELF-HOST-PRO.

## 0.2.0 — Premium Tier-2 (retired)
- Added `camoufox_fetch` (stealth, premium-gated), `download_all` bulk (20 free/100 pro), `auto_download` on `search_images`
- Optimizer: WebP + srcset snippets (premium), dimensions probe
- License guard + credits ledger + manifests
- Vision thumbnails (ImageContent, up to 3) on `search_images`
- Docs: README/QUICKSTART/TOOLS/SELF-HOST-PRO/COMPLIANCE

## 0.1.0 — Free core
- ddgs search_images/videos/web + download_media + sandbox caps
