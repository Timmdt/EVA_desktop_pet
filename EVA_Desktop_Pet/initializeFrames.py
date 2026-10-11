import argparse
from pathlib import Path
from PIL import Image, ImageChops

APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"

STATE_FILE = APP_DIR / "state.json"

framesPerSheet = 32


def _active_ranges(occupied: list[bool]) -> list[tuple[int, int]]:
    ranges = []
    start = None

    for index, is_occupied in enumerate(occupied):
        if is_occupied and start is None:
            start = index
        elif not is_occupied and start is not None:
            ranges.append((start, index))
            start = None

    if start is not None:
        ranges.append((start, len(occupied)))

    return ranges


def extract_spritesheet(input_path: Path, output_dir: Path) -> list[Path]:
    image = Image.open(input_path).convert("RGBA")
    hue, saturation, _ = image.convert("HSV").split()
    background = ImageChops.multiply(
        hue.point(lambda value: 255 if 190 <= value <= 245 else 0),
        saturation.point(lambda value: 255 if value >= 70 else 0),
    )
    foreground = ImageChops.multiply(
        ImageChops.invert(background),
        image.getchannel("A"),
    )
    pixels = foreground.load()
    width, height = image.size
    row_ranges = _active_ranges(
        [any(pixels[x, y] for x in range(width)) for y in range(height)]
    )

    frame_boxes = []
    for top, bottom in row_ranges:
        column_ranges = _active_ranges(
            [any(pixels[x, y] for y in range(top, bottom)) for x in range(width)]
        )
        for left, right in column_ranges:
            bounds = foreground.crop((left, top, right, bottom)).getbbox()
            if bounds is not None:
                frame_boxes.append(
                    (
                        left + bounds[0],
                        top + bounds[1],
                        left + bounds[2],
                        top + bounds[3],
                    )
                )

    if len(frame_boxes) != framesPerSheet:
        raise ValueError(
            f"Es wurden {len(frame_boxes)} Bilder erkannt; "
            f"erwartet werden {framesPerSheet}."
        )

    image.putalpha(foreground)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = []
    for index, bounds in enumerate(frame_boxes, start=1):
        output_path = output_dir / f"{input_path.stem}_{index:02}.png"
        image.crop(bounds).save(output_path)
        output_paths.append(output_path)

    return output_paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Entfernt den magentafarbenen Hintergrund und "
        "schneidet ein Sprite-Sheet in einzelne PNG-Bilder."
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Optionaler Pfad zu einem Sprite-Sheet; standardmäßig werden "
        "alle PNG-Dateien aus assets/models verarbeitet.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ASSETS_DIR / "frames",
        help="Zielordner für die transparenten PNGs (Standard: assets/frames)",
    )
    args = parser.parse_args()

    input_paths = [args.input] if args.input else sorted((ASSETS_DIR / "models").glob("*.png"))
    if not input_paths:
        parser.error(f"Keine PNG-Sprite-Sheets in {ASSETS_DIR / 'models'} gefunden.")

    for input_path in input_paths:
        output_paths = extract_spritesheet(input_path, args.output)
        print(
            f"{len(output_paths)} transparente Bilder aus {input_path.name} "
            f"gespeichert in: {args.output}"
        )


if __name__ == "__main__":
    main()
