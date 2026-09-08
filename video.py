"""Fast video downloads via yt-dlp - direct .mp4 files, no embeds.

Speed algo (why it's fast):
  1. ONE metadata pass only: probe with extract_info(download=False), then
     download with process_video_result(info, download=True) on the SAME
     YoutubeDL instance - no double page fetch.
  2. Progressive-first format selector: single-file mp4 whenever the site
     offers it (no ffmpeg step at all). Split DASH streams only as fallback,
     remuxed (not re-encoded) to mp4.
  3. concurrent_fragment_downloads=8: DASH/HLS fragments fetch in parallel.
  4. No FFmpegVideoConvertor postprocessor (that re-encodes = slow); only
     merge_output_format=mp4 (fast remux).
  5. Early rejects (live, >3h, over-cap estimate) before any bytes flow.

Works for YouTube AND any yt-dlp-supported site (Vimeo, TikTok, X/Twitter,
Dailymotion, Twitch clips, Rumble, ...). Direct .mp4 URLs skip yt-dlp and
use the plain HTTP downloader (fastest path).

Only download videos you have the right to use (your own, Creative Commons,
or explicitly licensed). YouTube ToS restricts downloading; the agent and
operator own that decision - see "Staying out of trouble" in README.
"""
from __future__ import annotations
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from config import SETTINGS
from license_guard import build_attribution, append_credits

QUALITY_HEIGHTS = {"360p": 360, "480p": 480, "720p": 720, "1080p": 1080, "best": 4320}

# Hosts where a page URL is almost certainly a video -> route straight to yt-dlp.
# (facebook/instagram stay out: login-walled, blocked in license_guard - embed those.)
KNOWN_VIDEO_HOSTS = (
    "youtube.com", "youtu.be", "youtube-nocookie.com", "m.youtube.com",
    "music.youtube.com", "vimeo.com", "player.vimeo.com",
    "dailymotion.com", "dai.ly", "tiktok.com", "vm.tiktok.com",
    "twitch.tv", "x.com", "twitter.com", "rumble.com", "odysee.com",
    "bitchute.com",
)

_DIRECT_VIDEO_EXTS = (".mp4", ".webm", ".mov", ".m4v", ".ogv")


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().split("@")[-1].split(":")[0]
    except Exception:
        return ""


def is_video_page_url(url: str) -> bool:
    """True for YouTube watch-type pages (not direct media files)."""
    if not url or not url.startswith(("http://", "https://")):
        return False
    host = _host(url)
    if not any(host == h or host.endswith("." + h) for h in
               ("youtube.com", "youtu.be", "youtube-nocookie.com")):
        return False
    if urlparse(url).path.lower().endswith(_DIRECT_VIDEO_EXTS):
        return False
    if "youtu.be" in host:
        return len((urlparse(url).path or "").strip("/")) > 0
    path = urlparse(url).path or ""
    qs = parse_qs(urlparse(url).query)
    return (path.startswith(("/watch", "/embed/", "/shorts/", "/live/", "/v/"))
            or "v" in qs)


def is_known_video_host(url: str) -> bool:
    """True for any known video-site host (YouTube, Vimeo, TikTok, ...)."""
    host = _host(url)
    if not host:
        return False
    return any(host == h or host.endswith("." + h) for h in KNOWN_VIDEO_HOSTS)


def is_direct_video_file(url: str) -> bool:
    return urlparse(url).path.lower().endswith(_DIRECT_VIDEO_EXTS)


def _format_selector(height: int) -> str:
    # Progressive single-file first (no ffmpeg step = fastest).
    # Split DASH video+audio only as fallback, remuxed to mp4.
    return (f"b[height<={height}][ext=mp4]/"
            f"b[height<={height}]/"
            f"bv*[height<={height}][ext=mp4]+ba[ext=m4a]/"
            f"bv*[height<={height}]+ba/best")


def _fast_opts(dest_dir: Path, height: int, cap_bytes: int) -> dict:
    opts: dict = {
        "format": _format_selector(height),
        "merge_output_format": "mp4",
        "outtmpl": str(dest_dir / "%(title).60s-%(id)s.%(ext)s"),
        "restrictfilenames": True,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 15,
        "retries": 2,
        "fragment_retries": 2,
        "concurrent_fragment_downloads": 8,
        "max_filesize": cap_bytes,
        "http_headers": {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/126.0 Safari/537.36"),
        },
    }
    if SETTINGS.yt_cookies_browser:
        opts["cookiesfrombrowser"] = (SETTINGS.yt_cookies_browser,)
    if SETTINGS.yt_cookies_file and Path(SETTINGS.yt_cookies_file).exists():
        opts["cookiefile"] = SETTINGS.yt_cookies_file
    return opts


def check_deps() -> tuple[bool, str]:
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        return False, "yt-dlp not installed. Run: pip install yt-dlp"
    if not shutil.which("ffmpeg"):
        return False, "ffmpeg not found on PATH (needed for split-stream sites). Install ffmpeg."
    return True, "ok"


def _resolve_video_dir(dest_subfolder: str | None) -> Path:
    from downloader import _slug
    raw = dest_subfolder or "videos"
    if ".." in raw or raw.startswith(("/", "\\")) or (len(raw) > 1 and raw[1] == ":"):
        raise ValueError("dest escapes MEDIA_ROOT - rejected")
    d = (SETTINGS.media_root / _slug(raw, 40)).resolve()
    if d != SETTINGS.media_root and SETTINGS.media_root not in d.parents:
        raise ValueError("dest escapes MEDIA_ROOT - rejected")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _friendly_error(source_url: str, e: Exception) -> dict:
    msg = str(e)
    if "Sign in to confirm" in msg or "bot" in msg.lower():
        return {"ok": False, "source_url": source_url,
                "error": "Video site bot-check blocked this IP. Set YT_COOKIES_BROWSER "
                         "(e.g. chrome) or YT_COOKIES_FILE=/path/cookies.txt and retry."}
    if "Unsupported URL" in msg:
        return {"ok": False, "source_url": source_url,
                "error": "unsupported URL for yt-dlp (not a video page)"}
    if "Private video" in msg or "Login required" in msg:
        return {"ok": False, "source_url": source_url,
                "error": "private/login-walled video - needs cookies or another result"}
    return {"ok": False, "source_url": source_url, "error": f"yt-dlp: {msg}"[:300]}


def download_video_page(source_url: str, dest_subfolder: str | None = None,
                        quality: str = "720p", title_hint: str = "") -> dict:
    """Download a video page (YouTube or any yt-dlp site) to a direct .mp4 file."""
    SETTINGS.ensure_dirs()
    ok, msg = check_deps()
    if not ok:
        return {"ok": False, "source_url": source_url, "error": msg}
    quality = (quality or SETTINGS.yt_default_quality).strip()
    height = QUALITY_HEIGHTS.get(quality, QUALITY_HEIGHTS.get(SETTINGS.yt_default_quality, 720))
    cap_mb = SETTINGS.max_video_mb
    cap_bytes = cap_mb * 1024 * 1024
    try:
        dest_dir = _resolve_video_dir(dest_subfolder)
    except ValueError as e:
        return {"ok": False, "source_url": source_url, "error": str(e)}

    import yt_dlp

    before = {p.name for p in dest_dir.glob("*")}
    vid, dur, title = "", 0, title_hint
    try:
        with yt_dlp.YoutubeDL(_fast_opts(dest_dir, height, cap_bytes)) as ydl:
            # Single metadata pass, then download from the SAME result object.
            info = ydl.extract_info(source_url, download=False)
            if not info:
                return {"ok": False, "source_url": source_url, "error": "video unavailable"}
            if info.get("_type") == "playlist":
                entries = [e for e in (info.get("entries") or []) if e]
                if not entries:
                    return {"ok": False, "source_url": source_url, "error": "empty playlist"}
                info = entries[0]  # noplaylist would do this anyway; take first fast
            if info.get("is_live"):
                return {"ok": False, "source_url": source_url,
                        "error": "live streams are not downloadable - embed instead"}
            dur = info.get("duration") or 0
            if dur and dur > 3 * 3600:
                return {"ok": False, "source_url": source_url,
                        "error": f"video too long ({dur // 60}min > 3h cap)"}
            vid = info.get("id", "")
            title = (info.get("title") or title_hint or vid)[:150]
            ydl.process_video_result(info, download=True)
    except Exception as e:
        return _friendly_error(source_url, e)

    cands = sorted((p for p in dest_dir.glob("*")
                    if p.name not in before and p.is_file()),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:  # name collision with an older file; take newest mp4
        mp4s = sorted(dest_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not mp4s:
            return {"ok": False, "source_url": source_url, "error": "download produced no file"}
        cands = [mp4s[0]]
    dest = cands[0]
    size = dest.stat().st_size
    if size > cap_bytes:
        dest.unlink(missing_ok=True)
        return {"ok": False, "source_url": source_url, "error": f"exceeds {cap_mb}MB cap"}
    if size == 0:
        dest.unlink(missing_ok=True)
        return {"ok": False, "source_url": source_url, "error": "empty file"}

    rel = dest.relative_to(SETTINGS.media_root).as_posix()
    safe_title = re.sub(r'"', "'", title)[:120]
    snippet = (f'<video src="/assets/{rel}" controls preload="metadata" '
               f'style="max-width:100%"></video>')
    append_credits(SETTINGS.credits_path, [build_attribution({
        "title": safe_title, "url": source_url, "image": source_url,
        "source": _host(source_url), "license_filter": ""})])
    return {"ok": True, "source_url": source_url, "local_path": str(dest),
            "relative_path": rel, "bytes": size, "title": safe_title,
            "video_id": vid, "duration": dur,
            "quality": quality, "height": height, "snippet": snippet,
            "downloaded_at": datetime.now(timezone.utc).isoformat()}


# backward-compat alias (old name)
def download_youtube(source_url: str, dest_subfolder: str | None = None,
                     quality: str = "720p", title_hint: str = "") -> dict:
    return download_video_page(source_url, dest_subfolder, quality, title_hint)
