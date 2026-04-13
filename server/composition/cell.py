"""Cell class — wraps a Chromium subprocess with lifecycle management."""
from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Optional


class CellStatus(Enum):
    EMPTY = "empty"
    STARTING = "starting"
    RUNNING = "running"
    RESTARTING = "restarting"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Chromium launcher abstraction
# ---------------------------------------------------------------------------


class ChromiumLauncher(ABC):
    """Interface for launching a Chromium process."""

    @abstractmethod
    async def launch(self, url: str, cell_index: int) -> asyncio.subprocess.Process:
        """Start Chromium and return the process handle."""

    @property
    @abstractmethod
    def last_launch_args(self) -> list[str]:
        """Return the last set of CLI args used to launch Chromium."""


# Chromium flags per PRD Section 5.1.1 (--app mode, NOT --kiosk)
_BASE_FLAGS = [
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-translate",
    "--disable-features=TranslateUI",
    "--disable-infobars",
    "--noerrdialogs",
    "--disable-session-crashed-bubble",
    "--autoplay-policy=no-user-gesture-required",
]


class RealChromiumLauncher(ChromiumLauncher):
    """Launches real Chromium subprocesses."""

    def __init__(self, profiles_dir: str, chromium_binary: str) -> None:
        self._profiles_dir = profiles_dir
        self._binary = chromium_binary
        self._last_args: list[str] = []

    async def launch(self, url: str, cell_index: int) -> asyncio.subprocess.Process:
        profile = str(Path(self._profiles_dir) / f"cell-{cell_index}")
        args = [
            self._binary,
            f"--app={url}",
            f"--user-data-dir={profile}",
        ] + _BASE_FLAGS
        self._last_args = args
        env = {**os.environ}
        return await asyncio.create_subprocess_exec(
            *args,
            env=env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

    @property
    def last_launch_args(self) -> list[str]:
        return self._last_args


class _MockProcess:
    """Minimal asyncio.subprocess.Process stub for testing."""

    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.returncode: int | None = None

    async def wait(self) -> int:
        return 0

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.returncode = -9


class MockChromiumLauncher(ChromiumLauncher):
    """Fake launcher — returns mock process objects without spawning real processes."""

    def __init__(self, profiles_dir: str) -> None:
        self._profiles_dir = profiles_dir
        self._next_pid = 10000
        self._last_args: list[str] = []

    async def launch(self, url: str, cell_index: int) -> asyncio.subprocess.Process:
        profile = str(Path(self._profiles_dir) / f"cell-{cell_index}")
        args = [
            "chromium-browser",
            f"--app={url}",
            f"--user-data-dir={profile}",
        ] + _BASE_FLAGS
        self._last_args = args
        pid = self._next_pid
        self._next_pid += 1
        return _MockProcess(pid)  # type: ignore[return-value]

    @property
    def last_launch_args(self) -> list[str]:
        return self._last_args


def create_chromium_launcher(
    mock_mode: bool, profiles_dir: str, chromium_binary: str
) -> ChromiumLauncher:
    """Return the appropriate Chromium launcher for the current environment."""
    if mock_mode:
        return MockChromiumLauncher(profiles_dir=profiles_dir)
    return RealChromiumLauncher(profiles_dir=profiles_dir, chromium_binary=chromium_binary)


# ---------------------------------------------------------------------------
# Cell
# ---------------------------------------------------------------------------


class Cell:
    """Manages one Chromium process for a single display cell."""

    def __init__(self, cell_index: int, launcher: ChromiumLauncher) -> None:
        self.cell_index = cell_index
        self.launcher = launcher
        self.source_id: str | None = None
        self.url: str | None = None
        self._process: Optional[asyncio.subprocess.Process] = None
        self._status = CellStatus.EMPTY

    @property
    def status(self) -> CellStatus:
        return self._status

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process is not None else None

    async def launch(self, url: str, source_id: str) -> None:
        """Start Chromium for this cell."""
        self._status = CellStatus.STARTING
        self._process = await self.launcher.launch(url=url, cell_index=self.cell_index)
        self.url = url
        self.source_id = source_id
        self._status = CellStatus.RUNNING

    async def stop(self) -> None:
        """Terminate the Chromium process and reset state."""
        if self._process is not None:
            try:
                self._process.terminate()
            except Exception:
                pass
            self._process = None
        self.url = None
        self.source_id = None
        self._status = CellStatus.EMPTY

    async def restart(self) -> None:
        """Stop and relaunch with the same URL."""
        url = self.url
        source_id = self.source_id
        if url is None or source_id is None:
            return
        self._status = CellStatus.RESTARTING
        await self.stop()
        await self.launch(url=url, source_id=source_id)
