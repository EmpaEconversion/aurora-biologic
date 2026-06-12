"""FastAPI REST API for aurora_biologic."""

import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

import aurora_biologic.biologic as bio

logger = logging.getLogger(__name__)

API_KEY = os.environ.get("AURORA_BIOLOGIC_API_KEY")

if API_KEY:
    logger.warning("🔑 API key authentication enabled")
else:
    logger.warning(
        "⚠️⚠️⚠️ No API key authentication enabled! ⚠️⚠️⚠️\n"
        "Anyone with access to this endpoint can stop all your measurements and set every channel to max voltage.\n"
        "Only use in this mode within a trusted network!\n"
        "Set an API key with the 'AURORA_BIOLOGIC_API_KEY' environment variable.\n"
        "E.g.\n"
        '$env:AURORA_BIOLOGIC_API_KEY = "myverysecretkey"\n'
        "uvicorn aurora_biologic.api.main:app --host=0.0.0.0 --port=8000"
    )

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_key(key: str | None = Security(api_key_header)) -> None:
    """If API key is set, compare against requests."""
    if API_KEY is None:
        return  # no key configured = open access
    if key is None or not secrets.compare_digest(key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201, ARG001
    """Check that the status of channels can be read on startup."""
    with bio.BiologicAPI() as b:
        b.get_status()
    yield


app = FastAPI(
    title="Biologic REST API",
    lifespan=lifespan,
    dependencies=[Security(verify_key)],
)


@app.exception_handler(ValueError)
def _value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Map ValueError to HTTP 400 Bad Request."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(FileNotFoundError)
def _file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
    """Map FileNotFoundError to HTTP 422 Unprocessable Entity."""
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/pipelines")
def get_pipelines(show_offline: bool = False) -> dict[str, dict]:
    """Get details of all connected instruments."""
    return bio.get_pipelines(show_offline=show_offline)


@app.get("/status")
def get_status(
    pipeline_ids: Annotated[list[str] | None, Query()] = None,
    show_offline: bool = False,
) -> dict[str, dict]:
    """Get cycling status for all or selected pipelines."""
    return bio.get_status(pipeline_ids=pipeline_ids, show_offline=show_offline)


@app.get("/job-id")
def get_job_id(
    pipeline_ids: Annotated[list[str] | None, Query()] = None,
    show_offline: bool = False,
) -> dict[str, str | None]:
    """Get job IDs for all or selected pipelines."""
    return bio.get_job_id(pipeline_ids, show_offline=show_offline)


class SettingsRequest(BaseModel):
    """Request body for loading settings onto a pipeline."""

    settings_file: str


class RunRequest(BaseModel):
    """Request body for running a pipeline."""

    output_path: str


class StartRequest(BaseModel):
    """Request body for start."""

    settings_file: str
    output_path: str


@app.post("/load-settings/{pipeline}", status_code=204)
def load_settings(pipeline: str, body: SettingsRequest) -> None:
    """Load settings onto a pipeline."""
    bio.load_settings(pipeline, Path(body.settings_file))


@app.post("/run-channel/{pipeline}", status_code=204)
def run_channel(pipeline: str, body: RunRequest) -> None:
    """Run settings loaded on a pipeline."""
    bio.run_channel(pipeline, Path(body.output_path))


@app.post("/start/{pipeline}", status_code=204)
def start(pipeline: str, body: StartRequest) -> None:
    """Load and run settings on a pipeline."""
    bio.start(pipeline, Path(body.settings_file), Path(body.output_path))


@app.post("/stop/{pipeline}", status_code=204)
def stop(pipeline: str) -> None:
    """Stop cycling on a pipeline."""
    bio.stop(pipeline)
