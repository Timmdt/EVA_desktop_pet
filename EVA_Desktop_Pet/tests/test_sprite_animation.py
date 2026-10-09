import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sprite_animation import aligned_grid_frames, intermediate_frames


class MotionInterpolationTests(unittest.TestCase):
    def test_translated_shape_moves_without_transparent_double(self):
        first = np.zeros((96, 96, 4), dtype=np.uint8)
        first[28:60, 24:48] = (40, 180, 240, 255)
        first[32:40, 28:36] = (255, 255, 255, 255)
        second = np.zeros_like(first)
        second[:, 12:] = first[:, :-12]
        frames = list(intermediate_frames(Image.fromarray(first), Image.fromarray(second), 3))
        self.assertEqual(len(frames), 3)
        previous_x = np.nonzero(first[..., 3])[1].mean()
        for index, frame in enumerate(frames, 1):
            result = np.array(frame)
            # Ghosting would introduce intermediate opacity or new colors.
            self.assertEqual(set(np.unique(result[..., 3])), {0, 255})
            self.assertTrue(set(map(tuple, result.reshape(-1, 4))).issubset(
                set(map(tuple, first.reshape(-1, 4)))
            ))
            x = np.nonzero(result[..., 3])[1].mean()
            self.assertGreater(x, previous_x)
            self.assertAlmostEqual(x, 35.5 + 12 * index / 4, delta=1.5)
            previous_x = x

    def test_identical_frames_are_preserved(self):
        frame = Image.new("RGBA", (32, 32), (20, 80, 160, 128))
        for result in intermediate_frames(frame, frame, 3):
            self.assertEqual(result.tobytes(), frame.tobytes())

    def test_zero_frames(self):
        frame = Image.new("RGBA", (32, 32))
        self.assertEqual(list(intermediate_frames(frame, frame, 0)), [])

    def test_blink_keeps_open_eyes_in_body_inbetweens(self):
        opened = np.zeros((96, 96, 4), dtype=np.uint8)
        opened[16:80, 16:80] = (20, 30, 50, 255)
        opened[30:50, 28:44] = (30, 210, 255, 255)
        opened[30:50, 52:68] = (30, 210, 255, 255)
        closed = opened.copy()
        closed[30:50, 28:44] = (20, 30, 50, 255)
        closed[30:50, 52:68] = (20, 30, 50, 255)
        closed[39:42, 28:44] = (30, 210, 255, 255)
        closed[39:42, 52:68] = (30, 210, 255, 255)
        regions = ((24, 26, 48, 54), (48, 26, 72, 54))
        outside = np.ones((96, 96), dtype=bool)
        outside[26:54, 24:72] = False
        for source in (0, 1):
            images = (opened, closed) if source == 0 else (closed, opened)
            frames = list(intermediate_frames(
                *(Image.fromarray(a) for a in images), 3,
                eye_regions=(regions, regions), open_eye_source=source,
            ))
            self.assertEqual(len(frames), 3)
            for frame in frames:
                array = np.array(frame)
                # Slow body steps retain the full eye aperture in BOTH blink
                # directions; only the original closed pose is a short blink.
                self.assertGreater((array[..., 1] > 180).sum(), 550)
                np.testing.assert_array_equal(array[outside], opened[outside])

    def test_generated_grid_aligns_scale_baseline_and_transparency(self):
        # Image generation doesn't always return widths divisible by columns.
        grid = Image.new("RGBA", (126, 126))
        for row in range(2):
            for column in range(4):
                left = round(column * grid.width / 4)
                top = round(row * grid.height / 2)
                grid.paste((20, 140, 220, 255),
                           (left + 6, top + 18, left + 24, top + 50))
        frames = aligned_grid_frames(grid, 4, 2, (54, 72))
        self.assertEqual(len(frames), 8)
        baselines = []
        for frame in frames:
            self.assertEqual(frame.size, (54, 72))
            self.assertEqual(frame.getpixel((0, 0)), (0, 0, 0, 0))
            baselines.append(frame.getchannel("A").getbbox()[3])
        self.assertEqual(set(baselines), {round(72 * 0.91)})


if __name__ == "__main__":
    unittest.main()
