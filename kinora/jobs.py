"""An in-memory job queue. One generation runs at a time (GPUs don't share well)."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .providers import GenerationRequest, Provider, ProviderError

log = logging.getLogger("kinora.jobs")


@dataclass
class Job:
    id: str
    provider: str
    request: GenerationRequest
    status: str = "queued"  # queued | running | succeeded | failed
    progress: float = 0.0
    error: str | None = None
    video_url: str | None = None
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["prompt"] = d.pop("request")["prompt"]
        return d


class JobManager:
    def __init__(self, providers: dict[str, Provider], output_dir: Path) -> None:
        self.providers = providers
        self.output_dir = output_dir
        self.jobs: dict[str, Job] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker: asyncio.Task | None = None

    def start(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._worker = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._worker:
            self._worker.cancel()

    def submit(self, provider: str, request: GenerationRequest) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], provider=provider, request=request)
        self.jobs[job.id] = job
        self._queue.put_nowait(job.id)
        return job

    def list(self) -> list[Job]:
        return sorted(self.jobs.values(), key=lambda j: j.created_at, reverse=True)

    async def _run(self) -> None:
        while True:
            job = self.jobs[await self._queue.get()]
            job.status = "running"
            out_path = self.output_dir / f"{job.id}.mp4"

            def progress(p: float, job: Job = job) -> None:
                job.progress = round(max(job.progress, min(p, 1.0)), 3)

            try:
                await asyncio.to_thread(self.providers[job.provider].generate, job.request, out_path, progress)
                job.status, job.progress, job.video_url = "succeeded", 1.0, f"/outputs/{out_path.name}"
            except ProviderError as e:
                job.status, job.error = "failed", str(e)
            except Exception as e:  # keep the worker alive no matter what a provider does
                log.exception("job %s crashed", job.id)
                job.status, job.error = "failed", f"Unexpected error: {e}"
            job.finished_at = time.time()
