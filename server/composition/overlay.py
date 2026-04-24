"""Pairing overlay — full-screen Chromium cell showing the pairing code on first boot."""

from __future__ import annotations

import logging

from server.composition.cell import Cell, ChromiumLauncher

logger = logging.getLogger(__name__)

# Sentinel cell_index that will not conflict with normal layout cells
_OVERLAY_CELL_INDEX = 9999


class PairingOverlay:
    """Single-instance overlay cell that shows the pairing code until paired."""

    def __init__(self, launcher: ChromiumLauncher, overlay_url: str) -> None:
        self._launcher = launcher
        self._overlay_url = overlay_url
        self._cell: Cell | None = None

    async def show(self) -> None:
        """Launch the overlay if not already showing."""
        if self._cell is not None:
            return
        cell = Cell(cell_index=_OVERLAY_CELL_INDEX, launcher=self._launcher)
        await cell.launch(url=self._overlay_url, source_id="__overlay__")
        self._cell = cell
        logger.info("Pairing overlay launched (pid=%s)", cell.pid)

    async def close(self) -> None:
        """Stop the overlay cell."""
        if self._cell is None:
            return
        await self._cell.stop()
        self._cell = None
        logger.info("Pairing overlay closed")

    @property
    def is_showing(self) -> bool:
        return self._cell is not None
