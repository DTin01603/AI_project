import pytest
import time

from research_agent.resilience import call_with_retry, with_timeout


def test_call_with_retry_succeeds_after_retry() -> None:
    state = {"count": 0}

    def _operation() -> str:
        state["count"] += 1
        if state["count"] < 2:
            raise RuntimeError("temporary")
        return "ok"

    result = call_with_retry(_operation, max_retries=2, base_delay_seconds=0)

    assert result == "ok"
    assert state["count"] == 2


def test_call_with_retry_raises_when_exhausted() -> None:
    def _operation() -> str:
        raise RuntimeError("always fail")

    with pytest.raises(RuntimeError):
        call_with_retry(_operation, max_retries=1, base_delay_seconds=0)


def test_with_timeout_raises_timeout_error() -> None:
    def _slow() -> str:
        import time

        time.sleep(0.05)
        return "done"

    with pytest.raises(TimeoutError):
        with_timeout(_slow, timeout_seconds=0.001, component_name="test_component")


def test_with_timeout_does_not_wait_for_slow_operation_completion() -> None:
    def _slow() -> str:
        time.sleep(0.2)
        return "done"

    started = time.perf_counter()
    with pytest.raises(TimeoutError):
        with_timeout(_slow, timeout_seconds=0.01, component_name="test_component")
    elapsed = time.perf_counter() - started

    assert elapsed < 0.12
