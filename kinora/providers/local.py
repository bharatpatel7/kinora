"""Run an open-weights model on this machine with Hugging Face diffusers.

Install with `pip install -e '.[local]'`. Uses CUDA if present, else Apple's MPS, else CPU.
Note: Linux containers (Docker, apple/container) can't see the Mac GPU, so run this provider natively on macOS.
"""

from __future__ import annotations

import threading
from importlib.util import find_spec
from pathlib import Path

from ..config import Settings
from .base import GenerationRequest, ProgressFn, Provider, ProviderError


class LocalProvider(Provider):
    name = "local"
    label = "Local GPU (experimental)"

    def __init__(self, settings: Settings) -> None:
        self.model_id = settings.local_model
        self.description = f"Runs {self.model_id} on your own GPU. First run downloads several GB of weights."
        self._pipe = None
        self._lock = threading.Lock()

    def available(self) -> tuple[bool, str]:
        if find_spec("torch") is None or find_spec("diffusers") is None:
            return False, "Install with: pip install -e '.[local]'"
        return True, ""

    def _device(self) -> str:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load(self):
        with self._lock:
            if self._pipe is None:
                import torch
                from diffusers import LTXPipeline

                device = self._device()
                dtype = torch.bfloat16 if device != "cpu" else torch.float32
                pipe = LTXPipeline.from_pretrained(self.model_id, torch_dtype=dtype)
                if device == "cuda":
                    pipe.enable_model_cpu_offload()
                else:
                    pipe.to(device)
                pipe.vae.enable_tiling()  # keeps VAE decode within memory on 16 GB machines
                self._pipe = pipe
            return self._pipe

    def generate(self, req: GenerationRequest, out_path: Path, progress: ProgressFn) -> None:
        ok, reason = self.available()
        if not ok:
            raise ProviderError(reason)
        import torch
        from diffusers.utils import export_to_video

        pipe = self._load()
        steps = 30

        def on_step(_pipe, step, _timestep, kwargs):
            progress(0.95 * (step + 1) / steps)
            return kwargs

        generator = None
        if req.seed is not None:
            generator = torch.Generator(device="cpu").manual_seed(req.seed)

        # LTX-Video wants dimensions divisible by 32 and frame counts of the form 8k+1.
        width, height = req.width // 32 * 32, req.height // 32 * 32
        num_frames = (req.num_frames - 1) // 8 * 8 + 1
        try:
            result = pipe(
                prompt=req.prompt,
                negative_prompt=req.negative_prompt or "worst quality, blurry, jittery, distorted",
                width=width,
                height=height,
                num_frames=num_frames,
                num_inference_steps=steps,
                generator=generator,
                callback_on_step_end=on_step,
            )
        except RuntimeError as e:  # most commonly out-of-memory
            raise ProviderError(f"Local generation failed: {e}. Try fewer frames or a smaller size.") from e
        export_to_video(result.frames[0], str(out_path), fps=req.fps)
        progress(1.0)
