"""Runtime settings, read from environment variables (prefix KINORA_)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(f"KINORA_{name}", default)


@dataclass(frozen=True)
class Settings:
    host: str = field(default_factory=lambda: _env("HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(_env("PORT", "8000")))
    output_dir: Path = field(default_factory=lambda: Path(_env("OUTPUT_DIR", "outputs")).resolve())
    # Comma-separated list of providers to enable, e.g. "mock,replicate,local".
    providers: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            p.strip() for p in _env("PROVIDERS", "mock,replicate,local").split(",") if p.strip()
        )
    )
    default_provider: str = field(default_factory=lambda: _env("DEFAULT_PROVIDER", "mock"))
    # Replicate (https://replicate.com) — set REPLICATE_API_TOKEN to enable.
    replicate_token: str | None = field(default_factory=lambda: os.environ.get("REPLICATE_API_TOKEN"))
    replicate_model: str = field(default_factory=lambda: _env("REPLICATE_MODEL", "lightricks/ltx-video"))
    # Public Hugging Face Space used by the free `huggingface` provider. HF_TOKEN is optional.
    hf_space: str = field(default_factory=lambda: _env("HF_SPACE", "Lightricks/ltx-video-distilled"))
    hf_token: str | None = field(default_factory=lambda: os.environ.get("HF_TOKEN"))
    # Local diffusers model (Hugging Face repo id).
    local_model: str = field(default_factory=lambda: _env("LOCAL_MODEL", "Lightricks/LTX-Video"))
