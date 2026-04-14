"""Tests for the window manager (mock implementation covers CI; X11 on hardware)."""
import pytest

from server.composition.window import MockWindowManager, create_window_manager, WindowNotFoundError


class TestMockWindowManager:
    @pytest.fixture
    def wm(self) -> MockWindowManager:
        return MockWindowManager()

    def test_find_window_by_pid_returns_window_id(self, wm):
        """Simulates finding a window; returns a positive integer id."""
        # Register a fake pid→window mapping
        wm.register_window(pid=1234, window_id=100)
        wid = wm.find_window_by_pid(1234, timeout=1.0)
        assert wid == 100

    def test_find_window_by_pid_timeout_returns_none(self, wm):
        """Returns None when no window is registered for that pid."""
        result = wm.find_window_by_pid(9999, timeout=0.0)
        assert result is None

    def test_set_geometry_records_state(self, wm):
        """set_geometry stores the applied geometry."""
        wm.register_window(pid=1, window_id=10)
        wm.set_geometry(10, x=0, y=0, width=960, height=540)
        geom = wm.get_geometry(10)
        assert geom == (0, 0, 960, 540)

    def test_remove_decorations_tracked(self, wm):
        """remove_decorations marks the window as decoration-free."""
        wm.register_window(pid=2, window_id=20)
        wm.remove_decorations(20)
        assert wm.has_decorations(20) is False

    def test_set_always_on_top_tracked(self, wm):
        """set_always_on_top records the state."""
        wm.register_window(pid=3, window_id=30)
        wm.set_always_on_top(30)
        assert wm.is_always_on_top(30) is True

    def test_close_window_removes_state(self, wm):
        """close_window removes the window from tracked state."""
        wm.register_window(pid=4, window_id=40)
        wm.close_window(40)
        assert wm.get_geometry(40) is None

    def test_get_geometry_unknown_window_returns_none(self, wm):
        """get_geometry returns None for unknown window ids."""
        assert wm.get_geometry(9999) is None

    def test_operations_on_unknown_window_raise(self, wm):
        """set_geometry on unknown window id raises WindowNotFoundError."""
        with pytest.raises(WindowNotFoundError):
            wm.set_geometry(9999, 0, 0, 100, 100)


class TestFactory:
    def test_create_mock_manager(self):
        """create_window_manager(mock_mode=True) returns MockWindowManager."""
        wm = create_window_manager(mock_mode=True)
        assert isinstance(wm, MockWindowManager)

    def test_create_real_manager_class(self):
        """create_window_manager(mock_mode=False) returns an X11WindowManager."""
        from server.composition.window import X11WindowManager
        wm = create_window_manager(mock_mode=False)
        assert isinstance(wm, X11WindowManager)
