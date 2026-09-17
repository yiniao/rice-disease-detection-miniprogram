import base64
import binascii
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.core.files.storage import default_storage
from PIL import Image, UnidentifiedImageError


def encode_bytes_to_base64(content):
    return base64.b64encode(content).decode("ascii")


def encode_bytes_to_data_url(content, mime_type="image/jpeg"):
    if not content:
        return ""
    return f"data:{mime_type};base64,{encode_bytes_to_base64(content)}"


def image_bytes_to_data_url(content, *, max_size=None, quality=82, mime_type="image/jpeg"):
    if not content:
        return ""
    raw_bytes = content
    if max_size:
        try:
            with Image.open(BytesIO(content)) as image:
                image = image.convert("RGB")
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=quality)
                raw_bytes = buffer.getvalue()
        except UnidentifiedImageError as exc:
            raise ValueError("无法识别图片内容。") from exc
    return encode_bytes_to_data_url(raw_bytes, mime_type=mime_type)


def fetch_remote_image_bytes(url, *, timeout=15):
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("不支持的图片链接。")

    request = Request(
        parsed.geturl(),
        headers={
            "User-Agent": "rice-guard/1.0",
            "Accept": "image/*,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except Exception as exc:
        raise ValueError("无法下载图片内容。") from exc


def decode_image_bytes(value):
    if not value:
        return b""

    payload = value.strip()
    if payload.startswith("data:") and "," in payload:
        payload = payload.split(",", 1)[1]

    try:
        return base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        if default_storage.exists(payload):
            with default_storage.open(payload, "rb") as handle:
                return handle.read()
        if Path(payload).exists():
            return Path(payload).read_bytes()
        raise ValueError("无法解析图片内容。")


def decode_image_to_jpeg_bytes(value):
    raw_bytes = decode_image_bytes(value)
    if not raw_bytes:
        return b""

    try:
        with Image.open(BytesIO(raw_bytes)) as image:
            image = image.convert("RGB")
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=92)
            return buffer.getvalue()
    except UnidentifiedImageError as exc:
        raise ValueError("无法识别图片内容。") from exc


def image_dimensions(value):
    raw_bytes = decode_image_bytes(value)
    if not raw_bytes:
        return 0, 0

    try:
        with Image.open(BytesIO(raw_bytes)) as image:
            return image.size
    except UnidentifiedImageError as exc:
        raise ValueError("无法识别图片内容。") from exc


def image_byte_size(value):
    return len(decode_image_bytes(value))
