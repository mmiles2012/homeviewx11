"""Health monitor — crash detection, exponential backoff restart, crash-loop protection."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

logger = logging.getLogger(__name__)

_MAX_BACKOFF = 60
_MAX_CONSECUTIVE_CRASHES = 5
_STABLE_RESET_SECONDS = 300  # 5 minutes


def compute_backoff(consecutive_crashes: int) -> int:
    """Return backoff delay in seconds for the given crash count.

    Sequence: 1, 2, 4, 8, 16, 32, 60 (capped).
    """
    return min(2**consecutive_crashes, _MAX_BACKOFF)


@dataclass
class HealthEvent:
    """Emitted by the HealthMonitor on state transitions."""

    cell_index: int
    event_type: str  # "cell_restarting" | "cell_recovered" | "cell_failed"
    detail: str = ""


@dataclass
class CellHealthState:
    """Per-cell tracking of crashes and backoff."""

    cell_index: int
    consecutive_crashes: int = 0
    _last_crash_time: float = field(default_factory=time.monotonic, repr=False)

    @property
    def backoff_seconds(self) -> int:
        return compute_backoff(self.consecutive_crashes)

    @property
    def is_failed(self) -> bool:
        return self.consecutive_crashes >= _MAX_CONSECUTIVE_CRASHES

    def record_crash(self) -> None:
        self._last_crash_time = time.monotonic()
        self.consecutive_crashes += 1

    def record_recovery(self) -> None:
        """Reset consecutive crash count on a successful stable run."""
        self.consecutive_crashes = 0

    def maybe_reset_backoff(self) -> None:
        """Reset backoff if the cell has been stable for 5+ minutes."""
        if time.monotonic() - self._last_crash_time >= _STABLE_RESET_SECONDS:
            self.consecutive_crashes = 0


class _WatchableCell(Protocol):
    """Minimal protocol for a cell that can be watched by HealthMonitor."""

    cell_index: int
    url: str | None
    source_id: str | None

    async def restart(self) -> None: ...

    def simulate_crash(self) -> None: ...

    _process_exit_event: asyncio.Event


class HealthMonitor:
    """Watches cell processes and manages restarts with backoff."""

    def __init__(self, on_event: Callable[[HealthEvent], None] | None = None) -> None:
        self._on_event = on_event or (lambda e: None)
        self._states: dict[int, CellHealthState] = {}
        self._tasks: dict[int, asyncio.Task] = {}

    def watch(self, cell) -> None:
        """Start monitoring a cell for crashes."""
        idx = cell.cell_index
        if idx not in self._states:
            self._states[idx] = CellHealthState(cell_index=idx)
        task = asyncio.create_task(self._watch_cell(cell, self._states[idx]))
        self._tasks[idx] = task

    def unwatch(self, cell_index: int) -> None:
        """Stop watching a cell."""
        task = self._tasks.pop(cell_index, None)
        if task is not None:
            task.cancel()
        self._states.pop(cell_index, None)

    async def stop(self) -> None:
        """Cancel all monitoring tasks."""
        for task in list(self._tasks.values()):
            task.cancel()
        for task in list(self._tasks.values()):
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()

    async def _watch_cell(self, cell, state: CellHealthState) -> None:
        """Await cell crash, then restart with backoff."""
        while True:
            # Wait until the cell process signals an exit
            try:
                await asyncio.wait_for(cell._process_exit_event.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                state.maybe_reset_backoff()
                continue

            # Process exited — treat as crash
            state.record_crash()

            if state.is_failed:
                logger.error("Cell %d crash-looped; marking FAILED", cell.cell_index)
                self._on_event(
                    HealthEvent(
                        cell_index=cell.cell_index,
                        event_type="cell_failed",
                        detail=f"Crashed {state.consecutive_crashes} times",
                    )
                )
                return

            backoff = state.backoff_seconds
            logger.warning(
                "Cell %d crashed (count=%d); restarting in %ds",
                cell.cell_index,
                state.consecutive_crashes,
                backoff,
            )
            self._on_event(
                HealthEvent(
                    cell_index=cell.cell_index,
                    event_type="cell_restarting",
                    detail=f"backoff={backoff}s",
                )
            )

            if backoff > 0:
                await asyncio.sleep(backoff)

            try:
                await cell.restart()
                self._on_event(
                    HealthEvent(
                        cell_index=cell.cell_index,
                        event_type="cell_recovered",
                    )
                )
            except Exception as exc:
                logger.error("Cell %d restart failed: %s", cell.cell_index, exc)
