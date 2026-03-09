from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Callable, TypeVar

T = TypeVar("T")


def call_with_retry(
    operation: Callable[[], T],
    max_retries: int = 2,
    base_delay_seconds: float = 1.0,
    is_retryable: Callable[[Exception], bool] | None = None,
) -> T:
    # Retry sync operation with exponential backoff until success or retry budget exhausted.
    attempt = 0
    delay = base_delay_seconds

    while True:
        try:
            return operation()
        except Exception as error:
            retryable = is_retryable(error) if is_retryable is not None else True
            if not retryable or attempt >= max_retries:
                raise
            time.sleep(delay)
            delay *= 2
            attempt += 1


def with_timeout(operation: Callable[[], T], timeout_seconds: float, component_name: str) -> T:
    # Run sync operation with hard timeout using a worker thread.
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(operation)
    try:
        return future.result(timeout=timeout_seconds)
    except FuturesTimeoutError as error:
        future.cancel()
        raise TimeoutError(f"{component_name} timed out after {timeout_seconds}s") from error
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


async def with_timeout_async(operation: Callable[[], T], timeout_seconds: float, component_name: str) -> T:
    # Run blocking operation in thread and enforce async timeout boundary.
    try:
        return await asyncio.wait_for(asyncio.to_thread(operation), timeout=timeout_seconds)
    except asyncio.TimeoutError as error:
        raise TimeoutError(f"{component_name} timed out after {timeout_seconds}s") from error
