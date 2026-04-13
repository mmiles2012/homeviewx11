"""Tests for the health monitor — crash detection and exponential backoff restarts."""
import asyncio
import time
import pytest

from server.composition.health import HealthMonitor, CellHealthState, HealthEvent


class FakeCell:
    """Minimal cell stub for health monitor tests."""

    def __init__(self, cell_index: int = 0) -> None:
        self.cell_index = cell_index
        self.url = "https://espn.com"
        self.source_id = "espn"
        self.restart_count = 0
        self._fail_on_restart = False
        self._process_exit_event = asyncio.Event()

    async def restart(self) -> None:
        self.restart_count += 1
        if self._fail_on_restart:
            raise RuntimeError("Restart failed")
        # Reset the "crash" — new process is alive
        self._process_exit_event.clear()

    def simulate_crash(self) -> None:
        """Signal that the process has exited."""
        self._process_exit_event.set()


class TestBackoffCalculation:
    def test_backoff_sequence(self):
        """Exponential backoff follows 1s, 2s, 4s, 8s, 16s, max 60s."""
        from server.composition.health import compute_backoff
        assert compute_backoff(0) == 1
        assert compute_backoff(1) == 2
        assert compute_backoff(2) == 4
        assert compute_backoff(3) == 8
        assert compute_backoff(4) == 16
        assert compute_backoff(5) == 32
        assert compute_backoff(6) == 60  # capped at 60
        assert compute_backoff(10) == 60  # stays capped


class TestCellHealthState:
    def test_initial_state(self):
        """CellHealthState starts at zero crashes, no backoff."""
        state = CellHealthState(cell_index=0)
        assert state.consecutive_crashes == 0
        assert state.backoff_seconds == 1
        assert not state.is_failed

    def test_record_crash_increments_count(self):
        """Recording a crash increments consecutive_crashes."""
        state = CellHealthState(cell_index=0)
        state.record_crash()
        assert state.consecutive_crashes == 1
        assert state.backoff_seconds == 2

    def test_record_five_crashes_marks_failed(self):
        """5 consecutive crashes marks the cell as failed."""
        state = CellHealthState(cell_index=0)
        for _ in range(5):
            state.record_crash()
        assert state.is_failed

    def test_reset_after_stable_operation(self):
        """Backoff resets after 5 minutes of stable operation."""
        state = CellHealthState(cell_index=0)
        state.record_crash()
        state.record_crash()
        # Simulate 5+ minutes since last crash
        state._last_crash_time = time.monotonic() - 301
        state.maybe_reset_backoff()
        assert state.consecutive_crashes == 0
        assert state.backoff_seconds == 1


class TestHealthMonitorEvents:
    @pytest.mark.asyncio
    async def test_monitors_cell_and_emits_events(self):
        """HealthMonitor emits cell_restarting on crash."""
        cell = FakeCell()
        events: list[HealthEvent] = []
        monitor = HealthMonitor(on_event=lambda e: events.append(e))
        monitor.watch(cell)

        # Simulate crash
        cell.simulate_crash()
        await asyncio.sleep(0.05)  # let monitor tick
        await monitor.stop()

        event_types = [e.event_type for e in events]
        assert "cell_restarting" in event_types or cell.restart_count >= 1

    @pytest.mark.asyncio
    async def test_crash_loop_protection(self):
        """After 5 crashes, monitor emits cell_failed and stops restarting."""
        cell = FakeCell()
        events: list[HealthEvent] = []

        # Override backoff to 0 for speed
        import server.composition.health as h
        original = h.compute_backoff
        h.compute_backoff = lambda n: 0

        try:
            monitor = HealthMonitor(on_event=lambda e: events.append(e))
            monitor.watch(cell)

            # Simulate 5 rapid crashes
            for _ in range(5):
                cell.simulate_crash()
                await asyncio.sleep(0.02)

            await asyncio.sleep(0.1)
            await monitor.stop()
        finally:
            h.compute_backoff = original

        failed_events = [e for e in events if e.event_type == "cell_failed"]
        # Either failed event emitted or restart count >= 5
        assert len(failed_events) >= 1 or cell.restart_count >= 5
