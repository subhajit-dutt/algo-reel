from pathlib import Path

from app.storage import LocalStorage, StoredObject


async def test_put_writes_file_and_returns_metadata(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    data = b"RIFFsomewavbytes"
    stored = await storage.put("audio/1/2.wav", data, "audio/wav")
    assert isinstance(stored, StoredObject)
    assert stored.key == "audio/1/2.wav"
    assert stored.bytes == len(data)
    written = tmp_path / "audio" / "1" / "2.wav"
    assert written.read_bytes() == data


async def test_put_creates_nested_dirs(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    await storage.put("audio/42/100.wav", b"x", "audio/wav")
    assert (tmp_path / "audio" / "42" / "100.wav").exists()


def test_url_is_file_uri(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    assert storage.url("audio/1/2.wav").startswith("file://")
    assert storage.url("audio/1/2.wav").endswith("audio/1/2.wav")


async def test_get_round_trips_bytes(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    await storage.put("video/1/2.mp4", b"\x00MP4DATA", "video/mp4")
    assert await storage.get("video/1/2.mp4") == b"\x00MP4DATA"
