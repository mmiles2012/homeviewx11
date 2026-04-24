"""Tests for the Cell class and Chromium process lifecycle."""

import pytest

from server.composition.cell import (
    Cell,
    CellStatus,
    MockChromiumLauncher,
    create_chromium_launcher,
)


@pytest.fixture
def mock_launcher(tmp_path) -> MockChromiumLauncher:
    return MockChromiumLauncher(profiles_dir=str(tmp_path / "profiles"))


@pytest.fixture
def cell(tmp_path) -> Cell:
    launcher = MockChromiumLauncher(profiles_dir=str(tmp_path / "profiles"))
    return Cell(cell_index=0, launcher=launcher)


class TestCellLifecycle:
    @pytest.mark.asyncio
    async def test_initial_status_is_empty(self, cell):
        """New cell starts in EMPTY status."""
        assert cell.status == CellStatus.EMPTY
        assert cell.pid is None

    @pytest.mark.asyncio
    async def test_launch_transitions_to_running(self, cell):
        """launch() transitions cell to RUNNING status."""
        await cell.launch(url="https://espn.com", source_id="espn")
        assert cell.status == CellStatus.RUNNING
        assert cell.source_id == "espn"
        assert cell.url == "https://espn.com"
        assert cell.pid is not None

    @pytest.mark.asyncio
    async def test_stop_transitions_to_empty(self, cell):
        """stop() terminates process and resets cell to EMPTY."""
        await cell.launch(url="https://espn.com", source_id="espn")
        await cell.stop()
        assert cell.status == CellStatus.EMPTY
        assert cell.pid is None
        assert cell.source_id is None

    @pytest.mark.asyncio
    async def test_restart_keeps_same_url(self, cell):
        """restart() stops and relaunches with the same URL."""
        await cell.launch(url="https://espn.com", source_id="espn")
        await cell.restart()
        assert cell.status == CellStatus.RUNNING
        assert cell.url == "https://espn.com"
        assert cell.source_id == "espn"

    @pytest.mark.asyncio
    async def test_stop_when_empty_is_noop(self, cell):
        """Stopping an already-empty cell does not raise."""
        await cell.stop()  # should not raise
        assert cell.status == CellStatus.EMPTY

    @pytest.mark.asyncio
    async def test_launch_uses_isolated_profile_dir(self, cell):
        """Each cell uses a separate --user-data-dir profile."""
        await cell.launch(url="https://espn.com", source_id="espn")
        launch_args = cell.launcher.last_launch_args
        profile_args = [a for a in launch_args if "--user-data-dir" in a]
        assert len(profile_args) == 1
        assert "cell-0" in profile_args[0]

    @pytest.mark.asyncio
    async def test_launch_uses_app_flag_not_kiosk(self, cell):
        """Chromium is launched with --app flag, never --kiosk."""
        await cell.launch(url="https://espn.com", source_id="espn")
        launch_args = cell.launcher.last_launch_args
        app_args = [a for a in launch_args if a.startswith("--app=")]
        kiosk_args = [a for a in launch_args if "--kiosk" in a]
        assert len(app_args) == 1
        assert len(kiosk_args) == 0


class TestChromiumLauncherFactory:
    def test_factory_mock_mode(self, tmp_path):
        """create_chromium_launcher(mock_mode=True) returns MockChromiumLauncher."""
        launcher = create_chromium_launcher(
            mock_mode=True,
            profiles_dir=str(tmp_path),
            chromium_binary="chromium-browser",
        )
        assert isinstance(launcher, MockChromiumLauncher)

    def test_factory_real_mode_class(self, tmp_path):
        """create_chromium_launcher(mock_mode=False) returns RealChromiumLauncher."""
        from server.composition.cell import RealChromiumLauncher

        launcher = create_chromium_launcher(
            mock_mode=False,
            profiles_dir=str(tmp_path),
            chromium_binary="chromium-browser",
        )
        assert isinstance(launcher, RealChromiumLauncher)
