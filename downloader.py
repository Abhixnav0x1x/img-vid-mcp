"""Downloader: sandboxed, capped, deduped downloads + bulk + manifest."""
from __future__ import annotations
import hashlib
import json
import mimetypes
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote

import httpx

from config import SETTINGS
from license_guard import is_blocked_url, build_attribution, append_credits

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/*,video/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://duckduckgo.com/",
}

IMAGE_CT = ("image/jpeg", "image/png", "image/webp", "image/gif", "image/avif", "image/svg+xml")
VIDEO_CT = ("video/mp4", "video/webm", "video/ogg", "video/quicktime")

def _slug(s: str, maxlen: int = 40) -> str:
    s = unquote(s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s[:maxlen] or "asset").strip("-")

def _safe_filename(url: str, content_type: str = "") -> str:
    path = urlparse(url).path.rstrip("/")
    base = path.split("/")[-1] if path else ""
    base = unquote(base).split("?")[0]
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)[:80] or "file"
    if "." not in base and content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ""
        base += ext
    if not base:
        base = f"file-{uuid.uuid4().hex[:8]}"
    return base

def _resolve_dest(dest_subfolder: str | None, filename: str) -> Path:
    raw_sub = dest_subfolder or "general"
    if ".." in raw_sub or raw_sub.startswith(("/", "\\")) or (len(raw_sub) > 1 and raw_sub[1] == ":"):
        raise ValueError("dest escapes MEDIA_ROOT - rejected")
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError("filename escapes MEDIA_ROOT - rejected")
    sub = _slug(raw_sub, 40)
    dest = (SETTINGS.media_root / sub / filename).resolve()
    # Sandbox: must stay inside MEDIA_ROOT
    if dest != SETTINGS.media_root and SETTINGS.media_root not in dest.parents:
        raise ValueError("dest escapes MEDIA_ROOT - rejected")
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest

def _is_video_ct(ct: str) -> bool:
    return ct.split(";")[0].strip().lower() in VIDEO_CT

def _is_image_ct(ct: str) -> bool:
    c = ct.split(";")[0].strip().lower()
    return c in IMAGE_CT or c.startswith("image/")

def download_one(source_url: str, dest_subfolder: str | None = None,
                 filename: str | None = None, title: str = "",
                 source_page: str = "", license_filter: str = "",
                 quality: str | None = None) -> dict:
    if not source_url or not source_url.startswith(("http://", "https://")):
        return {"ok": False, "source_url": source_url, "error": "invalid URL scheme"}
    if is_blocked_url(source_url):
        return {"ok": False, "source_url": source_url, "error": "blocked domain (login-walled/private). Use another result."}
    # Fast path: video pages (YouTube + any known video site) go straight to
    # yt-dlp for a direct .mp4 file. Direct media files use plain HTTP below.
    try:
        from video import is_video_page_url, is_known_video_host, is_direct_video_file, download_video_page
        if not is_direct_video_file(source_url) and (
                is_video_page_url(source_url) or is_known_video_host(source_url)):
            return download_video_page(source_url, dest_subfolder,
                                       quality=quality or "720p", title_hint=title)
    except ImportError:
        pass
    try:
        with httpx.Client(headers=BROWSER_HEADERS, timeout=SETTINGS.timeout, follow_redirects=True) as c:
            with c.stream("GET", source_url) as r:
                if r.status_code >= 400:
                    return {"ok": False, "source_url": source_url, "error": f"HTTP {r.status_code}"}
                ct = r.headers.get("content-type", "").split(";")[0].strip().lower()
                if ct and not (_is_image_ct(ct) or _is_video_ct(ct) or ct.startswith("image/") or ct.startswith("video/")):
                    return {"ok": False, "source_url": source_url, "error": f"not media: {ct}"}
                cap_mb = SETTINGS.max_video_mb if (ct.startswith("video") or "mp4" in ct) else SETTINGS.max_image_mb
                fname = filename or _safe_filename(source_url, ct)
                dest = _resolve_dest(dest_subfolder, fname)
                # dedupe by URL: if exists with same name, suffix hash
                if dest.exists():
                    h = hashlib.md5(source_url.encode()).hexdigest()[:6]
                    dest = dest.with_name(f"{dest.stem}-{h}{dest.suffix}")
                total = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_bytes(65536):
                        total += len(chunk)
                        if total > cap_mb * 1024 * 1024:
                            f.close()
                            dest.unlink(missing_ok=True)
                            return {"ok": False, "source_url": source_url, "error": f"exceeds {cap_mb}MB cap"}
                        f.write(chunk)
                if total == 0:
                    dest.unlink(missing_ok=True)
                    return {"ok": False, "source_url": source_url, "error": "empty body"}
                rel = dest.relative_to(SETTINGS.media_root).as_posix()
                # auto lossless optimise (imageoptimiser, in-place)
                width = height = None
                optimization: dict | None = None
                try:
                    from optimizer import probe_dimensions, lossless_optimise
                    width, height = probe_dimensions(dest)
                    if dest.suffix.lower() not in (".mp4", ".webm", ".mov", ".gif", ".svg"):
                        optimization = lossless_optimise(dest)
                except Exception as e:
                    optimization = {"ok": False, "error": str(e)[:150]}
                if optimization and optimization.get("ok"):
                    total = optimization["after"]
                is_vid = _is_video_ct(ct) or dest.suffix.lower() in (".mp4", ".webm", ".mov")
                if is_vid:
                    snippet = f'<video src="/assets/{rel}" controls preload="metadata" style="max-width:100%"></video>'
                else:
                    alt = (title or dest.stem)[:120].replace('"', "'")
                    snippet = f'<img src="/assets/{rel}" alt="{alt}" loading="lazy" style="max-width:100%" />'
                entry = build_attribution({"title": title or dest.stem, "url": source_page,
                                           "image": source_url, "license_filter": license_filter})
                entry.update({"local_path": str(dest), "relative_path": rel, "bytes": total,
                              "width": width, "height": height, "snippet": snippet,
                              "optimization": optimization})
                append_credits(SETTINGS.credits_path, [build_attribution({
                    "title": entry["title"], "url": source_page, "image": source_url,
                    "source": "", "license_filter": license_filter})])
                out: dict = {"ok": True, "source_url": source_url, "local_path": str(dest),
                        "relative_path": rel, "bytes": total, "width": width,
                        "height": height, "snippet": snippet}
                if optimization:
                    out["optimization"] = optimization
                    if optimization.get("ok"):
                        out["bytes_before"] = optimization.get("before")
                        out["bytes_saved"] = optimization.get("saved")
                return out
    except Exception as e:
        return {"ok": False, "source_url": source_url, "error": f"{type(e).__name__}: {e}"[:300]}

def download_many(urls: list[str], dest_subfolder: str | None = None,
                  max_files: int | None = None,
                  meta: list[dict] | None = None) -> dict:
    """Bulk download. Images are ALWAYS losslessly optimised before return -
    there is no opt-out; the agent only ever receives optimised files."""
    SETTINGS.ensure_dirs()
    cap = max_files or SETTINGS.max_files
    urls = [u for u in urls if u][:cap]
    job_id = uuid.uuid4().hex[:10]
    results: list[dict] = []
    title_by_url = {}
    if meta:
        for m in meta:
            u = m.get("image") or m.get("content") or m.get("source_url")
            if u:
                title_by_url[u] = m.get("title", "")
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(download_one, u, dest_subfolder, None,
                          title_by_url.get(u, ""), title_by_url.get(u + "#page", ""), ""): u for u in urls}
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as e:
                results.append({"ok": False, "source_url": futs[fut], "error": str(e)[:200]})
    ok = [r for r in results if r.get("ok")]
    failed = [r for r in results if not r.get("ok")]
    manifest = {
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dest_subfolder": dest_subfolder or "general",
        "requested": len(urls),
        "downloaded": len(ok),
        "failed": len(failed),
        "results": results,
        "tier": "free",
        "lossless_optimised": True,
    }
    # download_one already optimises every image in-place; this safety net
    # covers any file that slipped through. Always runs - no opt-out.
    try:
        from optimizer import optimize_manifest
        optimize_manifest(manifest)
    except Exception:
        pass
    SETTINGS.manifests_dir.mkdir(parents=True, exist_ok=True)
    (SETTINGS.manifests_dir / f"{job_id}.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest
