"""Tests for display resolution detection."""

from unittest.mock import patch, MagicMock

from server.composition.display import detect_display_resolution


class TestDetectDisplayResolution:
    def test_parses_connected_display(self):
        """Returns width/height from xrandr --current output."""
        mock_output = (
            "Screen 0: minimum 8 x 8, current 1920 x 1080, maximum 32767 x 32767\n"
            "HDMI-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 527mm x 296mm\n"
            "   1920x1080     60.00*+\n"
        )
        mock_result = MagicMock(returncode=0, stdout=mock_output)
        with patch(
            "server.composition.display.subprocess.run", return_value=mock_result
        ):
            width, height = detect_display_resolution(display=":0")
        assert width == 1920
        assert height == 1080

    def test_falls_back_on_xrandr_failure(self):
        """Returns 1920x1080 fallback when xrandr exits non-zero."""
        mock_result = MagicMock(returncode=1, stdout="")
        with patch(
            "server.composition.display.subprocess.run", return_value=mock_result
        ):
            width, height = detect_display_resolution(display=":0")
        assert width == 1920
        assert height == 1080

    def test_falls_back_on_exception(self):
        """Returns 1920x1080 fallback when xrandr raises."""
        with patch(
            "server.composition.display.subprocess.run",
            side_effect=FileNotFoundError("xrandr not found"),
        ):
            width, height = detect_display_resolution(display=":0")
        assert width == 1920
        assert height == 1080

    def test_parses_4k_resolution(self):
        """Parses 4K resolution correctly."""
        mock_output = "HDMI-2 connected 3840x2160+0+0 (normal left inverted right x axis y axis) 600mm x 340mm\n"
        mock_result = MagicMock(returncode=0, stdout=mock_output)
        with patch(
            "server.composition.display.subprocess.run", return_value=mock_result
        ):
            width, height = detect_display_resolution(display=":1")
        assert width == 3840
        assert height == 2160
