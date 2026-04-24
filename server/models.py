"""Pydantic domain models for HomeView server."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, field_validator


class Source(BaseModel):
    """A streamable content source."""

    id: str
    name: str
    type: Literal["streaming", "url"]
    url: str
    icon_url: str | None = None
    requires_widevine: bool = False
    notes: str | None = None


class SourceCreate(BaseModel):
    """Payload for creating a new source."""

    name: str
    type: Literal["streaming", "url"] = "url"
    url: str
    icon_url: str | None = None
    requires_widevine: bool = False
    notes: str | None = None


class SourceUpdate(BaseModel):
    """Payload for updating a source (all fields optional)."""

    name: str | None = None
    type: Literal["streaming", "url"] | None = None
    url: str | None = None
    icon_url: str | None = None
    requires_widevine: bool | None = None
    notes: str | None = None


class CellState(BaseModel):
    """Runtime state of a single display cell."""

    index: int
    source_id: str | None = None
    status: Literal["active", "idle", "crashed", "starting"] = "idle"
    pid: int | None = None


class AudioState(BaseModel):
    """Current audio routing state."""

    active_cell: int | None = None


class ServerStatus(BaseModel):
    """Aggregated server state for status responses."""

    layout_id: str | None = None
    cells: list[CellState] = []
    audio: AudioState = AudioState()
    mock_mode: bool = False


class Preset(BaseModel):
    """A saved named configuration."""

    id: str
    name: str
    layout_id: str
    cell_assignments: dict[str, str | None] = {}
    active_audio_cell: int | None = None


class PresetCreate(BaseModel):
    """Payload for creating a preset."""

    name: str
    layout_id: str
    cell_assignments: dict[str, str | None] = {}
    active_audio_cell: int | None = None


class PairingRequest(BaseModel):
    """Client submits a pairing code to get a token."""

    code: str

    @field_validator("code")
    @classmethod
    def code_must_be_6_digits(cls, v: str) -> str:
        if not re.fullmatch(r"\d{6}", v):
            raise ValueError("code must be exactly 6 digits")
        return v


class PairingResponse(BaseModel):
    """Returned after successful pairing — contains Bearer token."""

    token: str


class ErrorResponse(BaseModel):
    """Standard error body."""

    code: str
    message: str
