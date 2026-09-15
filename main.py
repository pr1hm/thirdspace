"""FastAPI image editor with dynamically discovered filter plugins."""

from __future__ import annotations

import importlib.util
import inspect
import io
import json
from pathlib import Path
from types import ModuleType
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image, UnidentifiedImageError

BASE_DIR = Path(__file__).resolve().parent
FILTERS_DIR = BASE_DIR / "filters"

app = FastAPI(title="Image Editor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def discover_filters() -> dict[str, dict[str, Any]]:
    """Load filter modules that expose a callable ``process`` function."""
    discovered: dict[str, dict[str, Any]] = {}
    FILTERS_DIR.mkdir(exist_ok=True)

    for path in sorted(FILTERS_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue

        module_name = f"image_editor_filter_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            print(f"Warning: could not load filter '{path.name}': {exc}")
            continue

        process = getattr(module, "process", None)
        if not callable(process):
            continue

        filter_name = str(getattr(module, "NAME", path.stem))
        discovered[filter_name] = {
            "name": filter_name,
            "description": str(
                getattr(module, "DESCRIPTION", f"Filter from {path.name}")
            ),
            "process": process,
            "module": module,
        }

    return discovered


def parse_filter_sequence(raw_filters: str) -> list[dict[str, Any]]:
    """Decode and validate the filter sequence sent by the browser."""
    try:
        filters = json.loads(raw_filters)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="filters must be valid JSON") from exc

    if not isinstance(filters, list):
        raise HTTPException(status_code=400, detail="filters must be a JSON array")

    validated: list[dict[str, Any]] = []
    for item in filters:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise HTTPException(
                status_code=400,
                detail="each filter must contain a string name",
            )
        try:
            intensity = float(item.get("intensity", 100))
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail="filter intensity must be numeric",
            ) from exc
        validated.append(
            {
                "name": item["name"],
                "intensity": max(0.0, min(100.0, intensity)),
            }
        )
    return validated


def call_plugin(process: Any, image: Image.Image, intensity: float) -> Image.Image:
    """Call a plugin while supporting the documented intensity contract."""
    result = process(image, intensity=intensity)
    if inspect.isawaitable(result):
        raise TypeError("async filter plugins are not supported; use a sync process()")
    if not isinstance(result, Image.Image):
        raise TypeError("filter process() must return a PIL.Image.Image")
    return result


@app.get("/inventory")
def inventory() -> list[dict[str, str]]:
    """Return metadata for every valid filter currently in ``filters/``."""
    return [
        {"name": item["name"], "description": item["description"]}
        for item in discover_filters().values()
    ]


@app.post("/process")
async def process_image(
    image: UploadFile = File(...),
    filters: str = Form("[]"),
) -> StreamingResponse:
    """Apply the selected plugins sequentially and return a PNG image."""
    try:
        source = Image.open(io.BytesIO(await image.read())).convert("RGBA")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="uploaded file is not a valid image") from exc

    selected_filters = parse_filter_sequence(filters)
    available_filters = discover_filters()

    for selected in selected_filters:
        plugin = available_filters.get(selected["name"])
        if plugin is None:
            raise HTTPException(
                status_code=404,
                detail=f"unknown filter: {selected['name']}",
            )
        try:
            source = call_plugin(plugin["process"], source, selected["intensity"])
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"filter '{selected['name']}' failed: {exc}",
            ) from exc

    output = io.BytesIO()
    source.convert("RGBA").save(output, format="PNG")
    output.seek(0)
    return StreamingResponse(output, media_type="image/png")
