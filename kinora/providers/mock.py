"""A no-GPU provider that renders an animated title card. Useful for development and CI."""

from __future__ import annotations

import colorsys
import hashlib
import textwrap
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .base import GenerationRequest, ProgressFn, Provider


class MockProvider(Provider):
    name = "mock"
    label = "Mock (no GPU)"
    description = "Renders an animated placeholder clip with your prompt. Works everywhere, instantly."

    def generate(self, req: GenerationRequest, out_path: Path, progress: ProgressFn) -> None:
        # Derive a stable base hue from the prompt (or seed) so the same input gives the same clip.
        key = f"{req.seed}" if req.seed is not None else req.prompt
        base_hue = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF

        font = _load_font(max(18, req.height // 14))
        lines = textwrap.wrap(req.prompt, width=max(20, req.width // (font.size // 2 + 4)))[:5]

        yy, xx = np.mgrid[0 : req.height, 0 : req.width].astype(np.float32)
        writer = imageio.get_writer(out_path, fps=req.fps, codec="libx264", quality=7, macro_block_size=1)
        try:
            for i in range(req.num_frames):
                t = i / max(1, req.num_frames - 1)
                img = Image.fromarray(_gradient(xx, yy, base_hue, t, req.width, req.height))
                draw = ImageDraw.Draw(img)
                line_h = font.size + 8
                y0 = (req.height - line_h * len(lines)) // 2
                alpha = int(255 * min(1.0, t * 4))  # fade text in
                for n, line in enumerate(lines):
                    w = draw.textlength(line, font=font)
                    draw.text(((req.width - w) / 2, y0 + n * line_h), line, font=font, fill=(255, 255, 255, alpha))
                draw.text((12, req.height - font.size - 12), "kinora · mock", font=font, fill=(255, 255, 255))
                writer.append_data(np.asarray(img))
                progress((i + 1) / req.num_frames)
        finally:
            writer.close()


def _gradient(xx: np.ndarray, yy: np.ndarray, hue: float, t: float, w: int, h: int) -> np.ndarray:
    c1 = np.array(colorsys.hsv_to_rgb((hue + 0.15 * t) % 1, 0.7, 0.9), dtype=np.float32)
    c2 = np.array(colorsys.hsv_to_rgb((hue + 0.5 + 0.15 * t) % 1, 0.8, 0.35), dtype=np.float32)
    mix = (xx / w * np.cos(t * np.pi) + yy / h * np.sin(t * np.pi) + 1) / 3
    frame = c1 * (1 - mix[..., None]) + c2 * mix[..., None]
    return (frame * 255).clip(0, 255).astype(np.uint8)


def _load_font(size: int) -> ImageFont.ImageFont:
    for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "Helvetica.ttc", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)
