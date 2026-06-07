from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredObject:
    key: str
    bytes: int


class Storage(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> StoredObject: ...

    def url(self, key: str) -> str: ...
