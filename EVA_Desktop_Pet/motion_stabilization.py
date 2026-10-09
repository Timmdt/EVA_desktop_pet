"""Keep EVA's body fixed while its ears, hands and glow effects move."""

import cv2
import numpy as np
from PIL import Image


def body_anchor(frame: Image.Image) -> tuple[float, float] | None:
    """Find the large bright shell, not the changing alpha/glow bounding box."""
    pixels = np.asarray(frame.convert("RGBA"))
    rgb = pixels[..., :3]
    alpha = pixels[..., 3]
    white_shell = (
        (alpha >= 180)
        & (rgb[..., 0] >= 140)
        & (rgb[..., 1] >= 140)
        & (rgb[..., 2] >= 140)
    ).astype(np.uint8)
    count, _, stats, centers = cv2.connectedComponentsWithStats(white_shell, 8)
    if count < 2:
        return None
    index = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    if stats[index, cv2.CC_STAT_AREA] < max(40, frame.width * frame.height * 0.006):
        return None
    return tuple(float(x) for x in centers[index])


def stabilize_frames(frames: list[Image.Image], max_shift: int = 18) -> list[Image.Image]:
    """Remove small registration errors, without resizing or fading sprites.

    Frame alignment uses the shell, avoiding the false shifts caused by
    independent arms, decorations, and hover particles changing the silhouette.
    Larger intended movements are limited by max_shift rather than erased.
    """
    if not frames:
        return []
    if max_shift < 0:
        raise ValueError("max_shift must be nonnegative")
    size = frames[0].size
    if any(frame.size != size for frame in frames):
        raise ValueError("All frames must have the same canvas size")

    anchors = [body_anchor(frame) for frame in frames]
    available = [anchor for anchor in anchors if anchor is not None]
    if not available:
        return [frame.copy() for frame in frames]

    target_x, target_y = np.median(np.array(available), axis=0)
    output = []
    for frame, anchor in zip(frames, anchors):
        if anchor is None:
            output.append(frame.copy())
            continue
        dx = int(np.clip(np.rint(target_x - anchor[0]), -max_shift, max_shift))
        dy = int(np.clip(np.rint(target_y - anchor[1]), -max_shift, max_shift))
        if dx == 0 and dy == 0:
            output.append(frame.copy())
        else:
            canvas = Image.new("RGBA", size, (0, 0, 0, 0))
            canvas.paste(frame.convert("RGBA"), (dx, dy))
            output.append(canvas)
    return output
