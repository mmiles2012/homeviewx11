"""Tests for server configuration."""
import os


def test_config_defaults():
    """Config loads with sensible defaults."""
    from server.config import get_config
    # Clear any env overrides and reset cache
    os.environ.pop("HOMEVIEW_MOCK", None)
    os.environ.pop("HOMEVIEW_PORT", None)
    os.environ.pop("HOMEVIEW_HOST", None)
    get_config.cache_clear()

    config = get_config()

    assert config.port == 8000
    assert config.host == "0.0.0.0"
    assert config.mock_mode is False


def test_config_mock_mode_from_env():
    """HOMEVIEW_MOCK=1 activates mock mode."""
    from server.config import get_config
    os.environ["HOMEVIEW_MOCK"] = "1"
    try:
        get_config.cache_clear()
        config = get_config()
        assert config.mock_mode is True
    finally:
        os.environ.pop("HOMEVIEW_MOCK", None)
        get_config.cache_clear()


def test_config_port_from_env():
    """HOMEVIEW_PORT overrides default port."""
    from server.config import get_config
    os.environ["HOMEVIEW_PORT"] = "9000"
    try:
        get_config.cache_clear()
        config = get_config()
        assert config.port == 9000
    finally:
        os.environ.pop("HOMEVIEW_PORT", None)
        get_config.cache_clear()


def test_config_has_required_fields():
    """Config has all required fields for the server."""
    from server.config import get_config
    config = get_config()

    assert hasattr(config, "host")
    assert hasattr(config, "port")
    assert hasattr(config, "mock_mode")
    assert hasattr(config, "db_path")
    assert hasattr(config, "profiles_dir")
    assert hasattr(config, "layouts_dir")
    assert hasattr(config, "chromium_binary")
    assert hasattr(config, "server_name")


def test_config_mock_display_resolution():
    """Mock mode provides a default display resolution."""
    from server.config import get_config
    os.environ["HOMEVIEW_MOCK"] = "1"
    try:
        get_config.cache_clear()
        config = get_config()
        assert config.mock_mode is True
        assert hasattr(config, "mock_display_width")
        assert hasattr(config, "mock_display_height")
        assert config.mock_display_width == 1920
        assert config.mock_display_height == 1080
    finally:
        os.environ.pop("HOMEVIEW_MOCK", None)
        get_config.cache_clear()
