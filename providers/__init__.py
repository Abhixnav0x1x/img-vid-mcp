"""Free provider: ddgs (DuckDuckGo/Bing/Google, no API key) + 24h JSON cache."""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from config import SETTINGS

def _cache_key(kind: str, query: str, extra: str = "") -> Path:
    h = hashlib.md5(f"{kind}|{query}|{extra}".encode()).hexdigest()
    return SETTINGS.cache_dir / f"{kind}-{h}.json"

def _read_cache(p: Path) -> list | None:
    try:
        if not p.exists():
            return None
        age_h = (time.time() - p.stat().st_mtime) / 3600
        if age_h > SETTINGS.cache_ttl_hours:
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def _write_cache(p: Path, data: list) -> None:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False)[:500_000], encoding="utf-8")
    except Exception:
        pass

def _ddgs():
    try:
        from ddgs import DDGS
        return DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # old package name
            return DDGS
        except ImportError as e:
            raise RuntimeError("ddgs not installed. Run: pip install -U ddgs") from e

def search_images(query: str, max_results: int = 6, license_image: str | None = None,
                  size: str | None = None, color: str | None = None,
                  layout: str | None = None, backend: str = "auto") -> list[dict[str, Any]]:
    SETTINGS.ensure_dirs()
    lic = license_image or SETTINGS.default_license
    key_extra = f"{lic}|{size}|{color}|{layout}|{backend}"
    cp = _cache_key("img", query, key_extra)
    hit = _read_cache(cp)
    if hit is not None:
        return hit[:max_results]
    DDGS = _ddgs()
    kwargs: dict[str, Any] = {"query": query, "max_results": max_results}
    if lic:
        kwargs["license_image"] = lic
    if size:
        kwargs["size"] = size
    if color:
        kwargs["color"] = color
    if layout:
        kwargs["layout"] = layout
    # backend param name differs across versions; try both
    out: list[dict] = []
    for attempt_backend in ([backend] if backend != "auto" else ["auto", "bing", "duckduckgo"]):
        try:
            with DDGS(timeout=10) as ddgs:
                try:
                    res = list(ddgs.images(backend=attempt_backend, **kwargs))
                except TypeError:
                    res = list(ddgs.images(**kwargs))
            out = [{"title": r.get("title", "")[:200], "image": r.get("image", ""),
                    "thumbnail": r.get("thumbnail", ""), "url": r.get("url", ""),
                    "width": r.get("width"), "height": r.get("height"),
                    "source": r.get("source", ""), "license_filter": lic or ""} for r in res if r.get("image")]
            if out:
                break
        except Exception:
            continue
    _write_cache(cp, out)
    return out[:max_results]

def search_videos(query: str, max_results: int = 4, backend: str = "auto") -> list[dict[str, Any]]:
    SETTINGS.ensure_dirs()
    cp = _cache_key("vid", query, backend)
    hit = _read_cache(cp)
    if hit is not None:
        return hit[:max_results]
    DDGS = _ddgs()
    out: list[dict] = []
    for attempt_backend in ([backend] if backend != "auto" else ["auto"]):
        try:
            with DDGS(timeout=10) as ddgs:
                try:
                    res = list(ddgs.videos(query, max_results=max_results, backend=attempt_backend))
                except TypeError:
                    res = list(ddgs.videos(query, max_results=max_results))
            out = [{"title": r.get("title", "")[:200], "content": r.get("content", ""),
                    "description": (r.get("description", "") or "")[:300],
                    "duration": r.get("duration", ""), "publisher": r.get("publisher", r.get("provider", "")),
                    "url": r.get("content", "")} for r in res if r.get("content")]
            if out:
                break
        except Exception:
            continue
    _write_cache(cp, out)
    return out[:max_results]

def search_web(query: str, max_results: int = 5, backend: str = "auto") -> list[dict[str, Any]]:
    SETTINGS.ensure_dirs()
    cp = _cache_key("web", query, backend)
    hit = _read_cache(cp)
    if hit is not None:
        return hit[:max_results]
    DDGS = _ddgs()
    out: list[dict] = []
    backends = [backend] if backend != "auto" else ["auto", "google", "bing", "duckduckgo"]
    for b in backends:
        try:
            with DDGS(timeout=10) as ddgs:
                try:
                    res = list(ddgs.text(query, max_results=max_results, backend=b)) if b != "auto" else list(ddgs.text(query, max_results=max_results))
                except TypeError:
                    res = list(ddgs.text(query, max_results=max_results))
            out = [{"title": r.get("title", "")[:200], "href": r.get("href", r.get("url", "")),
                    "body": (r.get("body", "") or "")[:400]} for r in res]
            if out:
                break
        except Exception:
            continue
    _write_cache(cp, out)
    return out[:max_results]
