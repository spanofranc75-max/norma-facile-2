"""Reference solution images for perizia PDF.

Maps AI keywords to solution images for the PDF report.
Images are loaded as base64 on first access and cached.
"""
import base64
import os
import logging

logger = logging.getLogger(__name__)

REF_DIR = os.path.join(os.path.dirname(__file__), "ref_images")

# keyword -> filename mapping
KEYWORD_MAP = {
    "costa": "costa.png",
    "costa ottica": "costa.png",
    "costa sensibile": "costa.png",
    "fotocellula": "fotocellula.png",
    "fotocellule": "fotocellula.png",
    "rete": "rete.png",
    "rete anti-cesoiamento": "rete.png",
    "encoder": "encoder.png",
    "motore": "encoder.png",
    "limitatore": "encoder.png",
}

_cache = {}


def get_ref_image_b64(keyword: str) -> str:
    """Return base64-encoded reference image for a keyword. Empty string if not found."""
    kw = keyword.lower().strip()
    fname = None
    for k, v in KEYWORD_MAP.items():
        if k in kw or kw in k:
            fname = v
            break
    if not fname:
        return ""
    if fname in _cache:
        return _cache[fname]
    path = os.path.join(REF_DIR, fname)
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        _cache[fname] = b64
        return b64
    except Exception as e:
        logger.warning(f"Failed to load ref image {fname}: {e}")
        return ""
