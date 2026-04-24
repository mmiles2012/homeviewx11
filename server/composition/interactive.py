"""Interactive mode manager — pauses geometry enforcement for one cell."""

from __future__ import annotations


class InteractiveConflictError(Exception):
    """Raised when interactive mode is already active on a different cell."""


class InteractiveManager:
    """Tracks which cell (if any) is in interactive mode."""

    def __init__(self) -> None:
        self._active_cell_index: int | None = None

    @property
    def active_cell_index(self) -> int | None:
        return self._active_cell_index

    def is_active(self) -> bool:
        return self._active_cell_index is not None

    def start(self, cell_index: int) -> None:
        """Enter interactive mode for the given cell.

        Raises InteractiveConflictError if another cell is already interactive.
        """
        if (
            self._active_cell_index is not None
            and self._active_cell_index != cell_index
        ):
            raise InteractiveConflictError(
                f"Interactive mode already active on cell {self._active_cell_index}"
            )
        self._active_cell_index = cell_index

    def stop(self) -> None:
        """Exit interactive mode."""
        self._active_cell_index = None
