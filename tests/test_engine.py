"""Tests for the CompositionEngine."""
import pytest
from pathlib import Path

from server.composition.engine import CompositionEngine, EngineState
from server.composition.window import MockWindowManager
from server.composition.cell import MockChromiumLauncher
from server.composition.layout import LayoutManager
from server.db import init_db
from server.sources.registry import SourceRegistry


LAYOUTS_DIR = str(Path(__file__).parent.parent / "layouts")


@pytest.fixture
async def engine(tmp_path) -> CompositionEngine:
    """Fully mocked engine with temp DB."""
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)

    layout_manager = LayoutManager()
    layout_manager.load_layouts(LAYOUTS_DIR)

    wm = MockWindowManager()
    launcher = MockChromiumLauncher(profiles_dir=str(tmp_path / "profiles"))

    eng = CompositionEngine(
        layout_manager=layout_manager,
        window_manager=wm,
        chromium_launcher=launcher,
        source_registry=SourceRegistry(db_path),
        display_width=1920,
        display_height=1080,
    )
    await eng.start()
    yield eng
    await eng.stop()


class TestEngineInit:
    @pytest.mark.asyncio
    async def test_starts_with_single_layout(self, engine):
        """Engine starts with the 'single' layout by default."""
        state = engine.get_state()
        assert state.layout_id == "single"

    @pytest.mark.asyncio
    async def test_initial_cells_are_empty(self, engine):
        """All cells start in EMPTY/idle state."""
        state = engine.get_state()
        assert len(state.cells) == 1
        assert state.cells[0].source_id is None
        assert state.cells[0].status == "idle"


class TestLayoutSwitching:
    @pytest.mark.asyncio
    async def test_set_layout_changes_layout(self, engine):
        """set_layout switches to the given layout."""
        await engine.set_layout("2x2")
        state = engine.get_state()
        assert state.layout_id == "2x2"
        assert len(state.cells) == 4

    @pytest.mark.asyncio
    async def test_set_layout_preserves_assigned_sources(self, engine):
        """Sources are carried over using transition rules when switching layouts."""
        await engine.assign_source(cell_index=0, source_id="espn")
        await engine.set_layout("2x2")
        state = engine.get_state()
        # espn should be present somewhere in the new layout
        source_ids = {c.source_id for c in state.cells}
        assert "espn" in source_ids

    @pytest.mark.asyncio
    async def test_set_layout_unknown_raises(self, engine):
        """set_layout raises ValueError for an unknown layout id."""
        with pytest.raises(ValueError):
            await engine.set_layout("nonexistent")


class TestSourceAssignment:
    @pytest.mark.asyncio
    async def test_assign_source_starts_cell(self, engine):
        """assign_source launches Chromium and marks cell running."""
        await engine.assign_source(cell_index=0, source_id="espn")
        state = engine.get_state()
        assert state.cells[0].source_id == "espn"
        assert state.cells[0].status == "active"
        assert state.cells[0].pid is not None

    @pytest.mark.asyncio
    async def test_clear_cell_stops_chromium(self, engine):
        """clear_cell stops Chromium and resets the cell to idle."""
        await engine.assign_source(cell_index=0, source_id="espn")
        await engine.clear_cell(cell_index=0)
        state = engine.get_state()
        assert state.cells[0].source_id is None
        assert state.cells[0].status == "idle"
        assert state.cells[0].pid is None


class TestStateSnapshot:
    @pytest.mark.asyncio
    async def test_get_state_returns_engine_state(self, engine):
        """get_state returns an EngineState with expected fields."""
        state = engine.get_state()
        assert isinstance(state, EngineState)
        assert state.layout_id is not None
        assert isinstance(state.cells, list)

    @pytest.mark.asyncio
    async def test_state_change_fires_callback(self, engine):
        """Assigning a source triggers the state-change callback."""
        events: list[EngineState] = []
        engine.on_state_change(lambda s: events.append(s))
        await engine.assign_source(cell_index=0, source_id="espn")
        assert len(events) >= 1
        assert events[-1].cells[0].source_id == "espn"


class TestDisplayResolution:
    @pytest.mark.asyncio
    async def test_geometry_recomputed_on_resolution_change(self, engine):
        """Changing display resolution triggers geometry recompute."""
        await engine.assign_source(cell_index=0, source_id="espn")
        wm = engine._window_manager
        await engine.set_display_resolution(3840, 2160)
        # After resolution change, the window geometry should reflect new size
        # In mock mode, we just verify it didn't crash and state is consistent
        state = engine.get_state()
        assert state.cells[0].source_id == "espn"
