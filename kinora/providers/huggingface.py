"""Free, rate-limited generation through a public Hugging Face Space (ZeroGPU).

Meant for trying Kinora and for development, not production: public Spaces have daily GPU
quotas, queues, and can change their API at any time. Install with `pip install -e '.[huggingface]'`
and enable with KINORA_PROVIDERS=mock,huggingface. Setting HF_TOKEN (a free account) raises the quota.
"""

from __future__ import annotations

import shutil
import time
from importlib.util import find_spec
from pathlib import Path

from ..config import Settings
from .base import GenerationRequest, ProgressFn, Provider, ProviderError


class HuggingFaceSpaceProvider(Provider):
    name = "huggingface"
    label = "Hugging Face Space (free, testing)"

    def __init__(self, settings: Settings) -> None:
        self.space = settings.hf_space
        self.token = settings.hf_token
        self.description = (
            f"Uses the public {self.space} Space on free shared GPUs. Rate-limited; for testing."
        )

    def available(self) -> tuple[bool, str]:
        if find_spec("gradio_client") is None:
            return False, "Install with: pip install -e '.[huggingface]'"
        return True, ""

    def generate(self, req: GenerationRequest, out_path: Path, progress: ProgressFn) -> None:
        ok, reason = self.available()
        if not ok:
            raise ProviderError(reason)
        from gradio_client import Client

        progress(0.05)
        try:
            client = Client(self.space, token=self.token, verbose=False)
            job = client.submit(
                prompt=req.prompt,
                negative_prompt=req.negative_prompt
                or "worst quality, inconsistent motion, blurry, jittery, distorted",
                input_image_filepath=None,
                input_video_filepath=None,
                height_ui=max(256, req.height // 32 * 32),
                width_ui=max(256, req.width // 32 * 32),
                mode="text-to-video",
                duration_ui=req.num_frames / req.fps,
                ui_frames_to_use=9,
                seed_ui=req.seed if req.seed is not None else 42,
                randomize_seed=req.seed is None,
                ui_guidance_scale=1,
                improve_texture_flag=True,
                api_name="/text_to_video",
            )
            while not job.done():
                status = job.status()
                if status.progress_data:
                    p = status.progress_data[-1]
                    if p.index is not None and p.length:
                        progress(0.1 + 0.85 * p.index / p.length)
                time.sleep(1)
            video, _seed = job.result()
        except Exception as e:  # quota exhausted, Space sleeping, API changed, ...
            raise ProviderError(f"Hugging Face Space {self.space} failed: {e}") from e

        src = video["video"] if isinstance(video, dict) else video
        shutil.copyfile(src, out_path)
        progress(1.0)
