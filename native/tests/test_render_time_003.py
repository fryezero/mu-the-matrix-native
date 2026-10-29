"""RENDER-TIME-003 private installed-data checks of the two ported behaviours (opt-in, MU_RECOVERY_INTEGRATION=1).

* The wheel: without a UI layer the native route zooms (as the client does when its UI layer declines);
  with --wheel-ui-hit (the recorded live client's base.swf under the cursor) it refuses, as live did.
* The visible-object flag: CreateFrustrum/CreateFrustrum2D take GetScreenWidth (640 units), so at the same
  camera the visible count does not depend on the window size.
Paths come from MU_GAME_ROOT and MU_RENDER_TIME_OBJECTS; nothing is copied."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private installed-data checks are opt-in')
class InstalledWheelAndVisibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, cls.objects = os.environ.get('MU_GAME_ROOT'), os.environ.get('MU_RENDER_TIME_OBJECTS')
        if not (cls.root and Path(cls.root).is_dir() and cls.objects and Path(cls.objects).is_dir()):
            raise AssertionError('MU_GAME_ROOT and MU_RENDER_TIME_OBJECTS are required for this requested check')
        subprocess.run(['make', '-s', '-C', str(ROOT / 'native'), 'build/mu-world'], check=True)

    def run_world(self, width, height, script, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'wheel.input'
            path.write_text(script)
            run = subprocess.run([str(ROOT / 'native/build/mu-world'), '--headless', '--backend', 'gl', '--game-root',
                                  self.root, '--world', '0', '--tile', '137,129', '--width', str(width), '--height',
                                  str(height), '--no-audio', '--no-names', '--no-helpers', '--no-map', '--no-players',
                                  '--frames', '41', '--every', '40', '--out-dir', tmp, '--time-series-start-ms',
                                  '5474564', '--time-series-every', '10', '--input-script', str(path),
                                  '--objects-dir', self.objects, '--env-seed', '1', '--particle-seed', '1', *extra],
                                 capture_output=True, text=True, timeout=300)
        self.assertEqual(run.returncode, 0, run.stderr[-2000:])
        return [json.loads(line) for line in run.stdout.splitlines() if line.startswith('{"time_series"')]

    def test_wheel_refused_with_the_ui_layer_and_zooms_without(self):
        script = '0:focus:1 0:move:600,300 5:wheel:1\n'
        free = self.run_world(960, 600, script)
        taken = self.run_world(960, 600, script, '--wheel-ui-hit')
        self.assertEqual(free[0]['camera'][7], 39.0)
        self.assertLess(free[-1]['camera'][7], 39.0)                  # zoomed in towards FOV 30
        self.assertEqual([r['camera'][7] for r in taken], [39.0] * len(taken))
        self.assertEqual([r['camera'][6] for r in taken], [taken[0]['camera'][6]] * len(taken))

    def test_visible_objects_do_not_depend_on_the_window_size(self):
        small = self.run_world(640, 480, '0:focus:1\n')
        wide = self.run_world(960, 600, '0:focus:1\n')
        self.assertEqual(small[0]['camera'], wide[0]['camera'])
        self.assertEqual(small[0]['objects'][17], wide[0]['objects'][17])
        self.assertEqual(wide[0]['objects'][17], 198)                 # live run 3 at this camera (RENDER-TIME-002)


if __name__ == '__main__':
    unittest.main()
