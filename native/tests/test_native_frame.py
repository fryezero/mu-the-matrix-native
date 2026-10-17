"""Native frame-loop skeleton (NATIVE-FRAME-001) checks.

Portable: `mu-frame` (headless, software rasterizer, no client data) runs the
scripted input timeline and must show the client's fixed 40 ms logic steps,
the frame cap, the wheel FOV zoom sequence 35 -> 30 -> 20 -> 30 -> 35 with its
pitch, click-to-move targets from the reconstructed picking and deterministic
images. The SDL window tool builds and its headless GL path runs where SDL2
and a GL context exist (explicit skip otherwise). Private (MU_RECOVERY_INTEGRATION=1
and MU_GAME_ROOT): the same run with an installed model, written to a
temporary directory.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
TOOL = NATIVE / 'build/mu-frame'
WINDOW = NATIVE / 'build/mu-frame-window'


def frames(*args):
    result = subprocess.run([str(TOOL), *[str(a) for a in args]], capture_output=True, text=True, check=True)
    lines = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    return [l for l in lines if 'frame' in l], [l['log'] for l in lines if 'log' in l]


class FrameLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'build/mu-frame'], check=True, capture_output=True)

    def test_timeline(self):
        with tempfile.TemporaryDirectory() as folder:
            rows, log = frames('--out-dir', folder, '--frames', '180', '--every', '30')
            by_frame = {r['frame']: r for r in rows}
            pngs = sorted(p.name for p in Path(folder).glob('*.png'))
        # 12 ms of work per frame: the cap sleeps 28 ms, one logic step per frame
        for r in rows:
            self.assertEqual(r['logic_steps'], r['frame'] + 1)
        self.assertEqual(by_frame[179]['tick'] - by_frame[0]['tick'], 179 * 40)
        self.assertEqual(by_frame[0]['fov'], 35.0)
        self.assertEqual((by_frame[59]['fov'], by_frame[59]['angle'][0]), (30.0, -54.4231))
        self.assertEqual((by_frame[84]['fov'], by_frame[84]['angle'][0]), (20.0, -66.2692))
        self.assertEqual(by_frame[144]['fov'], 30.0)
        self.assertEqual((by_frame[164]['fov'], by_frame[164]['angle']), (35.0, [-48.5, 0.0, -45.0]))
        # transition frames lie strictly between the levels
        self.assertTrue(30.0 < by_frame[46]['fov'] < 35.0)
        self.assertEqual(by_frame[10]['target_tile'], [131, 128])
        self.assertEqual(by_frame[97]['target_tile'], [127, 130])
        self.assertEqual((by_frame[179]['picks'], by_frame[179]['hits']), (2, 2))
        self.assertIn('click-to-move: tile 131,128', log)
        self.assertIn('wheel: zoom index 0 -> fov 20.0', log)
        self.assertTrue(any(line.startswith('vk 0x49') for line in log))
        self.assertIn('frame-084.png', pngs)
        # the eye keeps the client offset from the hero: yaw -45, distance 1000, height 850
        r = by_frame[0]
        self.assertAlmostEqual(r['eye'][0] - r['hero'][0], 707.107, places=2)
        self.assertAlmostEqual(r['eye'][1] - r['hero'][1], -707.107, places=2)
        self.assertEqual(r['eye'][2], 850.0)

    def test_deterministic_images(self):
        first, _ = frames('--frames', '100', '--every', '25', '--out-dir', tempfile.mkdtemp())
        second, _ = frames('--frames', '100', '--every', '25', '--out-dir', tempfile.mkdtemp())
        self.assertEqual([r['sha256'] for r in first], [r['sha256'] for r in second])
        self.assertTrue(all(len(r['sha256']) == 64 for r in first if r['frame'] < 99))

    def test_slow_frames_catch_up(self):
        rows, _ = frames('--frames', '50', '--work', '100', '--every', '0', '--out-dir', tempfile.mkdtemp())
        last = rows[-1]
        # 100 ms frames: no sleep, 2-3 logic steps per frame, logic stays at 25 Hz
        self.assertGreaterEqual(last['logic_steps'], (last["tick"] - 100000) // 40 - 6)  # the last two frames are still in the accumulator
        self.assertLessEqual(last['logic_steps'], (last['tick'] - 100000) // 40 + 1)

    @unittest.skipUnless(shutil.which('sdl2-config'), 'SDL2 not installed')
    def test_window_tool_builds_and_renders_headless(self):
        subprocess.run(['make', '-C', str(NATIVE), 'frame-window'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([str(WINDOW), '--headless', '--frames', '30', '--out-dir', folder, '--width', '320',
                                     '--height', '240'], capture_output=True, text=True)
            if result.returncode and 'headless GL' in result.stderr:
                self.skipTest('no offscreen GL context: ' + result.stderr.strip())
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout.splitlines()[-1])
            self.assertEqual((summary['frames'], summary['logic_steps']), (30, 30))
            self.assertTrue(list(Path(folder).glob('gl-frame-*.png')))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT'),
                         'private: needs MU_GAME_ROOT')
    def test_private_installed_model(self):
        model = Path(os.environ['MU_GAME_ROOT']) / 'Data/Monster/Monster02.bmd'
        with tempfile.TemporaryDirectory() as folder:
            rows, log = frames(model, '--out-dir', folder, '--frames', '100', '--every', '50')
            self.assertEqual(rows[-1]['logic_steps'], 100)
            self.assertIn('click-to-move: tile 131,128', log)
            self.assertTrue((Path(folder) / 'frame-050.png').exists())


if __name__ == '__main__':
    unittest.main()
