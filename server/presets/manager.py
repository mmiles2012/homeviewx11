"""Preset save/load/apply backed by SQLite."""
from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

import aiosqlite

from server.models import Preset

if TYPE_CHECKING:
    from server.composition.engine import CompositionEngine

logger = logging.getLogger(__name__)


class PresetNotFoundError(Exception):
    pass


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug.strip("-")
    return slug


class PresetManager:
    def __init__(self, db_path: str, engine: "CompositionEngine") -> None:
        self._db_path = db_path
        self._engine = engine

    async def save_preset(self, name: str) -> Preset:
        """Capture current engine state as a named preset."""
        preset_id = _slugify(name)
        state = self._engine.get_state()
        cell_assignments: dict[str, str | None] = {
            str(c.index): c.source_id for c in state.cells
        }
        active_audio_cell = state.audio.active_cell

        async with aiosqlite.connect(self._db_path) as conn:
            await conn.execute(
                """
                INSERT INTO presets (id, name, layout_id, cell_assignments, active_audio_cell)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    layout_id=excluded.layout_id,
                    cell_assignments=excluded.cell_assignments,
                    active_audio_cell=excluded.active_audio_cell
                """,
                (
                    preset_id,
                    name,
                    state.layout_id,
                    json.dumps(cell_assignments),
                    active_audio_cell,
                ),
            )
            await conn.commit()

        return Preset(
            id=preset_id,
            name=name,
            layout_id=state.layout_id,
            cell_assignments=cell_assignments,
            active_audio_cell=active_audio_cell,
        )

    async def list_presets(self) -> list[Preset]:
        """Return all saved presets."""
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT id, name, layout_id, cell_assignments, active_audio_cell FROM presets"
            )
            rows = await cursor.fetchall()

        return [
            Preset(
                id=row["id"],
                name=row["name"],
                layout_id=row["layout_id"],
                cell_assignments=json.loads(row["cell_assignments"]),
                active_audio_cell=row["active_audio_cell"],
            )
            for row in rows
        ]

    async def get_preset(self, preset_id: str) -> Preset:
        """Fetch a single preset by id."""
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT id, name, layout_id, cell_assignments, active_audio_cell FROM presets WHERE id = ?",
                (preset_id,),
            )
            row = await cursor.fetchone()

        if row is None:
            raise PresetNotFoundError(f"Preset '{preset_id}' not found")

        return Preset(
            id=row["id"],
            name=row["name"],
            layout_id=row["layout_id"],
            cell_assignments=json.loads(row["cell_assignments"]),
            active_audio_cell=row["active_audio_cell"],
        )

    async def apply_preset(self, preset_id: str) -> None:
        """Restore engine state from a saved preset."""
        preset = await self.get_preset(preset_id)

        # 1. Switch layout
        await self._engine.set_layout(preset.layout_id)

        # 2. Assign sources per cell_assignments (skip missing sources)
        for cell_index_str, source_id in preset.cell_assignments.items():
            cell_index = int(cell_index_str)
            if source_id is None:
                try:
                    await self._engine.clear_cell(cell_index=cell_index)
                except Exception:
                    pass
            else:
                try:
                    await self._engine.assign_source(cell_index=cell_index, source_id=source_id)
                except Exception as exc:
                    logger.warning(
                        "Skipping source '%s' for cell %d: %s", source_id, cell_index, exc
                    )

        # 3. Restore active audio cell
        self._engine._active_audio_cell = preset.active_audio_cell
        self._engine._notify_state_change()

    async def delete_preset(self, preset_id: str) -> None:
        """Remove a preset from the DB."""
        async with aiosqlite.connect(self._db_path) as conn:
            cursor = await conn.execute("DELETE FROM presets WHERE id = ?", (preset_id,))
            await conn.commit()
            if cursor.rowcount == 0:
                raise PresetNotFoundError(f"Preset '{preset_id}' not found")
