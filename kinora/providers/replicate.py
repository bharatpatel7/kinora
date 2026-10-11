"""Cloud generation via Replicate's HTTP API (bring your own API token)."""

from __future__ import annotations

import time
from pathlib import Path

import httpx

from ..config import Settings
from .base import GenerationRequest, ProgressFn, Provider, ProviderError

API = "https://api.replicate.com/v1"


class ReplicateProvider(Provider):
    name = "replicate"
    label = "Replicate (cloud)"

    def __init__(self, settings: Settings) -> None:
        self.token = settings.replicate_token
        self.model = settings.replicate_model
        self.description = f"Runs {self.model} on Replicate's GPUs. Needs REPLICATE_API_TOKEN; billed per run."

    def available(self) -> tuple[bool, str]:
        if not self.token:
            return False, "Set REPLICATE_API_TOKEN to enable."
        return True, ""

    def generate(self, req: GenerationRequest, out_path: Path, progress: ProgressFn) -> None:
        if not self.token:
            raise ProviderError("REPLICATE_API_TOKEN is not set.")
        headers = {"Authorization": f"Bearer {self.token}"}
        payload: dict = {"prompt": req.prompt}
        if req.negative_prompt:
            payload["negative_prompt"] = req.negative_prompt
        if req.seed is not None:
            payload["seed"] = req.seed

        with httpx.Client(headers=headers, timeout=60) as client:
            r = client.post(f"{API}/models/{self.model}/predictions", json={"input": payload})
            if r.status_code >= 400:
                raise ProviderError(f"Replicate rejected the request ({r.status_code}): {r.text[:300]}")
            prediction = r.json()

            started = time.monotonic()
            while prediction["status"] not in ("succeeded", "failed", "canceled"):
                # Replicate doesn't report fine-grained progress; show a slow creep so the UI feels alive.
                progress(min(0.9, (time.monotonic() - started) / 120))
                time.sleep(2)
                prediction = client.get(prediction["urls"]["get"]).json()

            if prediction["status"] != "succeeded":
                raise ProviderError(f"Replicate prediction {prediction['status']}: {prediction.get('error')}")

            output = prediction["output"]
            url = output[0] if isinstance(output, list) else output
            with client.stream("GET", url, follow_redirects=True) as resp:
                resp.raise_for_status()
                with out_path.open("wb") as f:
                    for chunk in resp.iter_bytes():
                        f.write(chunk)
        progress(1.0)
