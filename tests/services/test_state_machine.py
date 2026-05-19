import pytest

from app.domain.enums import JobStatus
from app.domain.state_machine import IllegalStateTransition, assert_transition


class TestJobStatusTransitions:
    def test_queued_to_scripting_is_allowed(self) -> None:
        assert_transition(JobStatus.QUEUED, JobStatus.SCRIPTING)

    def test_queued_to_cancelled_is_allowed(self) -> None:
        assert_transition(JobStatus.QUEUED, JobStatus.CANCELLED)

    def test_scripting_to_script_ready_is_allowed(self) -> None:
        assert_transition(JobStatus.SCRIPTING, JobStatus.SCRIPT_READY)

    def test_script_ready_to_rendering_is_allowed(self) -> None:
        assert_transition(JobStatus.SCRIPT_READY, JobStatus.RENDERING)

    def test_rendering_to_composing_is_allowed(self) -> None:
        assert_transition(JobStatus.RENDERING, JobStatus.COMPOSING)

    def test_composing_to_done_is_allowed(self) -> None:
        assert_transition(JobStatus.COMPOSING, JobStatus.DONE)

    def test_rendering_to_partially_failed_is_allowed(self) -> None:
        assert_transition(JobStatus.RENDERING, JobStatus.PARTIALLY_FAILED)

    @pytest.mark.parametrize(
        "src",
        [
            JobStatus.DONE,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.PARTIALLY_FAILED,
        ],
    )
    def test_terminal_states_have_no_outgoing_edges(self, src: JobStatus) -> None:
        with pytest.raises(IllegalStateTransition):
            assert_transition(src, JobStatus.RENDERING)

    def test_queued_to_done_is_disallowed(self) -> None:
        with pytest.raises(IllegalStateTransition) as exc:
            assert_transition(JobStatus.QUEUED, JobStatus.DONE)
        assert "queued" in str(exc.value) and "done" in str(exc.value)

    def test_idempotent_same_state_is_disallowed(self) -> None:
        with pytest.raises(IllegalStateTransition):
            assert_transition(JobStatus.RENDERING, JobStatus.RENDERING)
