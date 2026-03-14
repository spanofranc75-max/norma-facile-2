"""Object Storage service — local filesystem (Railway-compatible)."""
import os
import uuid
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Su Railway usa /tmp, in locale usa una cartella uploads
STORAGE_BASE = Path(os.environ.get("STORAGE_PATH", "/tmp/norma-facile-storage"))


def init_storage():
    """Inizializza lo storage locale."""
    try:
        STORAGE_BASE.mkdir(parents=True, exist_ok=True)
        logger.info(f"Storage locale inizializzato: {STORAGE_BASE}")
        return str(STORAGE_BASE)
    except Exception as e:
        logger.warning(f"Storage init warning: {e}")
        return str(STORAGE_BASE)


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Salva file in locale."""
    init_storage()
    full_path = STORAGE_BASE / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)
    logger.info(f"File salvato: {full_path}")
    return {
        "path": path,
        "size": len(data),
        "etag": str(uuid.uuid4()),
    }


def get_object(path: str) -> tuple:
    """Legge file da locale."""
    full_path = STORAGE_BASE / path
    if not full_path.exists():
        raise FileNotFoundError(f"File non trovato: {path}")
    content_type = "application/octet-stream"
    if path.endswith(".jpg") or path.endswith(".jpeg"):
        content_type = "image/jpeg"
    elif path.endswith(".png"):
        content_type = "image/png"
    elif path.endswith(".pdf"):
        content_type = "application/pdf"
    return full_path.read_bytes(), content_type


def upload_photo(user_id: str, file_data: bytes, 
                 filename: str, content_type: str) -> dict:
    """Upload foto e restituisce info storage."""
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    storage_path = f"sopralluoghi/{user_id}/{uuid.uuid4()}.{ext}"
    result = put_object(storage_path, file_data, content_type)
    return {
        "storage_path": result["path"],
        "original_filename": filename,
        "content_type": content_type,
        "size": result.get("size", len(file_data)),
    }
