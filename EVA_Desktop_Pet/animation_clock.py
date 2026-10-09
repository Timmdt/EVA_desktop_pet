"""Wall-clock animation progress independent of Qt timer jitter."""


def frame_index_at(
    elapsed: float,
    frame_count: int,
    original_fps: float,
    intermediates: int,
    speed: float = 1.0,
) -> int:
    """Return the correct sprite frame, even if a timer tick was missed.

    Original-pose timing is unchanged when the number of in-betweens changes.
    """
    if frame_count <= 0:
        raise ValueError("frame_count must be positive")
    if original_fps <= 0 or speed <= 0:
        raise ValueError("fps and speed must be positive")
    if intermediates < 0:
        raise ValueError("intermediates must be nonnegative")
    return int(max(0.0, elapsed) * original_fps * (intermediates + 1) * speed) % frame_count
