from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageChops


APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"
FRAMES_PER_SHEET = 32
SHEET_COLUMNS = 8
SHEET_ROWS = 4
FRAME_LAYOUT_VERSION = "centered-v1"
VERSION_FILE_NAME = ".layout-version"


def _remove_magenta_background(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    hue, saturation, _ = image.convert("HSV").split()
    magenta = ImageChops.multiply(
        hue.point(lambda value: 255 if 190 <= value <= 245 else 0),
        saturation.point(lambda value: 255 if value >= 70 else 0),
    )
    original_alpha = image.getchannel("A")
    foreground_alpha = ImageChops.multiply(ImageChops.invert(magenta), original_alpha)
    image.putalpha(foreground_alpha)
    return image


def extract_spritesheet(input_path: Path, output_dir: Path) -> list[Path]:
    """Teilt das Sprite-Sheet und zentriert jedes Motiv in einer festen Box."""
    image = _remove_magenta_background(Image.open(input_path))
    width, height = image.size
    frame_width = math.ceil(width / SHEET_COLUMNS)
    frame_height = math.ceil(height / SHEET_ROWS)

    output_dir.mkdir(parents=True, exist_ok=True)
    centered_frames: list[Image.Image] = []
    output_paths: list[Path] = []

    for row in range(SHEET_ROWS):
        for column in range(SHEET_COLUMNS):
            left = round(column * width / SHEET_COLUMNS)
            right = round((column + 1) * width / SHEET_COLUMNS)
            top = round(row * height / SHEET_ROWS)
            bottom = round((row + 1) * height / SHEET_ROWS)

            frame = image.crop((left, top, right, bottom))
            visible_bounds = frame.getchannel("A").getbbox()
            if visible_bounds is None:
                raise ValueError(f"Frame in Reihe {row + 1}, Spalte {column + 1} ist leer.")

            # Nur das sichtbare Pet verwenden. Die transparente Zielbox bleibt
            # fuer alle Frames gleich gross, das Pet sitzt immer in ihrer Mitte.
            pet = frame.crop(visible_bounds)
            canvas = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
            x = (frame_width - pet.width) // 2
            y = (frame_height - pet.height) // 2
            # Die Alpha-Maske verhindert, dass unsichtbare Magenta-RGB-Werte
            # beim Skalieren als farbiger Rand durchscheinen.
            canvas.paste(pet, (x, y), pet)
            centered_frames.append(canvas)

    for index, canvas in enumerate(centered_frames, start=1):
        output_path = output_dir / f"{input_path.stem}_{index:02}.png"
        canvas.save(output_path)
        output_paths.append(output_path)

    if len(output_paths) != FRAMES_PER_SHEET:
        raise RuntimeError(
            f"Es wurden {len(output_paths)} Frames erzeugt; erwartet werden {FRAMES_PER_SHEET}."
        )
    (output_dir / VERSION_FILE_NAME).write_text(FRAME_LAYOUT_VERSION, encoding="utf-8")
    return output_paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Entfernt den magentafarbenen Hintergrund und teilt Sprite-Sheets in Frames."
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Optionaler Pfad; standardmaessig werden alle PNGs aus assets/models verarbeitet.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ASSETS_DIR / "frames",
        help="Zielordner fuer die transparenten PNGs (Standard: assets/frames)",
    )
    args = parser.parse_args()

    input_paths = [args.input] if args.input else sorted((ASSETS_DIR / "models").glob("*.png"))
    if not input_paths:
        parser.error(f"Keine PNG-Sprite-Sheets in {ASSETS_DIR / 'models'} gefunden.")

    for input_path in input_paths:
        output_paths = extract_spritesheet(input_path, args.output)
        print(f"{len(output_paths)} Frames aus {input_path.name} gespeichert in: {args.output}")


if __name__ == "__main__":
    main()
