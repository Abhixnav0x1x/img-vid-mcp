"""Central config for imagemcp — 100% free + self-hostable."""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent

def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()

def _get_int(key: str, default: int) -> int:
    try:
        return int(_get(key, str(default)))
    except ValueError:
        return default

@dataclass(frozen=True)
class Settings:
    base_dir: Path = BASE_DIR
    media_root: Path = (BASE_DIR / _get("MEDIA_ROOT", "./public/assets")).resolve()
    storage_dir: Path = (BASE_DIR / _get("STORAGE_DIR", "./.storage")).resolve()
    # kept for backward compat — ignored, everything is free now
    license_key: str = _get("IMAGEMCP_LICENSE_KEY", "")
    premium_flag: bool = True
    enable_camoufox: bool = _get("ENABLE_CAMOUFOX", "0") == "1"
    max_image_mb: int = _get_int("MAX_IMAGE_MB", 15)
    max_video_mb: int = _get_int("MAX_VIDEO_MB", 200)
    max_files: int = _get_int("MAX_FILES", 100)
    timeout: int = _get_int("REQUEST_TIMEOUT_SEC", 30)
    cache_ttl_hours: int = _get_int("CACHE_TTL_HOURS", 24)
    default_license: str | None = _get("DEFAULT_LICENSE_FILTER", "ShareCommercially") or None
    # lossless optimiser (local imageoptimiser project)
    imgopt_enabled: bool = _get("IMGOPT_ENABLED", "1") == "1"
    imgopt_quality: int = _get_int("IMGOPT_QUALITY", 80)
    imgopt_path: Path = (BASE_DIR / _get("IMAGEOPTIMISER_PATH", "../imageoptimiser")).resolve()
    # youtube downloads via yt-dlp (direct .mp4 files, no embeds)
    yt_default_quality: str = _get("YT_DEFAULT_QUALITY", "720p")
    yt_cookies_browser: str = _get("YT_COOKIES_BROWSER", "")
    yt_cookies_file: str = _get("YT_COOKIES_FILE", "")

    @property
    def is_premium(self) -> bool:
        return True

    @property
    def max_files_free(self) -> int:
        return self.max_files

    @property
    def max_files_pro(self) -> int:
        return self.max_files

    @property
    def cache_dir(self) -> Path:
        return self.storage_dir / "cache"

    @property
    def manifests_dir(self) -> Path:
        return self.storage_dir / "manifests"

    @property
    def credits_path(self) -> Path:
        return self.media_root / "credits.json"

    def ensure_dirs(self) -> None:
        self.media_root.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)

SETTINGS = Settings()
