"""X11 window management — abstract interface with real and mock implementations."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Optional


class WindowNotFoundError(Exception):
    """Raised when an operation targets an unknown window id."""


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class WindowManager(ABC):
    """Interface for X11 window operations."""

    @abstractmethod
    def find_window_by_pid(self, pid: int, timeout: float = 10.0) -> Optional[int]:
        """Return the window id for a process, or None if not found within timeout."""

    @abstractmethod
    def set_geometry(self, window_id: int, x: int, y: int, width: int, height: int) -> None:
        """Move and resize a window to the given pixel coordinates."""

    @abstractmethod
    def remove_decorations(self, window_id: int) -> None:
        """Remove window manager decorations (title bar, borders)."""

    @abstractmethod
    def set_always_on_top(self, window_id: int) -> None:
        """Request the window stay above all others."""

    @abstractmethod
    def get_geometry(self, window_id: int) -> Optional[tuple[int, int, int, int]]:
        """Return (x, y, width, height) for *window_id*, or None if unknown."""

    @abstractmethod
    def close_window(self, window_id: int) -> None:
        """Close and untrack a window."""


# ---------------------------------------------------------------------------
# Mock implementation
# ---------------------------------------------------------------------------


class MockWindowManager(WindowManager):
    """In-memory mock — suitable for CI and mock mode."""

    def __init__(self) -> None:
        self._pid_to_window: dict[int, int] = {}
        self._geometries: dict[int, tuple[int, int, int, int]] = {}
        self._no_decorations: set[int] = set()
        self._always_on_top: set[int] = set()

    def register_window(self, pid: int, window_id: int) -> None:
        """Test helper: register a fake pid→window_id mapping."""
        self._pid_to_window[pid] = window_id
        self._geometries[window_id] = (0, 0, 1920, 1080)  # default geometry

    def find_window_by_pid(self, pid: int, timeout: float = 10.0) -> Optional[int]:
        return self._pid_to_window.get(pid)

    def _require_window(self, window_id: int) -> None:
        if window_id not in self._geometries:
            raise WindowNotFoundError(f"Window {window_id} not found")

    def set_geometry(self, window_id: int, x: int, y: int, width: int, height: int) -> None:
        self._require_window(window_id)
        self._geometries[window_id] = (x, y, width, height)

    def remove_decorations(self, window_id: int) -> None:
        self._require_window(window_id)
        self._no_decorations.add(window_id)

    def set_always_on_top(self, window_id: int) -> None:
        self._require_window(window_id)
        self._always_on_top.add(window_id)

    def get_geometry(self, window_id: int) -> Optional[tuple[int, int, int, int]]:
        return self._geometries.get(window_id)

    def close_window(self, window_id: int) -> None:
        self._geometries.pop(window_id, None)
        self._no_decorations.discard(window_id)
        self._always_on_top.discard(window_id)
        # Remove pid mapping
        for pid, wid in list(self._pid_to_window.items()):
            if wid == window_id:
                del self._pid_to_window[pid]

    def has_decorations(self, window_id: int) -> bool:
        return window_id not in self._no_decorations

    def is_always_on_top(self, window_id: int) -> bool:
        return window_id in self._always_on_top


# ---------------------------------------------------------------------------
# X11 implementation (requires python-xlib and a running X server)
# ---------------------------------------------------------------------------


class X11WindowManager(WindowManager):
    """Real X11 window management via python-xlib."""

    _POLL_INTERVAL = 0.1  # seconds between polls when searching for a window

    def __init__(self, display_name: str = ":0") -> None:
        from Xlib import display as xdisplay, X, Xatom
        from Xlib.ext import randr  # noqa: F401 — ensure extension loaded

        self._display = xdisplay.Display(display_name)
        self._X = X
        self._Xatom = Xatom

    def _get_atom(self, name: str) -> int:
        return self._display.intern_atom(name)

    def _walk_tree(self, window) -> list:
        """Recursively collect all windows in the tree."""
        children = window.query_tree().children
        result = list(children)
        for child in children:
            result.extend(self._walk_tree(child))
        return result

    def find_window_by_pid(self, pid: int, timeout: float = 10.0) -> Optional[int]:
        """Poll the window tree for a window with _NET_WM_PID == pid."""
        net_wm_pid = self._get_atom("_NET_WM_PID")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            root = self._display.screen().root
            for win in self._walk_tree(root):
                try:
                    prop = win.get_full_property(net_wm_pid, self._X.AnyPropertyType)
                    if prop and prop.value[0] == pid:
                        return win.id
                except Exception:
                    continue
            time.sleep(self._POLL_INTERVAL)
        return None

    def set_geometry(self, window_id: int, x: int, y: int, width: int, height: int) -> None:
        win = self._display.create_resource_object("window", window_id)
        win.configure(x=x, y=y, width=width, height=height)
        self._display.sync()

    def remove_decorations(self, window_id: int) -> None:
        """Remove decorations via _MOTIF_WM_HINTS."""
        motif_hints = self._get_atom("_MOTIF_WM_HINTS")
        win = self._display.create_resource_object("window", window_id)
        # MWM_HINTS_DECORATIONS = 1<<1; value 0 = no decorations
        # Format: flags, functions, decorations, input_mode, status
        win.change_property(
            motif_hints,
            motif_hints,
            32,
            [2, 0, 0, 0, 0],  # flags=MWM_HINTS_DECORATIONS, decorations=0
        )
        self._display.sync()

    def set_always_on_top(self, window_id: int) -> None:
        net_wm_state = self._get_atom("_NET_WM_STATE")
        net_wm_state_above = self._get_atom("_NET_WM_STATE_ABOVE")
        win = self._display.create_resource_object("window", window_id)
        win.change_property(net_wm_state, self._Xatom.ATOM, 32, [net_wm_state_above])
        self._display.sync()

    def get_geometry(self, window_id: int) -> Optional[tuple[int, int, int, int]]:
        try:
            win = self._display.create_resource_object("window", window_id)
            geom = win.get_geometry()
            return (geom.x, geom.y, geom.width, geom.height)
        except Exception:
            return None

    def close_window(self, window_id: int) -> None:
        try:
            win = self._display.create_resource_object("window", window_id)
            win.destroy()
            self._display.sync()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_window_manager(mock_mode: bool, display_name: str = ":0") -> WindowManager:
    """Return the appropriate WindowManager for the current environment."""
    if mock_mode:
        return MockWindowManager()
    return X11WindowManager(display_name=display_name)
