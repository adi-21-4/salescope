import uuid
from pathlib import Path

STORAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "storage" / "uploads"


def save_upload(shop_id: uuid.UUID, dataset_id: uuid.UUID, filename: str, content: bytes) -> str:
    """Persist a raw uploaded file to local disk, scoped by shop then dataset.

    Local disk is a deliberate placeholder for M1 — swapping this for S3/blob storage
    later only touches this module, since routers/services only ever call
    save_upload/load_upload and store the returned path string.
    """
    shop_dir = STORAGE_ROOT / str(shop_id)
    shop_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix
    dest = shop_dir / f"{dataset_id}{ext}"
    dest.write_bytes(content)
    return str(dest)
