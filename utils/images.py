"""Обработка загруженных картинок (ТЗ, раздел 4)."""
import io
import uuid
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageOps, UnidentifiedImageError

from core import settings
from utils.logger import get_logger

logger = get_logger(__name__)

MAX_SIDE = 1600
THUMB_SIDE = 480
WEBP_QUALITY = 82
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
# Защита от «бомб»: огромная картинка в маленьком файле
PILImage.MAX_IMAGE_PIXELS = 50_000_000


class ImageError(Exception):
    """Понятная пользователю ошибка загрузки."""


def _save_webp(img: PILImage.Image, path: Path, side: int) -> None:
    copy = img.copy()
    copy.thumbnail((side, side), PILImage.Resampling.LANCZOS)
    copy.save(path, "WEBP", quality=WEBP_QUALITY, method=4)


def process_upload(data: bytes) -> str:
    """Проверяет и обрабатывает картинку, возвращает имя файла '<uuid>.webp'.

    Тип определяется по содержимому. EXIF-поворот применяется, метаданные (в том числе GPS)
    не сохраняются. Рядом кладётся миниатюра '<uuid>_thumb.webp'.
    """
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise ImageError(f"Файл больше {settings.MAX_UPLOAD_MB} МБ")
    try:
        img = PILImage.open(io.BytesIO(data))
        if img.format not in ALLOWED_FORMATS:
            raise ImageError("Допустимы только JPEG, PNG и WebP")
        if getattr(img, "is_animated", False):
            raise ImageError("Анимированные картинки не принимаются")
        img.load()
    except ImageError:
        raise
    except (UnidentifiedImageError, OSError, PILImage.DecompressionBombError):
        raise ImageError("Файл не похож на изображение")

    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "transparency" in img.info else "RGB")

    folder = settings.upload_path
    folder.mkdir(parents=True, exist_ok=True)
    name = uuid.uuid4().hex
    filename = f"{name}.webp"
    _save_webp(img, folder / filename, MAX_SIDE)
    _save_webp(img, folder / f"{name}_thumb.webp", THUMB_SIDE)
    return filename


def delete_image_files(filenames: list[str]) -> None:
    for filename in filenames:
        for variant in (filename, filename.replace(".webp", "_thumb.webp")):
            try:
                (settings.upload_path / variant).unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not delete file %s", variant)
