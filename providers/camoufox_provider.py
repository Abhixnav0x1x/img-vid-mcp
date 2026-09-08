"""Stealth provider: Camoufox browser fallback (optional, free + self-hosted)."""
from __future__ import annotations
import re
from pathlib import Path
from urllib.parse import quote_plus

from config import SETTINGS

def available() -> tuple[bool, str]:
    if not SETTINGS.enable_camoufox:
        return False, "ENABLE_CAMOUFOX != 1. Set ENABLE_CAMOUFOX=1 and run `python -m camoufox fetch`."
    try:
        import camoufox  # noqa: F401
        return True, "ok"
    except ImportError:
        return False, "camoufox not installed. Run: pip install 'camoufox[geoip]' && python -m camoufox fetch"

def fetch_images(query_or_url: str, scroll_pages: int = 2, screenshot: bool = True,
                 dest_subfolder: str = "camoufox") -> dict:
    ok, msg = available()
    if not ok:
        return {"ok": False, "error": msg}
    try:
        from camoufox.sync_api import Camoufox
    except Exception as e:
        return {"ok": False, "error": f"camoufox import failed: {e}"}
    SETTINGS.ensure_dirs()
    target = query_or_url
    if not query_or_url.startswith("http"):
        target = f"https://www.google.com/search?q={quote_plus(query_or_url)}&tbm=isch&tbs=il:cl"
    images: list[dict] = []
    shot_path: str | None = None
    try:
        with Camoufox(headless=True, humanize=True) as browser:
            page = browser.new_page()
            page.goto(target, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)
            for _ in range(max(0, min(scroll_pages, 5))):
                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(1200)
            # grab <img> srcs
            try:
                els = page.query_selector_all("img")
                for el in els[:60]:
                    try:
                        src = el.get_attribute("src") or el.get_attribute("data-src") or ""
                        alt = (el.get_attribute("alt") or "")[:150]
                        if src.startswith("http") and len(src) > 20:
                            images.append({"image": src, "thumbnail": src, "title": alt, "url": target, "source": "camoufox"})
                    except Exception:
                        continue
            except Exception:
                pass
            # dedupe, cap 20
            seen, uniq = set(), []
            for im in images:
                if im["image"] not in seen:
                    seen.add(im["image"])
                    uniq.append(im)
            images = uniq[:20]
            if screenshot:
                out = (SETTINGS.media_root / _safe_sub(dest_subfolder) / "camoufox-preview.png").resolve()
                out.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(out), full_page=False)
                shot_path = str(out)
            try:
                page.close()
            except Exception:
                pass
        return {"ok": True, "target": target, "count": len(images), "images": images, "screenshot": shot_path}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"[:400]}

def _safe_sub(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (s or "camoufox").lower()).strip("-")
    return s[:40] or "camoufox"
