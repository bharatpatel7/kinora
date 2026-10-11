from __future__ import annotations

from ..config import Settings
from .base import GenerationRequest, Provider, ProviderError
from .local import LocalProvider
from .mock import MockProvider
from .replicate import ReplicateProvider

__all__ = ["GenerationRequest", "Provider", "ProviderError", "build_providers"]


def build_providers(settings: Settings) -> dict[str, Provider]:
    factories = {
        "mock": lambda: MockProvider(),
        "replicate": lambda: ReplicateProvider(settings),
        "local": lambda: LocalProvider(settings),
    }
    unknown = set(settings.providers) - factories.keys()
    if unknown:
        raise ValueError(f"Unknown provider(s) in KINORA_PROVIDERS: {', '.join(sorted(unknown))}")
    return {name: factories[name]() for name in settings.providers}
