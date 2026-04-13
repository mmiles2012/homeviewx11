"""All REST API routes per PRD Section 5.5.1."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from server.api.dependencies import get_engine, get_source_registry, get_preset_manager
from server.composition.engine import CompositionEngine
from server.models import SourceCreate, SourceUpdate
from server.presets.manager import PresetManager, PresetNotFoundError as _PresetNotFoundError
from server.sources.registry import SourceNotFoundError, SourceAlreadyExistsError, SourceRegistry

router = APIRouter(prefix="/api/v1")

_NOT_IMPLEMENTED = {"error": {"code": "NOT_IMPLEMENTED", "message": "Not yet implemented", "details": {}}}


def _err(code: str, message: str, status: int = 400) -> HTTPException:
    return HTTPException(status_code=status, detail={"error": {"code": code, "message": message, "details": {}}})


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

@router.get("/server/info")
async def server_info(request: Request) -> dict:
    from server.config import get_config
    config = get_config()
    return {
        "server_name": config.server_name,
        "version": "1.0.0",
        "mock_mode": request.app.state.mock_mode,
    }


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@router.get("/status")
async def get_status(engine: CompositionEngine = Depends(get_engine)) -> dict:
    state = engine.get_state()
    return {
        "layout_id": state.layout_id,
        "cells": [c.model_dump() for c in state.cells],
        "audio": state.audio.model_dump(),
    }


# ---------------------------------------------------------------------------
# Layouts
# ---------------------------------------------------------------------------

@router.get("/layouts")
async def list_layouts(engine: CompositionEngine = Depends(get_engine)) -> list:
    layouts = engine._layout_manager.list_layouts()
    return [{"id": l.id, "name": l.name, "gap_px": l.gap_px, "cell_count": len(l.cells)} for l in layouts]


@router.put("/layout")
async def apply_layout(body: dict, engine: CompositionEngine = Depends(get_engine)) -> dict:
    layout_id = body.get("layout_id")
    if not layout_id:
        raise _err("MISSING_FIELD", "layout_id is required", 422)
    try:
        await engine.set_layout(layout_id)
    except ValueError:
        raise _err("NOT_FOUND", f"Layout '{layout_id}' not found", 404)
    return {"layout_id": layout_id}


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

@router.get("/sources")
async def list_sources(registry: SourceRegistry = Depends(get_source_registry)) -> list:
    sources = await registry.list_sources()
    return [s.model_dump() for s in sources]


@router.get("/sources/{source_id}")
async def get_source(source_id: str, registry: SourceRegistry = Depends(get_source_registry)) -> dict:
    try:
        return (await registry.get_source(source_id)).model_dump()
    except SourceNotFoundError:
        raise _err("NOT_FOUND", f"Source '{source_id}' not found", 404)


@router.post("/sources", status_code=201)
async def create_source(body: dict, registry: SourceRegistry = Depends(get_source_registry)) -> dict:
    try:
        data = SourceCreate(**body)
        source = await registry.create_source(data)
        return source.model_dump()
    except SourceAlreadyExistsError as e:
        raise _err("CONFLICT", str(e), 409)


@router.put("/sources/{source_id}")
async def update_source(source_id: str, body: dict, registry: SourceRegistry = Depends(get_source_registry)) -> dict:
    try:
        data = SourceUpdate(**body)
        source = await registry.update_source(source_id, data)
        return source.model_dump()
    except SourceNotFoundError:
        raise _err("NOT_FOUND", f"Source '{source_id}' not found", 404)


@router.delete("/sources/{source_id}", status_code=204)
async def delete_source(source_id: str, registry: SourceRegistry = Depends(get_source_registry)) -> None:
    try:
        await registry.delete_source(source_id)
    except SourceNotFoundError:
        raise _err("NOT_FOUND", f"Source '{source_id}' not found", 404)
    except ValueError as e:
        raise _err("CONFLICT", str(e), 409)


# ---------------------------------------------------------------------------
# Cells
# ---------------------------------------------------------------------------

@router.put("/cells/{cell_index}/source")
async def assign_source(cell_index: int, body: dict, engine: CompositionEngine = Depends(get_engine)) -> dict:
    source_id = body.get("source_id")
    if not source_id:
        raise _err("MISSING_FIELD", "source_id is required", 422)
    try:
        await engine.assign_source(cell_index=cell_index, source_id=source_id)
    except (ValueError, SourceNotFoundError) as e:
        raise _err("NOT_FOUND", str(e), 404)
    return engine.get_state().cells[cell_index].model_dump()


@router.delete("/cells/{cell_index}/source", status_code=204)
async def clear_cell(cell_index: int, engine: CompositionEngine = Depends(get_engine)) -> None:
    try:
        await engine.clear_cell(cell_index=cell_index)
    except ValueError as e:
        raise _err("NOT_FOUND", str(e), 404)


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

@router.put("/audio/active")
async def set_active_audio(body: dict, engine: CompositionEngine = Depends(get_engine)) -> dict:
    cell_index = body.get("cell_index")
    engine._active_audio_cell = cell_index
    engine._notify_state_change()
    return {"active_cell": cell_index}


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

@router.get("/presets")
async def list_presets(mgr: PresetManager = Depends(get_preset_manager)) -> list:
    presets = await mgr.list_presets()
    return [p.model_dump() for p in presets]


@router.post("/presets", status_code=201)
async def save_preset(body: dict, mgr: PresetManager = Depends(get_preset_manager)) -> dict:
    name = body.get("name")
    if not name:
        raise _err("MISSING_FIELD", "name is required", 422)
    preset = await mgr.save_preset(name)
    return preset.model_dump()


@router.put("/presets/{preset_id}/apply")
async def apply_preset(preset_id: str, mgr: PresetManager = Depends(get_preset_manager)) -> dict:
    try:
        await mgr.apply_preset(preset_id)
    except _PresetNotFoundError:
        raise _err("NOT_FOUND", f"Preset '{preset_id}' not found", 404)
    return {"preset_id": preset_id}


@router.delete("/presets/{preset_id}", status_code=204)
async def delete_preset(preset_id: str, mgr: PresetManager = Depends(get_preset_manager)) -> None:
    try:
        await mgr.delete_preset(preset_id)
    except _PresetNotFoundError:
        raise _err("NOT_FOUND", f"Preset '{preset_id}' not found", 404)


# ---------------------------------------------------------------------------
# Stubs — Interactive Mode (Task 14)
# ---------------------------------------------------------------------------

@router.post("/interactive/start")
@router.post("/interactive/stop")
async def interactive_stub() -> JSONResponse:
    return JSONResponse(status_code=501, content=_NOT_IMPLEMENTED)
