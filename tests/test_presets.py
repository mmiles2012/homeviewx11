"""Tests for preset save/load/apply/delete."""

import pytest
from httpx import AsyncClient, ASGITransport

from server.db import init_db
from server.auth.pairing import PairingManager


@pytest.fixture
async def db_path(tmp_path) -> str:
    path = str(tmp_path / "test.db")
    await init_db(path)
    return path


@pytest.fixture
async def auth_token(db_path) -> str:
    mgr = PairingManager(db_path)
    code = await mgr.generate_pairing_code()
    token = await mgr.validate_code(code)
    return token


@pytest.fixture
async def api_client(db_path, auth_token):
    from server.main import create_app

    app = create_app(db_path=db_path, mock_mode=True)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=True),
        base_url="http://test",
        headers={"Authorization": f"Bearer {auth_token}"},
    ) as ac:
        async with app.router.lifespan_context(app):
            yield ac


class TestPresetManager:
    @pytest.mark.asyncio
    async def test_save_and_list_preset(self, db_path):
        """PresetManager.save_preset() captures engine state; list returns it."""
        from server.composition.engine import CompositionEngine
        from server.composition.layout import LayoutManager
        from server.composition.window import create_window_manager
        from server.composition.cell import create_chromium_launcher
        from server.sources.registry import SourceRegistry
        from server.config import get_config
        from server.presets.manager import PresetManager

        config = get_config()
        layout_manager = LayoutManager()
        layout_manager.load_layouts(config.layouts_dir)
        window_manager = create_window_manager(mock_mode=True)
        chromium_launcher = create_chromium_launcher(
            mock_mode=True, profiles_dir="/tmp", chromium_binary="chromium"
        )
        registry = SourceRegistry(db_path)
        engine = CompositionEngine(
            layout_manager=layout_manager,
            window_manager=window_manager,
            chromium_launcher=chromium_launcher,
            source_registry=registry,
        )
        await engine.start()

        mgr = PresetManager(db_path=db_path, engine=engine)
        preset = await mgr.save_preset("Living Room")
        assert preset.id == "living-room"
        assert preset.name == "Living Room"
        assert preset.layout_id == "single"

        presets = await mgr.list_presets()
        assert len(presets) == 1
        assert presets[0].id == "living-room"

        await engine.stop()

    @pytest.mark.asyncio
    async def test_apply_preset_restores_layout(self, db_path):
        """apply_preset() switches to the saved layout."""
        from server.composition.engine import CompositionEngine
        from server.composition.layout import LayoutManager
        from server.composition.window import create_window_manager
        from server.composition.cell import create_chromium_launcher
        from server.sources.registry import SourceRegistry
        from server.config import get_config
        from server.presets.manager import PresetManager

        config = get_config()
        layout_manager = LayoutManager()
        layout_manager.load_layouts(config.layouts_dir)
        window_manager = create_window_manager(mock_mode=True)
        chromium_launcher = create_chromium_launcher(
            mock_mode=True, profiles_dir="/tmp", chromium_binary="chromium"
        )
        registry = SourceRegistry(db_path)
        engine = CompositionEngine(
            layout_manager=layout_manager,
            window_manager=window_manager,
            chromium_launcher=chromium_launcher,
            source_registry=registry,
        )
        await engine.start()

        mgr = PresetManager(db_path=db_path, engine=engine)
        # Save preset in single layout
        await mgr.save_preset("Single View")

        # Switch to 2x2
        await engine.set_layout("2x2")
        assert engine.get_state().layout_id == "2x2"

        # Apply preset should restore single
        await mgr.apply_preset("single-view")
        assert engine.get_state().layout_id == "single"

        await engine.stop()

    @pytest.mark.asyncio
    async def test_delete_preset(self, db_path):
        """delete_preset() removes it from the DB."""
        from server.composition.engine import CompositionEngine
        from server.composition.layout import LayoutManager
        from server.composition.window import create_window_manager
        from server.composition.cell import create_chromium_launcher
        from server.sources.registry import SourceRegistry
        from server.config import get_config
        from server.presets.manager import PresetManager

        config = get_config()
        layout_manager = LayoutManager()
        layout_manager.load_layouts(config.layouts_dir)
        window_manager = create_window_manager(mock_mode=True)
        chromium_launcher = create_chromium_launcher(
            mock_mode=True, profiles_dir="/tmp", chromium_binary="chromium"
        )
        registry = SourceRegistry(db_path)
        engine = CompositionEngine(
            layout_manager=layout_manager,
            window_manager=window_manager,
            chromium_launcher=chromium_launcher,
            source_registry=registry,
        )
        await engine.start()

        mgr = PresetManager(db_path=db_path, engine=engine)
        await mgr.save_preset("My Setup")
        await mgr.delete_preset("my-setup")

        presets = await mgr.list_presets()
        assert len(presets) == 0

        await engine.stop()

    @pytest.mark.asyncio
    async def test_apply_unknown_preset_raises(self, db_path):
        """apply_preset() with unknown id raises PresetNotFoundError."""
        from server.composition.engine import CompositionEngine
        from server.composition.layout import LayoutManager
        from server.composition.window import create_window_manager
        from server.composition.cell import create_chromium_launcher
        from server.sources.registry import SourceRegistry
        from server.config import get_config
        from server.presets.manager import PresetManager, PresetNotFoundError

        config = get_config()
        layout_manager = LayoutManager()
        layout_manager.load_layouts(config.layouts_dir)
        window_manager = create_window_manager(mock_mode=True)
        chromium_launcher = create_chromium_launcher(
            mock_mode=True, profiles_dir="/tmp", chromium_binary="chromium"
        )
        registry = SourceRegistry(db_path)
        engine = CompositionEngine(
            layout_manager=layout_manager,
            window_manager=window_manager,
            chromium_launcher=chromium_launcher,
            source_registry=registry,
        )
        await engine.start()

        mgr = PresetManager(db_path=db_path, engine=engine)
        with pytest.raises(PresetNotFoundError):
            await mgr.apply_preset("does-not-exist")

        await engine.stop()

    @pytest.mark.asyncio
    async def test_apply_preset_skips_deleted_sources(self, db_path):
        """apply_preset() skips sources that no longer exist — does not raise."""
        from server.composition.engine import CompositionEngine
        from server.composition.layout import LayoutManager
        from server.composition.window import create_window_manager
        from server.composition.cell import create_chromium_launcher
        from server.sources.registry import SourceRegistry
        from server.config import get_config
        from server.presets.manager import PresetManager

        config = get_config()
        layout_manager = LayoutManager()
        layout_manager.load_layouts(config.layouts_dir)
        window_manager = create_window_manager(mock_mode=True)
        chromium_launcher = create_chromium_launcher(
            mock_mode=True, profiles_dir="/tmp", chromium_binary="chromium"
        )
        registry = SourceRegistry(db_path)
        engine = CompositionEngine(
            layout_manager=layout_manager,
            window_manager=window_manager,
            chromium_launcher=chromium_launcher,
            source_registry=registry,
        )
        await engine.start()

        # Assign espn to cell 0
        await engine.assign_source(cell_index=0, source_id="espn")

        mgr = PresetManager(db_path=db_path, engine=engine)
        await mgr.save_preset("ESPN Setup")

        # Now "delete" espn from the registry by directly removing (simulate using raw DB)
        import aiosqlite

        async with aiosqlite.connect(db_path) as conn:
            await conn.execute("DELETE FROM sources WHERE id = 'espn'")
            await conn.commit()

        # Apply should not raise — it skips the missing source
        await engine.set_layout("2x2")  # change layout so apply has something to do
        await mgr.apply_preset("espn-setup")
        # Layout is restored
        assert engine.get_state().layout_id == "single"

        await engine.stop()


class TestPresetAPI:
    @pytest.mark.asyncio
    async def test_list_presets_empty(self, api_client):
        """GET /api/v1/presets returns empty list initially."""
        r = await api_client.get("/api/v1/presets")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_save_preset(self, api_client):
        """POST /api/v1/presets saves current state."""
        r = await api_client.post("/api/v1/presets", json={"name": "My Setup"})
        assert r.status_code == 201
        data = r.json()
        assert data["id"] == "my-setup"
        assert data["name"] == "My Setup"

    @pytest.mark.asyncio
    async def test_apply_preset(self, api_client):
        """PUT /api/v1/presets/{id}/apply restores state."""
        # Save in single layout
        await api_client.post("/api/v1/presets", json={"name": "Single"})
        # Switch to 2x2
        await api_client.put("/api/v1/layout", json={"layout_id": "2x2"})
        # Apply preset
        r = await api_client.put("/api/v1/presets/single/apply")
        assert r.status_code == 200
        # Layout should be restored
        status = await api_client.get("/api/v1/status")
        assert status.json()["layout_id"] == "single"

    @pytest.mark.asyncio
    async def test_delete_preset(self, api_client):
        """DELETE /api/v1/presets/{id} removes the preset."""
        await api_client.post("/api/v1/presets", json={"name": "Temp"})
        r = await api_client.delete("/api/v1/presets/temp")
        assert r.status_code == 204
        presets = await api_client.get("/api/v1/presets")
        assert presets.json() == []

    @pytest.mark.asyncio
    async def test_apply_unknown_preset_returns_404(self, api_client):
        """PUT /api/v1/presets/{id}/apply with unknown id returns 404."""
        r = await api_client.put("/api/v1/presets/nonexistent/apply")
        assert r.status_code == 404
