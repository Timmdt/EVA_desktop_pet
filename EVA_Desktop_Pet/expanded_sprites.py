"""Optional 4x4 EVA sprite sheets with safe fallback to existing assets.

Unlike per-frame alpha bounding-box normalization, this loader keeps the
same coordinate system for all frames, avoiding pose-dependent shifting.
"""
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image


def load_expanded_sheets(assets_dir: Path) -> dict[str, Path]:
    directory = assets_dir / "expanded"
    path = directory / "manifest.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if (data.get("format") != "eva-4x4-v1"
                or data.get("columns") != 4 or data.get("rows") != 4
                or not isinstance(data.get("states"), dict)):
            return {}
    except (ValueError, OSError, UnicodeError):
        return {}

    result: dict[str, Path] = {}
    for state, filename in data["states"].items():
        if not isinstance(state, str) or not isinstance(filename, str):
            continue
        if Path(filename).name != filename or not filename.endswith(".png"):
            continue
        candidate = directory / filename
        if candidate.is_file():
            result[state] = candidate
    return result


def fixed_grid_frames(
    sheet: Image.Image,
    columns: int = 4,
    rows: int = 4,
    frame_size: tuple[int, int] = (543, 724),
) -> list[Image.Image]:
    """Split a possibly non-divisible grid without recentering any pose."""
    if columns <= 0 or rows <= 0:
        raise ValueError("Grid dimensions must be positive")
    width, height = frame_size
    if width <= 0 or height <= 0:
        raise ValueError("Frame dimensions must be positive")
    tile_width = round(width * .86)
    tile_height = round(tile_width * sheet.height / rows / (sheet.width / columns))
    anchor_y = round(height * .91)
    result: list[Image.Image] = []
    rgba = sheet.convert("RGBA")
    for r in range(rows):
        for c in range(columns):
            cell = rgba.crop((
                round(c * rgba.width / columns),
                round(r * rgba.height / rows),
                round((c + 1) * rgba.width / columns),
                round((r + 1) * rgba.height / rows),
            ))
            if cell.getchannel("A").getbbox() is None:
                raise ValueError(f"Empty generated sprite cell at ({r}, {c})")
            resized = cell.resize((tile_width, tile_height), Image.Resampling.NEAREST)
            frame = Image.new("RGBA", frame_size)
            frame.paste(resized, ((width - tile_width) // 2, anchor_y - tile_height))
            result.append(frame)
    return result
