import logging
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

import httpx

from app.core.config import settings


logger = logging.getLogger("lary.vosk")


class VoskModelManagerError(Exception):
    pass


def ensure_vosk_model_available() -> bool:
    if settings.speech_provider not in {"vosk", "salute_then_vosk"}:
        return False
    if not settings.vosk_model_path:
        logger.warning("vosk_model_path_missing")
        return False

    target_path = Path(settings.vosk_model_path)
    if _looks_like_vosk_model(target_path):
        return True

    if not settings.vosk_auto_download:
        logger.warning("vosk_model_missing auto_download_disabled path=%s", target_path)
        return False
    if not settings.vosk_model_url:
        logger.warning("vosk_model_missing download_url_missing path=%s", target_path)
        return False

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lary-vosk-download-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        archive_path = temp_dir / "model.zip"
        extract_dir = temp_dir / "extracted"
        _download_archive(settings.vosk_model_url, archive_path)
        with ZipFile(archive_path) as archive:
            archive.extractall(extract_dir)

        model_root = _find_model_root(extract_dir)
        if not model_root:
            raise VoskModelManagerError("Downloaded archive does not contain a Vosk model.")

        if target_path.exists():
            shutil.rmtree(target_path)
        shutil.copytree(model_root, target_path)

    logger.info("vosk_model_ready path=%s", target_path)
    return True


def _download_archive(url: str, archive_path: Path) -> None:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        shutil.copyfile(Path(parsed.path), archive_path)
        return

    with httpx.stream("GET", url, follow_redirects=True, timeout=300) as response:
        response.raise_for_status()
        with archive_path.open("wb") as output:
            for chunk in response.iter_bytes():
                if chunk:
                    output.write(chunk)


def _find_model_root(extract_dir: Path) -> Path | None:
    candidates = [extract_dir] + [item for item in extract_dir.rglob("*") if item.is_dir()]
    for candidate in candidates:
        if _looks_like_vosk_model(candidate):
            return candidate
    return None


def _looks_like_vosk_model(path: Path) -> bool:
    return path.is_dir() and (path / "conf").is_dir() and (path / "graph").is_dir()
