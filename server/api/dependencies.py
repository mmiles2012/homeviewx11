"""FastAPI dependency providers — engine, registry, auth."""

from __future__ import annotations

from fastapi import Request

from server.composition.engine import CompositionEngine
from server.sources.registry import SourceRegistry
from server.auth.tokens import TokenManager
from server.auth.pairing import PairingManager


def get_engine(request: Request) -> CompositionEngine:
    return request.app.state.engine


def get_source_registry(request: Request) -> SourceRegistry:
    return request.app.state.source_registry


def get_token_manager(request: Request) -> TokenManager:
    return request.app.state.token_manager


def get_pairing_manager(request: Request) -> PairingManager:
    return request.app.state.pairing_manager


def get_preset_manager(request: Request):
    return request.app.state.preset_manager
