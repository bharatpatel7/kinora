"""HTTP API + static frontend."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .config import Settings
from .jobs import JobManager
from .providers import GenerationRequest, build_providers

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


class CreateJob(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    negative_prompt: str = Field(default="", max_length=2000)
    provider: str | None = None
    width: int = Field(default=768, ge=128, le=1280)
    height: int = Field(default=432, ge=128, le=1280)
    seconds: float = Field(default=4.0, gt=0, le=10)
    fps: int = Field(default=24, ge=8, le=30)
    seed: int | None = None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    providers = build_providers(settings)
    manager = JobManager(providers, settings.output_dir)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        manager.start()
        yield
        await manager.stop()

    app = FastAPI(title="Kinora", version=__version__, lifespan=lifespan)
    app.state.manager = manager

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "version": __version__}

    @app.get("/api/providers")
    def list_providers() -> dict:
        items = []
        for p in providers.values():
            ok, reason = p.available()
            items.append(
                {
                    "name": p.name,
                    "label": p.label,
                    "description": p.description,
                    "available": ok,
                    "reason": reason,
                }
            )
        return {"default": settings.default_provider, "providers": items}

    @app.post("/api/jobs", status_code=201)
    def create_job(body: CreateJob) -> dict:
        name = body.provider or settings.default_provider
        provider = providers.get(name)
        if provider is None:
            raise HTTPException(404, f"Unknown provider '{name}'")
        ok, reason = provider.available()
        if not ok:
            raise HTTPException(400, f"Provider '{name}' is not available: {reason}")
        req = GenerationRequest(
            prompt=body.prompt.strip(),
            negative_prompt=body.negative_prompt.strip(),
            width=body.width // 16 * 16,
            height=body.height // 16 * 16,
            num_frames=max(1, round(body.seconds * body.fps)),
            fps=body.fps,
            seed=body.seed,
        )
        return manager.submit(name, req).to_dict()

    @app.get("/api/jobs")
    def list_jobs() -> list[dict]:
        return [j.to_dict() for j in manager.list()]

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        job = manager.jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "Job not found")
        return job.to_dict()

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/outputs", StaticFiles(directory=settings.output_dir), name="outputs")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    return app
