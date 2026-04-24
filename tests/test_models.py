"""Tests for Pydantic domain models."""

import pytest
from pydantic import ValidationError

from server.models import (
    Source,
    SourceCreate,
    SourceUpdate,
    Preset,
    PresetCreate,
    CellState,
    AudioState,
    ServerStatus,
    PairingRequest,
    PairingResponse,
    ErrorResponse,
)


class TestSource:
    def test_source_valid(self):
        """Source model accepts valid data."""
        source = Source(
            id="espn",
            name="ESPN",
            type="streaming",
            url="https://espn.com",
            icon_url="https://espn.com/icon.png",
            requires_widevine=False,
        )
        assert source.id == "espn"
        assert source.name == "ESPN"
        assert source.type == "streaming"

    def test_source_requires_id_name_type_url(self):
        """Source model requires id, name, type, url."""
        with pytest.raises(ValidationError):
            Source(name="ESPN", type="streaming", url="https://espn.com")  # missing id

    def test_source_type_must_be_streaming_or_url(self):
        """Source type must be 'streaming' or 'url'."""
        with pytest.raises(ValidationError):
            Source(id="x", name="X", type="invalid", url="https://x.com")

    def test_source_create_without_id(self):
        """SourceCreate does not require id — it's assigned on creation."""
        sc = SourceCreate(name="My Stream", type="url", url="https://example.com")
        assert sc.name == "My Stream"

    def test_source_update_all_optional(self):
        """SourceUpdate allows partial updates."""
        su = SourceUpdate(name="New Name")
        assert su.name == "New Name"
        assert su.url is None


class TestPreset:
    def test_preset_valid(self):
        """Preset model accepts valid data."""
        preset = Preset(
            id="weekend",
            name="Weekend",
            layout_id="2x2",
            cell_assignments={"0": "espn", "1": "prime"},
            active_audio_cell=0,
        )
        assert preset.id == "weekend"
        assert preset.layout_id == "2x2"

    def test_preset_create_no_id(self):
        """PresetCreate does not require id."""
        pc = PresetCreate(
            name="Sports",
            layout_id="1x1",
            cell_assignments={"0": "espn"},
            active_audio_cell=0,
        )
        assert pc.name == "Sports"


class TestCellState:
    def test_cell_state_valid(self):
        """CellState models a single cell's runtime state."""
        cs = CellState(index=0, source_id="espn", status="active", pid=12345)
        assert cs.index == 0
        assert cs.status == "active"

    def test_cell_state_idle(self):
        """CellState can be idle with no source."""
        cs = CellState(index=1, source_id=None, status="idle", pid=None)
        assert cs.source_id is None


class TestAudioState:
    def test_audio_state_valid(self):
        """AudioState holds current audio routing."""
        audio = AudioState(active_cell=0)
        assert audio.active_cell == 0

    def test_audio_state_none(self):
        """AudioState active_cell can be None (muted)."""
        audio = AudioState(active_cell=None)
        assert audio.active_cell is None


class TestServerStatus:
    def test_server_status(self):
        """ServerStatus aggregates server state."""
        status = ServerStatus(
            layout_id="2x2",
            cells=[CellState(index=0, source_id="espn", status="active", pid=None)],
            audio=AudioState(active_cell=0),
            mock_mode=False,
        )
        assert status.layout_id == "2x2"
        assert len(status.cells) == 1


class TestPairing:
    def test_pairing_request(self):
        """PairingRequest holds a 6-digit code."""
        req = PairingRequest(code="123456")
        assert req.code == "123456"

    def test_pairing_request_code_must_be_6_digits(self):
        """PairingRequest rejects invalid codes."""
        with pytest.raises(ValidationError):
            PairingRequest(code="abc")

    def test_pairing_response(self):
        """PairingResponse contains a token."""
        resp = PairingResponse(token="abc123token")
        assert resp.token == "abc123token"


class TestErrorResponse:
    def test_error_response(self):
        """ErrorResponse wraps error details."""
        err = ErrorResponse(code="not_found", message="Source not found")
        assert err.code == "not_found"
