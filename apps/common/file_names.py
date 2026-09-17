from pathlib import Path


def sanitize_filename(name, default="image.jpg"):
    value = str(name or "").strip().replace("\\", "/")
    candidate = Path(value).name
    if not candidate:
        candidate = default

    cleaned = "".join(char for char in candidate if char not in '<>:"/\\|?*').strip().strip(".")
    if not cleaned:
        cleaned = default

    stem = Path(cleaned).stem.strip() or Path(default).stem
    suffix = Path(cleaned).suffix.lower() or Path(default).suffix or ".jpg"
    return f"{stem}{suffix}"


def derive_visualized_filename(name, suffix="_result"):
    original = sanitize_filename(name)
    path = Path(original)
    return f"{path.stem}{suffix}{path.suffix or '.jpg'}"
