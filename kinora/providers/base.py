"""The provider interface every video backend implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ProgressFn = Callable[[float], None]


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    negative_prompt: str = ""
    width: int = 768
    height: int = 432
    num_frames: int = 97  # ~4s at 24 fps
    fps: int = 24
    seed: int | None = None


class ProviderError(RuntimeError):
    """A generation failed in a way that should be shown to the user."""


class Provider(ABC):
    name: str
    label: str
    description: str

    def available(self) -> tuple[bool, str]:
        """Return (is_available, reason). Shown in the UI so users know what to set up."""
        return True, ""

    @abstractmethod
    def generate(self, req: GenerationRequest, out_path: Path, progress: ProgressFn) -> None:
        """Generate a video for `req` and write it as an .mp4 to `out_path`. Runs in a worker thread."""
