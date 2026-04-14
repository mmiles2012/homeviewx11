"""Composition engine — orchestrates cells, layouts, window placement, and state."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable

from server.audio.router import AudioRouter
from server.composition.cell import Cell, CellStatus, ChromiumLauncher
from server.composition.health import HealthMonitor
from server.composition.interactive import InteractiveManager
from server.composition.layout import LayoutManager, LayoutNotFoundError
from server.composition.window import WindowManager
from server.models import CellState, AudioState
from server.sources.registry import SourceRegistry

logger = logging.getLogger(__name__)

_GEOMETRY_ENFORCE_INTERVAL = 5.0  # seconds


@dataclass
class EngineState:
    """Snapshot of engine state for API responses and WebSocket events."""

    layout_id: str | None
    cells: list[CellState]
    audio: AudioState = field(default_factory=AudioState)
    mock_mode: bool = False


class CompositionEngine:
    """Central coordinator: manages cells, layouts, window placement."""

    def __init__(
        self,
        layout_manager: LayoutManager,
        window_manager: WindowManager,
        chromium_launcher: ChromiumLauncher,
        source_registry: SourceRegistry,
        audio_router: AudioRouter | None = None,
        display_width: int = 1920,
        display_height: int = 1080,
        default_layout_id: str = "single",
    ) -> None:
        self._layout_manager = layout_manager
        self._window_manager = window_manager
        self._chromium_launcher = chromium_launcher
        self._source_registry = source_registry
        self._audio_router = audio_router
        self._display_width = display_width
        self._display_height = display_height
        self._default_layout_id = default_layout_id

        self._layout_id: str | None = None
        self._cells: list[Cell] = []
        self._active_audio_cell: int | None = None
        self._state_callbacks: list[Callable[[EngineState], None]] = []
        self._enforce_task: asyncio.Task | None = None
        self.interactive = InteractiveManager()
        self._health_monitor = HealthMonitor()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Initialize with the default layout."""
        await self.set_layout(self._default_layout_id)
        self._enforce_task = asyncio.create_task(self._geometry_enforcer())

    async def stop(self) -> None:
        """Stop all cells and cancel background tasks."""
        await self._health_monitor.stop()
        if self._enforce_task is not None:
            self._enforce_task.cancel()
            try:
                await self._enforce_task
            except asyncio.CancelledError:
                pass
            self._enforce_task = None
        for cell in self._cells:
            await cell.stop()
        self._cells = []

    # ------------------------------------------------------------------
    # Layout management
    # ------------------------------------------------------------------

    async def set_layout(self, layout_id: str) -> None:
        """Switch to the given layout, preserving source assignments."""
        try:
            new_layout = self._layout_manager.get_layout(layout_id)
        except LayoutNotFoundError:
            raise ValueError(f"Unknown layout: {layout_id!r}")

        # Compute transition from old layout
        old_assignments: dict[int, str | None] = {}
        if self._layout_id is not None:
            try:
                old_layout = self._layout_manager.get_layout(self._layout_id)
                old_assignments = {
                    c.cell_index: c.source_id for c in self._cells
                }
                new_assignments = self._layout_manager.compute_transition(
                    old_layout, new_layout, old_assignments
                )
            except Exception as exc:
                logger.warning("compute_transition failed: %s", exc)
                new_assignments = {c.index: None for c in new_layout.cells}
        else:
            new_assignments = {c.index: None for c in new_layout.cells}

        # Stop all existing cells
        for cell in self._cells:
            await cell.stop()

        # Build new cell list
        self._layout_id = layout_id
        self._cells = [
            Cell(cell_index=c.index, launcher=self._chromium_launcher)
            for c in sorted(new_layout.cells, key=lambda x: x.index)
        ]

        # Re-launch cells that had sources in the transition
        for cell in self._cells:
            src = new_assignments.get(cell.cell_index)
            if src is not None:
                try:
                    source = await self._source_registry.get_source(src)
                    await cell.launch(url=source.url, source_id=src)
                    await self._place_window(cell)
                except Exception as exc:
                    logger.warning("Failed to relaunch cell %d: %s", cell.cell_index, exc)

        self._notify_state_change()

    # ------------------------------------------------------------------
    # Cell operations
    # ------------------------------------------------------------------

    async def assign_source(self, cell_index: int, source_id: str) -> None:
        """Launch (or replace) a source in the given cell."""
        cell = self._get_cell(cell_index)

        # Stop existing process if running
        if cell.status != CellStatus.EMPTY:
            self._health_monitor.unwatch(cell.cell_index)
            await cell.stop()

        source = await self._source_registry.get_source(source_id)
        await cell.launch(url=source.url, source_id=source_id)
        await self._place_window(cell)
        self._health_monitor.watch(cell)

        # Route audio if this cell is the active audio cell
        if self._audio_router and self._active_audio_cell == cell_index and cell.pid:
            all_pids = [c.pid for c in self._cells if c.pid is not None]
            await self._audio_router.set_active_cell(cell.pid, all_pids)

        self._notify_state_change()

    async def clear_cell(self, cell_index: int) -> None:
        """Stop the Chromium process in the given cell."""
        cell = self._get_cell(cell_index)
        self._health_monitor.unwatch(cell.cell_index)
        await cell.stop()
        self._notify_state_change()

    async def set_display_resolution(self, width: int, height: int) -> None:
        """Update display resolution and re-apply geometry to all running cells."""
        self._display_width = width
        self._display_height = height
        for cell in self._cells:
            if cell.status == CellStatus.RUNNING:
                await self._place_window(cell)
        self._notify_state_change()

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def get_state(self) -> EngineState:
        """Return a snapshot of current engine state."""
        cells = [
            CellState(
                index=c.cell_index,
                source_id=c.source_id,
                status="active" if c.status == CellStatus.RUNNING else "idle",
                pid=c.pid,
            )
            for c in self._cells
        ]
        return EngineState(
            layout_id=self._layout_id,
            cells=cells,
            audio=AudioState(active_cell=self._active_audio_cell),
        )

    def on_state_change(self, callback: Callable[[EngineState], None]) -> None:
        """Register a callback that fires on any state change."""
        self._state_callbacks.append(callback)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_cell(self, cell_index: int) -> Cell:
        for cell in self._cells:
            if cell.cell_index == cell_index:
                return cell
        raise ValueError(f"Cell index {cell_index} not found in current layout")

    async def _place_window(self, cell: Cell) -> None:
        """Find the Chromium window for a cell and apply geometry."""
        if cell.pid is None:
            return
        if self._layout_id is None:
            return

        layout = self._layout_manager.get_layout(self._layout_id)
        geometries = self._layout_manager.compute_geometry(
            layout, self._display_width, self._display_height
        )
        geom = next((g for g in geometries if g.cell_index == cell.cell_index), None)
        if geom is None:
            return

        window_id = self._window_manager.find_window_by_pid(cell.pid, timeout=5.0)
        if window_id is None:
            logger.warning("Could not find window for cell %d (pid %d)", cell.cell_index, cell.pid)
            return

        self._window_manager.set_geometry(window_id, geom.x, geom.y, geom.width, geom.height)
        self._window_manager.remove_decorations(window_id)
        self._window_manager.set_always_on_top(window_id)

    def _notify_state_change(self) -> None:
        state = self.get_state()
        for cb in self._state_callbacks:
            try:
                cb(state)
            except Exception as exc:
                logger.warning("State callback raised: %s", exc)

    async def _geometry_enforcer(self) -> None:
        """Background task: re-apply geometry to running cells every 5s."""
        while True:
            await asyncio.sleep(_GEOMETRY_ENFORCE_INTERVAL)
            for cell in self._cells:
                if cell.status == CellStatus.RUNNING:
                    # Skip the cell that is currently in interactive mode
                    if self.interactive.active_cell_index == cell.cell_index:
                        continue
                    try:
                        await self._place_window(cell)
                    except Exception as exc:
                        logger.warning("Geometry enforcement failed for cell %d: %s", cell.cell_index, exc)
