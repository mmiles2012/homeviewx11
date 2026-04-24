"""Tests for the audio router."""

import pytest

from server.audio.router import MockAudioRouter, create_audio_router


@pytest.fixture
async def router() -> MockAudioRouter:
    r = MockAudioRouter()
    await r.setup()
    return r


class TestMockAudioRouter:
    @pytest.mark.asyncio
    async def test_setup_initializes_sinks(self, router):
        """setup() prepares null sink and marks HDMI available."""
        assert router.get_hdmi_sink() is not None
        assert "homeview_mute" in router.get_null_sink()

    @pytest.mark.asyncio
    async def test_route_to_hdmi(self, router):
        """route_to_hdmi() registers a PID as routed to HDMI."""
        await router.route_to_hdmi(pid=1001)
        assert router.get_routing(1001) == "hdmi"

    @pytest.mark.asyncio
    async def test_route_to_mute(self, router):
        """route_to_mute() registers a PID as routed to null sink."""
        await router.route_to_mute(pid=1002)
        assert router.get_routing(1002) == "mute"

    @pytest.mark.asyncio
    async def test_set_active_cell_routes_active_to_hdmi(self, router):
        """set_active_cell routes the active pid to HDMI."""
        await router.set_active_cell(active_pid=100, all_pids=[100, 200, 300])
        assert router.get_routing(100) == "hdmi"

    @pytest.mark.asyncio
    async def test_set_active_cell_mutes_others(self, router):
        """set_active_cell routes all non-active pids to null sink."""
        await router.set_active_cell(active_pid=100, all_pids=[100, 200, 300])
        assert router.get_routing(200) == "mute"
        assert router.get_routing(300) == "mute"

    @pytest.mark.asyncio
    async def test_set_active_cell_none_mutes_all(self, router):
        """set_active_cell with active_pid=None routes all to mute."""
        await router.set_active_cell(active_pid=None, all_pids=[100, 200])
        assert router.get_routing(100) == "mute"
        assert router.get_routing(200) == "mute"

    @pytest.mark.asyncio
    async def test_inject_sink_input_event(self, router):
        """inject_sink_input_event simulates a new sink-input arriving for a pid."""
        # Pre-register pid as active so the injection routes it to hdmi
        await router.route_to_hdmi(pid=555)
        router.inject_sink_input_event(555)
        assert router.get_routing(555) == "hdmi"

    @pytest.mark.asyncio
    async def test_cleanup_idempotent(self, router):
        """cleanup() can be called multiple times without error."""
        await router.cleanup()
        await router.cleanup()  # should not raise

    @pytest.mark.asyncio
    async def test_get_routing_unknown_pid_returns_none(self, router):
        """get_routing returns None for unknown PIDs."""
        assert router.get_routing(99999) is None


class TestAudioRouterFactory:
    def test_factory_mock_mode(self):
        """create_audio_router(mock_mode=True) returns MockAudioRouter."""
        router = create_audio_router(mock_mode=True)
        assert isinstance(router, MockAudioRouter)

    def test_factory_real_mode_class(self):
        """create_audio_router(mock_mode=False) returns PulseAudioRouter."""
        from server.audio.router import PulseAudioRouter

        router = create_audio_router(mock_mode=False)
        assert isinstance(router, PulseAudioRouter)
