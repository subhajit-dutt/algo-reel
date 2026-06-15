from app.domain.enums import JobStatus

_ALLOWED_JOB_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset({JobStatus.SCRIPTING, JobStatus.CANCELLED}),
    JobStatus.SCRIPTING: frozenset({JobStatus.SCRIPT_READY, JobStatus.FAILED, JobStatus.CANCELLED}),
    JobStatus.SCRIPT_READY: frozenset({JobStatus.RENDERING, JobStatus.CANCELLED}),
    JobStatus.RENDERING: frozenset(
        {JobStatus.COMPOSING, JobStatus.FAILED, JobStatus.PARTIALLY_FAILED, JobStatus.CANCELLED}
    ),
    JobStatus.COMPOSING: frozenset({JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED}),
    JobStatus.DONE: frozenset(),
    JobStatus.FAILED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
    JobStatus.PARTIALLY_FAILED: frozenset({JobStatus.RENDERING}),
}

TERMINAL_JOB_STATUSES: frozenset[JobStatus] = frozenset(
    {JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.PARTIALLY_FAILED}
)


class IllegalStateTransitionError(Exception):
    pass


def assert_transition(src: JobStatus, dst: JobStatus) -> None:
    if dst not in _ALLOWED_JOB_TRANSITIONS[src]:
        raise IllegalStateTransitionError(f"illegal job transition: {src} -> {dst}")
