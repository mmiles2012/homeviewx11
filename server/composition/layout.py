"""Layout loading, geometry computation, and transition logic."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

CellRole = Literal["hero", "side", "grid", "pip"]

# Priority order for keeping cells when shrinking (lower = higher priority)
_ROLE_PRIORITY: dict[str, int] = {"hero": 0, "side": 1, "grid": 2, "pip": 3}


class CellDef(BaseModel):
    """Proportional cell definition from a layout JSON file."""

    index: int
    role: CellRole
    x: float  # proportion [0, 1)
    y: float
    w: float  # proportion (0, 1]
    h: float


class Layout(BaseModel):
    """A named layout configuration."""

    id: str
    name: str
    gap_px: int = 0
    cells: list[CellDef] = []


@dataclass
class CellGeometry:
    """Pixel-precise geometry for a single cell."""

    cell_index: int
    x: int
    y: int
    width: int
    height: int


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LayoutNotFoundError(Exception):
    """Raised when a layout id is not found."""


# ---------------------------------------------------------------------------
# LayoutManager
# ---------------------------------------------------------------------------


class LayoutManager:
    """Loads layouts from JSON files and computes pixel geometry."""

    def __init__(self) -> None:
        self._layouts: dict[str, Layout] = {}

    def load_layouts(self, directory: str) -> None:
        """Load all *.json layout files from *directory*."""
        for path in sorted(Path(directory).glob("*.json")):
            with path.open() as f:
                data = json.load(f)
            layout = Layout.model_validate(data)
            self._layouts[layout.id] = layout

    def list_layouts(self) -> list[Layout]:
        """Return all loaded layouts ordered by id."""
        return sorted(self._layouts.values(), key=lambda l: l.id)

    def get_layout(self, layout_id: str) -> Layout:
        """Return a layout by id, or raise LayoutNotFoundError."""
        if layout_id not in self._layouts:
            raise LayoutNotFoundError(f"Layout '{layout_id}' not found")
        return self._layouts[layout_id]

    def compute_geometry(
        self, layout: Layout, display_width: int, display_height: int
    ) -> list[CellGeometry]:
        """Convert proportional cell definitions to pixel geometry.

        Gap pixels are distributed between adjacent cells.  Each cell's
        proportional rect is first scaled to display size, then the gap
        is subtracted from the *right* and *bottom* edges of every cell
        that is not already touching the display boundary.
        """
        gap = layout.gap_px
        result: list[CellGeometry] = []

        for cell in sorted(layout.cells, key=lambda c: c.index):
            # Raw pixel rect (proportional × display size)
            raw_x = round(cell.x * display_width)
            raw_y = round(cell.y * display_height)
            raw_w = round(cell.w * display_width)
            raw_h = round(cell.h * display_height)

            # Apply gap: shrink right/bottom if not at display edge
            right_edge = raw_x + raw_w
            bottom_edge = raw_y + raw_h

            actual_w = raw_w - (gap if right_edge < display_width else 0)
            actual_h = raw_h - (gap if bottom_edge < display_height else 0)

            result.append(
                CellGeometry(
                    cell_index=cell.index,
                    x=raw_x,
                    y=raw_y,
                    width=max(1, actual_w),
                    height=max(1, actual_h),
                )
            )

        return result

    def compute_transition(
        self,
        old_layout: Layout,
        new_layout: Layout,
        old_assignments: dict[int, str | None],
    ) -> dict[int, str | None]:
        """Compute new cell assignments when switching layouts.

        Rules (per PRD Section 5.2.3):
        1. hero → hero first
        2. side → side by position order
        3. remaining by role priority then alphabetical source id
        4. If fewer cells: drop lowest-priority cells
        5. New cells start empty (None)
        """
        old_cells = sorted(old_layout.cells, key=lambda c: c.index)
        new_cells = sorted(new_layout.cells, key=lambda c: c.index)

        # Build a list of (source_id, role) from old assignments, ordered by priority
        # hero > side > grid > pip, then by original index
        filled = [
            (old_assignments.get(c.index), c.role, c.index)
            for c in old_cells
            if old_assignments.get(c.index) is not None
        ]
        filled.sort(key=lambda t: (_ROLE_PRIORITY.get(t[1], 99), t[2]))

        sources_to_place = [src for src, _, _ in filled]

        # Place sources into new cells by role priority (hero first, then side, etc.)
        new_cells_by_priority = sorted(
            new_cells, key=lambda c: (_ROLE_PRIORITY.get(c.role, 99), c.index)
        )

        new_assignments: dict[int, str | None] = {c.index: None for c in new_cells}
        for i, cell in enumerate(new_cells_by_priority):
            if i < len(sources_to_place):
                new_assignments[cell.index] = sources_to_place[i]

        return new_assignments
