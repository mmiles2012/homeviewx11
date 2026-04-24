"""Display resolution detection via xrandr."""

from __future__ import annotations

import logging
import re
import subprocess

logger = logging.getLogger(__name__)

_CONNECTED_RE = re.compile(r"(\d+)x(\d+)\+\d+\+\d+")


def detect_display_resolution(display: str = ":0") -> tuple[int, int]:
    """Detect the connected display resolution via xrandr.

    Returns (width, height). Falls back to 1920x1080 if detection fails.
    """
    try:
        result = subprocess.run(
            ["xrandr", "--current"],
            capture_output=True,
            text=True,
            timeout=5,
            env={"DISPLAY": display},
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if " connected" in line:
                    match = _CONNECTED_RE.search(line)
                    if match:
                        width, height = int(match.group(1)), int(match.group(2))
                        logger.info("Detected display resolution: %dx%d", width, height)
                        return width, height
    except Exception as exc:
        logger.warning("xrandr detection failed: %s", exc)

    logger.warning("Could not detect display resolution; falling back to 1920x1080")
    return 1920, 1080
