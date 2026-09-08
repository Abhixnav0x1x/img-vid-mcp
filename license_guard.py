"""License guard: enforce CC-friendly filters, blocklist, attribution."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

ALLOWED_LICENSES = {
    None, "", "any",
    "Public", "Share", "ShareCommercially",
    "Modify", "ModifyCommercially",
}

# Domains we never download from (trackers, paywalls known-bad).
BLOCKED_SUBSTRINGS = [
    "localhost", "127.", "10.", "192.168.", "169.254.",
    "facebook.com", "instagram.com",  # require login; prefer embed
]

def normalize_license(v: str | None) -> str | None:
    if not v:
        return None
    v = v.strip()
    if v in ("None", "any", ""):
        return None
    if v not in ALLOWED_LICENSES:
        raise ValueError(f"Unknown license_image={v!r}. Use one of {sorted(x or 'any' for x in ALLOWED_LICENSES)}")
    return v

def is_blocked_url(url: str) -> bool:
    u = url.lower()
    if not (u.startswith("http://") or u.startswith("https://")):
        return True
    return any(b in u for b in BLOCKED_SUBSTRINGS)

def build_attribution(item: dict) -> dict:
    return {
        "title": item.get("title", "")[:200],
        "source_page": item.get("url") or item.get("source_page") or "",
        "direct_url": item.get("image") or item.get("content") or item.get("source_url") or "",
        "source": item.get("source") or item.get("publisher") or "",
        "license_filter": item.get("license_filter") or "",
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
    }

def append_credits(credits_path: Path, entries: list[dict]) -> int:
    credits_path.parent.mkdir(parents=True, exist_ok=True)
    existing: list = []
    if credits_path.exists():
        try:
            existing = json.loads(credits_path.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []
    seen = {e.get("direct_url") for e in existing}
    added = 0
    for e in entries:
        if e.get("direct_url") not in seen:
            existing.append(e)
            seen.add(e.get("direct_url"))
            added += 1
    credits_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    return added
