"""Shared test doubles for the arq render pool."""


class FakeArqJob:
    def __init__(self, value: object = None, exc: BaseException | None = None) -> None:
        self._value = value
        self._exc = exc

    async def result(self, timeout: float | None = None) -> object:
        if self._exc is not None:
            raise self._exc
        return self._value


class FakeArqPool:
    """Runs render/compose jobs in-process at enqueue time (eager), capturing any
    exception to re-raise from result() — mirrors arq's enqueue+await contract.
    `alive=False` simulates a render pool with no live worker (no health key)."""

    def __init__(self, fns, *, alive: bool = True):  # type: ignore[no-untyped-def]
        self._fns = fns
        self._alive = alive

    async def exists(self, key: str) -> int:
        return 1 if self._alive else 0

    async def enqueue_job(self, function, *args, _queue_name=None):  # type: ignore[no-untyped-def]
        try:
            value = await self._fns[function]({}, *args)
            return FakeArqJob(value=value)
        except Exception as exc:
            return FakeArqJob(exc=exc)
