import unittest
import numpy as np
from PIL import Image, ImageDraw
from motion_stabilization import body_anchor, stabilize_frames
from animation_clock import frame_index_at


class StabilizationTests(unittest.TestCase):
    @staticmethod
    def frame(dx=0, dy=0, particle_x=10):
        image = Image.new('RGBA', (160, 160))
        draw = ImageDraw.Draw(image)
        draw.ellipse((32+dx, 34+dy, 125+dx, 128+dy), fill=(240, 235, 248, 255))
        draw.ellipse((46+dx, 47+dy, 112+dx, 94+dy), fill=(20, 24, 51, 255))
        draw.ellipse((particle_x, 5, particle_x+12, 17), fill=(0, 220, 255, 220))
        return image

    def test_anchors_ignore_moving_cyan_effect(self):
        left, right = self.frame(particle_x=4), self.frame(particle_x=135)
        ax, ay = body_anchor(left)
        bx, by = body_anchor(right)
        self.assertAlmostEqual(ax, bx, delta=0.001)
        self.assertAlmostEqual(ay, by, delta=0.001)

    def test_corrects_small_misalignment_without_ghosting(self):
        images = [self.frame(dx=-8,dy=5),self.frame(dx=8,dy=-5)]
        aligned = stabilize_frames(images)
        a,b = [body_anchor(im) for im in aligned]
        self.assertAlmostEqual(a[0],b[0],delta=1)
        self.assertAlmostEqual(a[1],b[1],delta=1)
        for frame in aligned:
            self.assertTrue(set(np.unique(np.asarray(frame)[..., 3])).issubset({0, 220,255}))

    def test_stabilizer_keeps_unrecognized_images(self):
        black = Image.new('RGBA',(20,20),(10,20,30,255))
        self.assertEqual(stabilize_frames([black])[0].tobytes(),black.tobytes())

    def test_clock_keeps_total_loop_duration_when_frames_double(self):
        for intermediates in (3,7):
            frame_count = 8 * (intermediates+1)
            self.assertEqual(frame_index_at(0,frame_count,5,intermediates,.65),0)
            self.assertEqual(frame_index_at(8/3.25,frame_count,5,intermediates,.65),0)
            self.assertEqual(frame_index_at(1/3.25,frame_count,5,intermediates,.65),intermediates+1)

    def test_clock_skips_missed_ticks_not_slow_motion(self):
        self.assertEqual(frame_index_at(.5,64,5,7,.65),13)


if __name__ == '__main__':
    unittest.main()
