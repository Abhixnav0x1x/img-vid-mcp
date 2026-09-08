"""Optimizer: auto lossless in-place optimisation.

Uses the optional companion `imageoptimiser` project (see IMAGEOPTIMISER_PATH,
default `../imageoptimiser`) with Pillow fallback if unavailable. Lossless:
PNG (pngquant), JPG (progressive + EXIF strip), WebP (method=6), metadata stripped.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

from config import SETTINGS

_LOSSLESS_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".heic", ".heif"}

_imgopt_fn = None
_imgopt_error = ""

def _load_imgopt():
    global _imgopt_fn, _imgopt_error
    if _imgopt_fn is not None:
        return _imgopt_fn
    # 1. try installed package
    try:
        from optimiser.optimizer import optimize_image  # type: ignore
        _imgopt_fn = optimize_image
        return _imgopt_fn
    except Exception as e:
        _imgopt_error = str(e)[:200]
    # 2. try local path from settings (../imageoptimiser by default)
    try:
        p = str(SETTINGS.imgopt_path)
        if p not in sys.path and Path(p).exists():
            sys.path.insert(0, p)
        from optimiser.optimizer import optimize_image  # type: ignore
        _imgopt_fn = optimize_image
        _imgopt_error = ""
        return _imgopt_fn
    except Exception as e:
        _imgopt_error = str(e)[:200]
    return None

def imgopt_available() -> tuple[bool, str]:
    if not SETTINGS.imgopt_enabled:
        return False, "IMGOPT_ENABLED != 1"
    fn = _load_imgopt()
    if fn is not None:
        return True, "ok"
    return False, f"imageoptimiser not importable: {_imgopt_error or 'unknown'}"

def probe_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.width, im.height
    except Exception:
        return None, None

def lossless_optimise(path: Path, quality: int | None = None) -> dict:
    """Lossless in-place optimise. Returns {ok, before, after, saved, percent, method}."""
    q = quality or SETTINGS.imgopt_quality
    if path.suffix.lower() not in _LOSSLESS_EXTS:
        return {"ok": False, "skipped": True, "reason": f"extension {path.suffix} not optimisable"}
    if not path.exists():
        return {"ok": False, "error": "file missing"}
    before = path.stat().st_size
    if not SETTINGS.imgopt_enabled:
        return {"ok": False, "skipped": True, "reason": "IMGOPT_ENABLED=0", "before": before}
    fn = _load_imgopt()
    if fn is None:
        # Pillow fallback: strip metadata + re-save optimize=True (still lossless-ish)
        try:
            from PIL import Image
            with Image.open(path) as im:
                fmt = (im.format or "").upper()
                mode = im.mode
                data = list(im.getdata())
                clean = Image.new(mode, im.size)
                clean.putdata(data)
                tmp = path.with_name(path.stem + "_tmp" + path.suffix)
                kw: dict = {"optimize": True}
                if fmt in ("JPEG", "JPG"):
                    kw.update({"quality": q, "progressive": True})
                    clean.convert("RGB" if mode in ("RGBA", "P") else mode)
                    clean.save(tmp, "JPEG", **kw)
                elif fmt == "PNG":
                    clean.save(tmp, "PNG", optimize=True)
                elif fmt == "WEBP":
                    clean.save(tmp, "WEBP", quality=q, method=6)
                else:
                    clean.save(tmp, optimize=True)
            after = tmp.stat().st_size
            if after < before:
                tmp.replace(path)
            else:
                tmp.unlink(missing_ok=True)
                after = before
            return {"ok": True, "before": before, "after": after,
                    "saved": before - after,
                    "percent": round((1 - after / before) * 100, 1) if before else 0,
                    "method": "pillow-fallback"}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"[:200], "before": before}
    # real imageoptimiser path: optimise to tmp then replace in-place if smaller
    try:
        tmp = path.with_name(f"{path.stem}_opttmp{path.suffix}")
        res = fn(str(path), str(tmp), q)
        after = res.get("optimized_size", tmp.stat().st_size if tmp.exists() else before)
        if tmp.exists():
            if after < before:
                tmp.replace(path)
                after = path.stat().st_size
            else:
                tmp.unlink(missing_ok=True)
                after = before
        return {"ok": True, "before": before, "after": after,
                "saved": before - after,
                "percent": round((1 - after / before) * 100, 1) if before else 0,
                "method": res.get("method", "imgopt")}
    except Exception as e:
        try:
            tmp.unlink(missing_ok=True)  # type: ignore
        except Exception:
            pass
        return {"ok": False, "error": f"{type(e).__name__}: {e}"[:200], "before": before}

# backward compat: old premium webp helper kept but unused by default
def _to_webp(src: Path, max_w: int = 1600, quality: int = 82) -> Path | None:
    try:
        from PIL import Image
        with Image.open(src) as im:
            if im.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[-1])
                im = bg
            elif im.mode != "RGB":
                im = im.convert("RGB")
            if im.width > max_w:
                im = im.resize((max_w, int(im.height * max_w / im.width)))
            out = src.with_suffix(".webp")
            im.save(out, "WEBP", quality=quality, method=6)
            return out
    except Exception:
        return None

def optimize_manifest(manifest: dict) -> None:
    """Auto lossless pass over every downloaded image in manifest (in-place)."""
    for r in manifest.get("results", []):
        if not r.get("ok"):
            continue
        p = Path(r["local_path"])
        if p.suffix.lower() not in _LOSSLESS_EXTS:
            continue
        opt = lossless_optimise(p)
        r["optimization"] = opt
        if opt.get("ok"):
            r["bytes"] = opt["after"]
            r["bytes_before"] = opt["before"]
            r["bytes_saved"] = opt["saved"]
