from pathlib import Path

from app.config import get_settings
from app.storage.base import StoredObject


class LocalStorage:
    """Filesystem-backed Storage. `content_type` is accepted for interface parity
    with the future S3 backend; the local filesystem does not record it."""

    def __init__(self, media_root: Path | str) -> None:
        self._root = Path(media_root)

    async def put(self, key: str, data: bytes, content_type: str) -> StoredObject:
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredObject(key=key, bytes=len(data))

    async def get(self, key: str) -> bytes:
        return (self._root / key).read_bytes()

    def url(self, key: str) -> str:
        return (self._root / key).resolve().as_uri()


def get_storage() -> LocalStorage:
    return LocalStorage(get_settings().media_root)
