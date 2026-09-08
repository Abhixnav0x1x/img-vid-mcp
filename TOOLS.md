# TOOLS reference (all free, self-hosted)

## status() -> dict
`{tier:'free', self_hostable, ddgs_available, camoufox_available, imgopt_available, imgopt_path, ytdlp_available, yt_default_quality, media_root, max_files, caps_mb}`

## search_images(query, max_results=6, license_image, size, color, layout, auto_download=false, dest_subfolder)
- `license_image`: `ShareCommercially` (default) | `ModifyCommercially` | `Public` | `Share` | `Modify` | `any`
- `size`: `Small|Medium|Large|Wallpaper`, `color`: `Red|Blue|...|Monochrome`, `layout`: `Square|Tall|Wide`
- Returns `{query, count, license_filter, results[]}` + up to 3 vision `Image` blocks so agent SEES picks.
- `results[]`: `{title, image(direct), thumbnail, url(source page), width, height, source}`
- `auto_download=true`: downloads + **lossless-optimises** all hits (cap 100), returns `manifest_id + downloaded`.

## search_videos(query, max_results=4)
Returns `{title, content(video page), description, duration, publisher}`.
Pass any result URL to `download_video` for a direct `.mp4` file — no embeds needed.

## search_web(query, max_results=5, backend="auto")
`backend`: `auto|google|bing|duckduckgo|brave`. Returns `{title, href, body}`.

## camoufox_fetch(query_or_url, scroll_pages=2, screenshot=true)
Stealth Firefox. URL or keywords (keywords -> Google Images `tbs=il:cl`). Returns `{images[], screenshot}`.
Requires `ENABLE_CAMOUFOX=1` + `python -m camoufox fetch`. Free.

## download_media(source_url, dest_subfolder, filename?)
Steps: validate -> sandbox to `MEDIA_ROOT` -> download (cap 15MB img / 200MB vid, dedupe)
-> **instantly lossless-optimise in-place** -> return.
Images: optimisation is automatic and unconditional — the agent never optimises.
Video pages (YouTube, Vimeo, ...) auto-save as direct `.mp4`.
Returns `{ok, local_path, relative_path, bytes, bytes_before, bytes_saved, width, height, snippet, optimization{method,percent}}`.
Snippet points at the optimised/filed file: `<img src="/assets/<rel>" ...>` or `<video src="/assets/<rel>" controls>`.

## download_video(source_url, dest_subfolder, quality="720p")
Video page -> direct `.mp4` file. Sites: YouTube, Vimeo, TikTok, X/Twitter, Dailymotion, Twitch, Rumble, Odysee, Bitchute (+ any yt-dlp site).
Fast: one metadata pass, progressive mp4 preferred (no re-encode), 8 parallel fragments.
`quality`: `360p|480p|720p|1080p|best` (height cap; default 720p keeps files small).
Direct `.mp4` URLs skip yt-dlp and use plain HTTP (fastest).
Returns `{ok, local_path, relative_path, bytes, title, video_id, duration, quality, snippet:<video...>}`.
Only download videos you have rights to (own / CC / licensed) — see COMPLIANCE.md.
If a site bot-blocks your IP: set `YT_COOKIES_BROWSER=chrome` or `YT_COOKIES_FILE=...` in `.env`.

## download_all(urls[], dest_subfolder)
Bulk "download everything the agent says". Cap 100, 4 workers.
Steps per URL: same as `download_media` — images optimised instantly, video pages saved as `.mp4`.
No `optimize` flag: optimisation always runs.
Returns `{job_id/manifest_id, requested, downloaded, failed, results[50]}`. Full via `get_manifest`.

## optimize_image(relative_path, quality=80)
Maintenance only — downloads are already optimised, the agent never calls this after a download.
Re-runs lossless optimisation on an older file under `MEDIA_ROOT` in-place.

## get_manifest(job_id) / get_credits(limit=50)
Manifest JSON (includes per-file `optimization`) + attribution ledger (`public/assets/credits.json`).
