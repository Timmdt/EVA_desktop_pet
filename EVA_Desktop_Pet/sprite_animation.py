"""Generate motion-based sprite in-betweens without cross-fading poses."""

from collections.abc import Iterator

import cv2
import numpy as np
from PIL import Image

EyeRegions = tuple[tuple[int, int, int, int], ...]


def aligned_grid_frames(
    sheet: Image.Image,
    columns: int,
    rows: int,
    frame_size: tuple[int, int],
) -> list[Image.Image]:
    """Normalize a generated uniform grid to a common scale and baseline."""
    if columns < 1 or rows < 1:
        raise ValueError("Sprite grid must have positive rows and columns")
    crops = []
    for row in range(rows):
        for column in range(columns):
            cell = sheet.crop((round(column * sheet.width / columns),
                               round(row * sheet.height / rows),
                               round((column + 1) * sheet.width / columns),
                               round((row + 1) * sheet.height / rows)))
            alpha = np.array(cell.getchannel("A"))
            # Ignore isolated faint glow specks when aligning the character.
            ys = np.flatnonzero((alpha > 128).sum(axis=1) > 3)
            xs = np.flatnonzero((alpha > 128).sum(axis=0) > 3)
            if not len(xs) or not len(ys):
                raise ValueError("Empty sprite cell")
            crops.append(cell.crop((int(xs[0]), int(ys[0]),
                                    int(xs[-1]) + 1, int(ys[-1]) + 1)))
    width, height = frame_size
    scale = min(width * 0.88 / max(c.width for c in crops),
                height * 0.77 / max(c.height for c in crops))
    result = []
    for crop in crops:
        resized = crop.resize((round(crop.width * scale), round(crop.height * scale)),
                              Image.Resampling.NEAREST)
        frame = Image.new("RGBA", frame_size)
        frame.paste(resized, ((width - resized.width) // 2,
                             round(height * 0.91) - resized.height))
        result.append(frame)
    return result


def _region_mask(size: tuple[int, int], regions: EyeRegions) -> np.ndarray:
    width, height = size
    mask = np.zeros((height, width), dtype=np.uint8)
    for left, top, right, bottom in regions:
        mask[max(0, top):min(height, bottom), max(0, left):min(width, right)] = 255
    return mask


def _motion_image(
    rgba: np.ndarray,
    size: tuple[int, int],
    eye_regions: EyeRegions = (),
) -> np.ndarray:
    # Include the silhouette in motion estimation, even for dark sprites.
    opacity = rgba[..., 3:4].astype(np.float32) / 255.0
    rgb = rgba[..., :3] * opacity + 64.0 * (1.0 - opacity)
    gray = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    gray = cv2.resize(gray, size, interpolation=cv2.INTER_AREA)
    if eye_regions:
        mask = cv2.resize(_region_mask((rgba.shape[1], rgba.shape[0]), eye_regions),
                          size, interpolation=cv2.INTER_NEAREST)
        # Estimate head motion from its outline, not by morphing an oval iris
        # into a closed eyelid. The blink is a separate, discrete eye change.
        gray = cv2.inpaint(gray, mask, 5, cv2.INPAINT_TELEA)
    return gray


def intermediate_frames(
    current: Image.Image,
    following: Image.Image,
    count: int,
    *,
    eye_regions: tuple[EyeRegions, EyeRegions] | None = None,
    open_eye_source: int | None = None,
) -> Iterator[Image.Image]:
    """Warp the nearer pose toward the other; never overlay two poses.

    Nearest-neighbour sampling keeps original colors and opacity. Optical
    flow estimates motion, but cannot invent details hidden in both poses.
    """
    if count < 0:
        raise ValueError("Intermediate frame count must be nonnegative")
    if current.size != following.size:
        raise ValueError("Animation frames must have matching dimensions")
    if count == 0:
        return

    first = np.array(current.convert("RGBA"))
    second = np.array(following.convert("RGBA"))
    if np.array_equal(first, second):
        for _ in range(count):
            yield current.copy()
        return

    height, width = first.shape[:2]
    scale = min(1.0, 384 / max(width, height))
    motion_size = (max(12, round(width * scale)), max(12, round(height * scale)))
    if open_eye_source not in (None, 0, 1):
        raise ValueError("Open-eye source must be 0 or 1")
    if open_eye_source is not None and eye_regions is None:
        raise ValueError("An eye source requires eye regions")
    first_gray = _motion_image(first, motion_size, eye_regions[0] if eye_regions else ())
    second_gray = _motion_image(second, motion_size, eye_regions[1] if eye_regions else ())
    estimator = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    forward = estimator.calc(first_gray, second_gray, None)
    backward = estimator.calc(second_gray, first_gray, None)

    def full_size(flow: np.ndarray) -> np.ndarray:
        result = cv2.resize(flow, (width, height), interpolation=cv2.INTER_LINEAR)
        result[..., 0] *= width / motion_size[0]
        result[..., 1] *= height / motion_size[1]
        return result

    forward = full_size(forward)
    backward = full_size(backward)
    grid_y, grid_x = np.mgrid[:height, :width].astype(np.float32)

    def warp(source: np.ndarray, flow: np.ndarray, distance: float) -> np.ndarray:
        map_x = grid_x.copy()
        map_y = grid_y.copy()
        for _ in range(3):
            displacement = cv2.remap(
                flow, map_x, map_y, cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE,
            )
            map_x = grid_x - distance * displacement[..., 0]
            map_y = grid_y - distance * displacement[..., 1]
        return cv2.remap(source, map_x, map_y, cv2.INTER_NEAREST,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    for step in range(1, count + 1):
        progress = step / (count + 1)
        if progress <= 0.5:
            source, flow, distance = first, forward, progress
            source_index = 0
        else:
            source, flow, distance = second, backward, 1.0 - progress
            source_index = 1

        # Invert the forward displacement: find the source pixel that arrives
        # at each destination. Iterate because motion varies across the sprite.
        warped = warp(source, flow, distance)
        if open_eye_source is not None and open_eye_source != source_index:
            eye_source = first if open_eye_source == 0 else second
            eye_flow = forward if open_eye_source == 0 else backward
            eye_distance = progress if open_eye_source == 0 else 1.0 - progress
            eyes = warp(eye_source, eye_flow, eye_distance)
            mask = warp(_region_mask(current.size, eye_regions[open_eye_source]),
                        eye_flow, eye_distance)
            warped[mask > 0] = eyes[mask > 0]
        yield Image.fromarray(warped)
