"""Audio router — PulseAudio/PipeWire routing via pactl."""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)

_NULL_SINK_NAME = "homeview_mute"
_NULL_SINK_MODULE = "module-null-sink"
_MOCK_HDMI_SINK = "alsa_output.hdmi.mock"


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class AudioRouter(ABC):
    """Interface for PulseAudio/PipeWire audio routing."""

    @abstractmethod
    async def setup(self) -> None:
        """Initialize: create null sink, identify HDMI sink."""

    @abstractmethod
    async def route_to_hdmi(self, pid: int) -> None:
        """Route all sink-inputs for *pid* to the HDMI sink."""

    @abstractmethod
    async def route_to_mute(self, pid: int) -> None:
        """Route all sink-inputs for *pid* to the null (mute) sink."""

    @abstractmethod
    async def set_active_cell(
        self, active_pid: int | None, all_pids: list[int]
    ) -> None:
        """Route the active cell to HDMI; route all others to mute."""

    @abstractmethod
    async def cleanup(self) -> None:
        """Tear down: cancel subscribe task, unload null sink."""

    @abstractmethod
    def get_hdmi_sink(self) -> str | None:
        """Return the detected HDMI sink name, or None if not found."""

    @abstractmethod
    def get_null_sink(self) -> str:
        """Return the name of the null/mute sink."""


# ---------------------------------------------------------------------------
# Mock implementation
# ---------------------------------------------------------------------------


class MockAudioRouter(AudioRouter):
    """In-memory mock — suitable for CI and mock mode."""

    def __init__(self) -> None:
        self._routing: dict[int, str] = {}
        self._hdmi_sink: str | None = None
        self._cleaned_up = False
        self._event_log: list[int] = []

    async def setup(self) -> None:
        self._hdmi_sink = _MOCK_HDMI_SINK
        self._cleaned_up = False

    async def route_to_hdmi(self, pid: int) -> None:
        self._routing[pid] = "hdmi"

    async def route_to_mute(self, pid: int) -> None:
        self._routing[pid] = "mute"

    async def set_active_cell(
        self, active_pid: int | None, all_pids: list[int]
    ) -> None:
        for pid in all_pids:
            if pid == active_pid:
                await self.route_to_hdmi(pid)
            else:
                await self.route_to_mute(pid)

    async def cleanup(self) -> None:
        self._cleaned_up = True

    def get_hdmi_sink(self) -> str | None:
        return self._hdmi_sink

    def get_null_sink(self) -> str:
        return _NULL_SINK_NAME

    def get_routing(self, pid: int) -> str | None:
        """Test helper: return the current routing status for *pid*."""
        return self._routing.get(pid)

    def inject_sink_input_event(self, pid: int) -> None:
        """Test helper: simulate a 'new sink-input' event for *pid*."""
        self._event_log.append(pid)
        # If we already know what this PID's routing should be, re-apply it
        existing = self._routing.get(pid)
        if existing:
            self._routing[pid] = existing


# ---------------------------------------------------------------------------
# PulseAudio/PipeWire real implementation
# ---------------------------------------------------------------------------


class PulseAudioRouter(AudioRouter):
    """Routes audio via pactl subprocess commands.

    Works with both PulseAudio and PipeWire (pipewire-pulse compatibility layer).
    """

    def __init__(self) -> None:
        self._hdmi_sink: str | None = None
        self._null_sink_module_id: int | None = None
        self._subscribe_task: asyncio.Task | None = None

    async def setup(self) -> None:
        """Load null sink module and detect HDMI output."""
        # Load null sink for muting
        result = await self._run_pactl(
            "load-module", _NULL_SINK_MODULE,
            f"sink_name={_NULL_SINK_NAME}",
            "sink_properties=device.description=HomeView_Mute",
        )
        if result.strip().isdigit():
            self._null_sink_module_id = int(result.strip())

        # Find HDMI sink
        self._hdmi_sink = await self._find_hdmi_sink()

        # Start subscribe task for real-time sink-input events
        self._subscribe_task = asyncio.create_task(self._subscribe_loop())

    async def route_to_hdmi(self, pid: int) -> None:
        if self._hdmi_sink is None:
            logger.warning("No HDMI sink found; cannot route pid %d", pid)
            return
        for si_id in await self._find_sink_inputs_for_pid(pid):
            await self._run_pactl("move-sink-input", str(si_id), self._hdmi_sink)

    async def route_to_mute(self, pid: int) -> None:
        for si_id in await self._find_sink_inputs_for_pid(pid):
            await self._run_pactl("move-sink-input", str(si_id), _NULL_SINK_NAME)

    async def set_active_cell(
        self, active_pid: int | None, all_pids: list[int]
    ) -> None:
        for pid in all_pids:
            if pid == active_pid:
                await self.route_to_hdmi(pid)
            else:
                await self.route_to_mute(pid)

    async def cleanup(self) -> None:
        if self._subscribe_task is not None:
            self._subscribe_task.cancel()
            try:
                await self._subscribe_task
            except asyncio.CancelledError:
                pass
            self._subscribe_task = None

        if self._null_sink_module_id is not None:
            await self._run_pactl("unload-module", str(self._null_sink_module_id))
            self._null_sink_module_id = None

    def get_hdmi_sink(self) -> str | None:
        return self._hdmi_sink

    def get_null_sink(self) -> str:
        return _NULL_SINK_NAME

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_pactl(self, *args: str) -> str:
        proc = await asyncio.create_subprocess_exec(
            "pactl", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.warning("pactl %s failed: %s", args, stderr.decode())
        return stdout.decode().strip()

    async def _find_hdmi_sink(self) -> str | None:
        """Parse `pactl list sinks short` to find the first HDMI sink."""
        output = await self._run_pactl("list", "sinks", "short")
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                name = parts[1]
                if "hdmi" in name.lower() or "iec958" in name.lower():
                    return name
        logger.warning("No HDMI sink found in pactl output")
        return None

    async def _find_sink_inputs_for_pid(self, pid: int) -> list[int]:
        """Return all sink-input IDs belonging to *pid*."""
        output = await self._run_pactl("list", "sink-inputs")
        results: list[int] = []
        current_id: int | None = None
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("Sink Input #"):
                current_id = int(line.split("#")[1])
            elif "application.process.id" in line and current_id is not None:
                # Format: application.process.id = "1234"
                try:
                    found_pid = int(line.split("=")[1].strip().strip('"'))
                    if found_pid == pid:
                        results.append(current_id)
                except (ValueError, IndexError):
                    pass
        return results

    async def _subscribe_loop(self) -> None:
        """Background task: parse `pactl subscribe` for new sink-input events."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "pactl", "subscribe",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            assert proc.stdout is not None
            async for line in proc.stdout:
                text = line.decode().strip()
                # Parse: "Event 'new' on sink-input #N"
                if "new" in text and "sink-input" in text:
                    try:
                        si_id = int(text.split("#")[-1])
                        logger.debug("New sink-input #%d detected", si_id)
                    except (ValueError, IndexError):
                        pass  # ignore malformed lines
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("pactl subscribe loop error: %s", exc)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_audio_router(mock_mode: bool) -> AudioRouter:
    """Return the appropriate AudioRouter for the current environment."""
    if mock_mode:
        return MockAudioRouter()
    return PulseAudioRouter()
