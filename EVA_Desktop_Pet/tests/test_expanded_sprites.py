import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from expanded_sprites import fixed_grid_frames, load_expanded_sheets


class ExpandedSpritesTests(unittest.TestCase):
    def test_rounding_and_fixed_alignment(self):
        sheet = Image.new("RGBA", (1254, 1254))
        draw = ImageDraw.Draw(sheet)
        for row in range(4):
            for col in range(4):
                x = round(col * 1254 / 4) + 120
                y = round(row * 1254 / 4) + 120
                draw.rectangle((x, y, x + 20, y + 20), fill=(255, 255, 255, 255))
        frames = fixed_grid_frames(sheet)
        self.assertEqual(len(frames), 16)
        self.assertEqual({f.size for f in frames}, {(543, 724)})
        bounds = [f.getchannel("A").getbbox() for f in frames]
        for axis in range(4):
            self.assertLessEqual(
                max(b[axis] for b in bounds) - min(b[axis] for b in bounds), 3
            )

    def test_missing_assets_are_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "expanded"
            folder.mkdir()
            (folder / "present.png").write_bytes(b"example")
            (folder / "manifest.json").write_text(json.dumps({
                "format": "eva-4x4-v1", "columns": 4, "rows": 4,
                "states": {
                    "idle": "present.png", "sad": "missing.png",
                    "escape": "../outside.png"
                }
            }), encoding="utf-8")
            self.assertEqual(
                list(load_expanded_sheets(Path(temp))), ["idle"]
            )


if __name__ == "__main__":
    unittest.main()
