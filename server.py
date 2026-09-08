"""imagemcp MCP server - 100% free + self-hostable.

Tools:
  status, search_images, search_videos, search_web,
  camoufox_fetch, download_media, download_video, download_all,
  get_manifest, get_credits, optimize_image
All downloads are auto losslessly optimised (imageoptimiser) before paths
are handed to the agent. Video pages (YouTube + more) download as direct
.mp4 files via fast yt-dlp - no embeds needed.
"""
from __future__ import annotations
import json
import io
from pathlib import Path
from typing import Any

from config import SETTINGS

# --- FastMCP import (support both package layouts) ---
try:
    from fastmcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP  # type: ignore

try:
    from fastmcp.utilities.types import Image as MCPImage
except ImportError:
    try:
        from mcp.server.fastmcp.utilities.types import Image as MCPImage  # type: ignore
    except Exception:
        MCPImage = None  # type: ignore

mcp = FastMCP("imagemcp")

SETTINGS.ensure_dirs()

# ---------- helpers ----------
def _thumb_images(items: list[dict], limit: int = 3) -> list:
    """Fetch up to `limit` thumbnails and wrap as MCP Image blocks (vision for agent)."""
    if MCPImage is None:
        return []
    import httpx
    out = []
    for it in items[:limit]:
        url = it.get("thumbnail") or it.get("image")
        if not url or not url.startswith("http"):
            continue
        try:
            r = httpx.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
            if r.status_code != 200 or len(r.content) > 800_000:
                continue
            ct = r.headers.get("content-type", "image/jpeg")
            fmt = "jpeg"
            if "png" in ct:
                fmt = "png"
            elif "webp" in ct:
                fmt = "webp"
            elif "gif" in ct:
                fmt = "gif"
            # shrink big thumbs via PIL to keep context small
            try:
                from PIL import Image as PILImage
                im = PILImage.open(io.BytesIO(r.content))
                im.thumbnail((512, 512))
                buf = io.BytesIO()
                im.save(buf, format="JPEG" if fmt == "jpeg" else fmt.upper(), quality=70)
                out.append(MCPImage(data=buf.getvalue(), format="jpeg" if fmt == "jpeg" else fmt))
            except Exception:
                out.append(MCPImage(data=r.content, format=fmt))
        except Exception:
            continue
    return out

# ---------- tools ----------
@mcp.tool()
def status() -> dict:
    """Server status: providers, optimiser, dirs, caps. Everything free."""
    try:
        import ddgs
        ddgs_ok = True
    except Exception:
        try:
            import duckduckgo_search  # noqa
            ddgs_ok = True
        except Exception:
            ddgs_ok = False
    from providers import camoufox_provider
    from optimizer import imgopt_available
    cam_ok, cam_msg = camoufox_provider.available()
    opt_ok, opt_msg = imgopt_available()
    try:
        from video import check_deps as _yt_check
        yt_ok, yt_msg = _yt_check()
    except Exception as e:
        yt_ok, yt_msg = False, str(e)[:150]
    return {
        "name": "imagemcp",
        "version": "1.4.0",
        "tier": "free",
        "self_hostable": True,
        "ddgs_available": ddgs_ok,
        "camoufox_available": cam_ok,
        "camoufox_msg": cam_msg,
        "imgopt_available": opt_ok,
        "imgopt_msg": opt_msg,
        "imgopt_path": str(SETTINGS.imgopt_path),
        "ytdlp_available": yt_ok,
        "ytdlp_msg": yt_msg,
        "yt_default_quality": SETTINGS.yt_default_quality,
        "media_root": str(SETTINGS.media_root),
        "max_files": SETTINGS.max_files,
        "caps_mb": {"image": SETTINGS.max_image_mb, "video": SETTINGS.max_video_mb},
    }

@mcp.tool()
def search_images(query: str, max_results: int = 6, license_image: str | None = None,
                  size: str | None = None, color: str | None = None, layout: str | None = None,
                  auto_download: bool = False, dest_subfolder: str | None = None) -> Any:
    """Free web image search (DuckDuckGo/Bing, no key). Returns metadata + up to 3 vision thumbnails.
    Set auto_download=true to download + lossless-optimise everything found (cap 100)."""
    from providers import ddg_provider
    from license_guard import normalize_license
    max_results = max(1, min(int(max_results or 6), 30))
    lic = normalize_license(license_image if license_image is not None else SETTINGS.default_license)
    results = ddg_provider.search_images(query, max_results=max_results, license_image=lic,
                                         size=size, color=color, layout=layout)
    summary = {"query": query, "count": len(results), "license_filter": lic or "",
               "tier": "free", "lossless_optimised": True, "results": results}
    manifest = None
    if auto_download and results:
        from downloader import download_many
        urls = [r["image"] for r in results if r.get("image")]
        manifest = download_many(urls, dest_subfolder=dest_subfolder or query, meta=results)
        summary["manifest_id"] = manifest["job_id"]
        summary["downloaded"] = manifest["downloaded"]
    thumbs = _thumb_images(results, 3)
    if thumbs:
        return [json.dumps(summary, ensure_ascii=False)[:8000]] + thumbs
    return summary

@mcp.tool()
def search_videos(query: str, max_results: int = 4) -> dict:
    """Free web video search. Every hit can be downloaded as a direct file:
    pass any result URL to download_video (YouTube, Vimeo, TikTok, ...) - no embeds needed."""
    from providers import ddg_provider
    max_results = max(1, min(int(max_results or 4), 20))
    results = ddg_provider.search_videos(query, max_results=max_results)
    return {"query": query, "count": len(results), "results": results,
            "hint": "Pass any result URL to download_video for a direct .mp4 file."}

@mcp.tool()
def search_web(query: str, max_results: int = 5, backend: str = "auto") -> dict:
    """Free text browse (Google/Bing/DuckDuckGo via ddgs, no key)."""
    from providers import ddg_provider
    max_results = max(1, min(int(max_results or 5), 20))
    return {"query": query, "backend": backend, "results": ddg_provider.search_web(query, max_results, backend)}

@mcp.tool()
def camoufox_fetch(query_or_url: str, scroll_pages: int = 2, screenshot: bool = True,
                   dest_subfolder: str = "camoufox") -> dict:
    """Stealth fetch via Camoufox (JS sites, Google Images, Cloudflare). Free; requires ENABLE_CAMOUFOX=1."""
    from providers import camoufox_provider
    return camoufox_provider.fetch_images(query_or_url, scroll_pages, screenshot, dest_subfolder)

@mcp.tool()
def download_media(source_url: str, dest_subfolder: str | None = None, filename: str | None = None) -> dict:
    """Download one image/video the agent picked. Images are losslessly optimised
    instantly after download - the returned path is always the optimised file.
    Video pages (YouTube, Vimeo, TikTok, ...) auto-download as direct .mp4 files.
    Sandboxed to MEDIA_ROOT. Returns local + relative path + HTML snippet."""
    SETTINGS.ensure_dirs()
    from downloader import download_one
    return download_one(source_url, dest_subfolder, filename)

@mcp.tool()
def download_video(source_url: str, dest_subfolder: str | None = None,
                   quality: str = "720p") -> dict:
    """Download a video page as a direct .mp4 file - YouTube, Vimeo, TikTok, X, Dailymotion, Twitch, Rumble...
    Fast: single metadata pass, progressive mp4 preferred (no re-encode), 8 parallel fragments.
    quality: 360p | 480p | 720p (default) | 1080p | best. Only download videos you have rights to (own/CC/licensed)."""
    SETTINGS.ensure_dirs()
    quality = (quality or "720p").strip()
    if quality not in ("360p", "480p", "720p", "1080p", "best"):
        return {"ok": False, "source_url": source_url,
                "error": f"unknown quality {quality!r}; use 360p|480p|720p|1080p|best"}
    from video import is_direct_video_file, download_video_page
    from downloader import download_one
    if is_direct_video_file(source_url):
        return download_one(source_url, dest_subfolder)  # plain HTTP = fastest
    return download_video_page(source_url, dest_subfolder, quality=quality)

@mcp.tool()
def download_all(urls: list[str], dest_subfolder: str | None = None) -> dict:
    """Download EVERYTHING the agent lists (bulk, cap 100). Each image is losslessly
    optimised automatically before return; each video page saved as a direct .mp4.
    Returns manifest_id + per-file status + bytes_saved."""
    SETTINGS.ensure_dirs()
    if not urls:
        return {"ok": False, "error": "empty urls[]"}
    from downloader import download_many
    m = download_many(list(urls), dest_subfolder, max_files=SETTINGS.max_files)
    return {"ok": True, "job_id": m["job_id"], "requested": m["requested"],
            "downloaded": m["downloaded"], "failed": m["failed"],
            "results": m["results"][:50], "manifest_id": m["job_id"],
            "hint": "Use get_manifest(job_id) for full list. Files under MEDIA_ROOT; snippets ready to paste."}

@mcp.tool()
def optimize_image(relative_path: str, quality: int = 80) -> dict:
    """Maintenance only - every download is already optimised automatically,
    so the agent never needs this after download_media/download_all.
    Re-runs lossless optimisation on an older file under MEDIA_ROOT in-place
    (e.g. 'smoke/400.jpg'). Returns before/after bytes + method."""
    SETTINGS.ensure_dirs()
    if ".." in relative_path or relative_path.startswith(("/", "\\")):
        return {"ok": False, "error": "path escapes MEDIA_ROOT"}
    p = (SETTINGS.media_root / relative_path).resolve()
    if SETTINGS.media_root not in p.parents and p != SETTINGS.media_root:
        return {"ok": False, "error": "path escapes MEDIA_ROOT"}
    if not p.exists() or not p.is_file():
        return {"ok": False, "error": "file not found"}
    from optimizer import lossless_optimise, probe_dimensions
    res = lossless_optimise(p, quality)
    w, h = probe_dimensions(p)
    out = {"ok": bool(res.get("ok")), "local_path": str(p), "relative_path": relative_path,
           "width": w, "height": h, **res}
    if res.get("ok"):
        out["snippet"] = f'<img src="/assets/{relative_path}" alt="{p.stem}" loading="lazy" style="max-width:100%" />'
    return out

@mcp.tool()
def get_manifest(job_id: str) -> dict:
    """Fetch full bulk-download manifest by id."""
    p = SETTINGS.manifests_dir / f"{job_id}.json"
    if not p.exists():
        return {"ok": False, "error": f"unknown job_id {job_id}"}
    return {"ok": True, "manifest": json.loads(p.read_text(encoding="utf-8"))}

@mcp.tool()
def get_credits(limit: int = 50) -> dict:
    """Attribution ledger (source pages) for downloaded assets."""
    p = SETTINGS.credits_path
    if not p.exists():
        return {"ok": True, "count": 0, "credits": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return {"ok": True, "count": len(data), "credits": data[-int(limit):]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

if __name__ == "__main__":
    mcp.run()
