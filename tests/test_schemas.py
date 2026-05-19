from datetime import UTC, datetime

from app.domain.enums import JobStatus
from app.schemas.event import ProgressEvent


class TestProgressEvent:
    def test_round_trip_json(self) -> None:
        e = ProgressEvent(
            event="transition",
            job_id=42,
            status=JobStatus.RENDERING,
            progress={"current_scene": 2, "total": 4, "stage": "stub_render"},
            scene_id=99,
            error=None,
            ts=datetime(2026, 5, 19, 12, 0, tzinfo=UTC),
        )
        raw = e.model_dump_json()
        parsed = ProgressEvent.model_validate_json(raw)
        assert parsed == e

    def test_terminal_done_event(self) -> None:
        e = ProgressEvent(
            event="done",
            job_id=1,
            status=JobStatus.DONE,
            progress={},
            ts=datetime.now(tz=UTC),
        )
        assert e.event == "done"
        assert e.scene_id is None
        assert e.error is None
