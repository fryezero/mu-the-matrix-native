"""RENDER-TIME-003: GetScreenWidth 0x016bc355 and the WM_MOUSEWHEEL route (client_wheel.c).

The portable tests use the C library only (synthetic inputs). The private test runs the instruction comparison
scripts/validate_wheel_route.py against the pinned client captures."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_wheel_route as w  # noqa: E402
import validate_camera as vc  # noqa: E402


def env(**kw):
    e = w.Env()
    state = {'hits': kw.pop('hits', [0, 0]), 'dispatch': kw.pop('dispatch', [0, 0]), 'log': []}
    e.dispatch = w.Env.DISPATCH(lambda c, n, m, wp, p: (state['log'].append(('dispatch', n, p)),
                                                        state['dispatch'][n])[1])
    e.hit_test = w.Env.HIT(lambda c, x, y: (state['log'].append(('hit', x, y)),
                                            state['hits'][sum(1 for t in state['log'] if t[0] == 'hit') - 1])[1])
    e.event = w.Env.EVENT(lambda c, t, x, y, lines: state['log'].append(('event', t, x, y, lines)))
    e.window_open = w.Env.OPEN(lambda c, i: (state['log'].append(('window', i)), kw.get('window3e', 0))[1])
    e.origin_x, e.origin_y = kw.pop('origin', (420, 297))
    e.base_movie = kw.pop('base_movie', 1)
    e.gfx_input = 1
    for k, v in kw.items():
        if k != 'window3e':
            setattr(e, k, v)
    return e, state


def lorencia():
    c = vc.WorldCamera()
    c.scene, c.world, c.world_fov = 6, 0, 39.0
    c.distance = c.distance_target = 1000.0
    c.zoom_timer.done, c.zoom_index = 1, 2
    v = vc.View()
    v.fov = 39.0
    return c, v


class WheelRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = w.load_library()

    def wheel(self, e, delta=120, screen=(1020, 597)):
        c, v = lorencia()
        m = vc.Mouse()
        flag = ctypes.c_uint8(0)
        lparam = (screen[1] << 16) | screen[0]
        stage = self.lib.mu_client_mouse_wheel(ctypes.byref(c), ctypes.byref(v), ctypes.byref(m), ctypes.byref(e),
                                               (delta & 0xffff) << 16, lparam, 0, ctypes.byref(flag))
        return stage, c, m, flag.value

    def test_screen_width(self):
        def width(opened):
            return self.lib.mu_client_screen_width(w.Env.OPEN(lambda c, i: int(i in opened)), None)
        self.assertEqual(width(set()), 640)
        self.assertEqual(width({0x10}), 450)       # one side window
        self.assertEqual(width({0x0d, 0x10}), 260)
        self.assertEqual(width({0x08}), 260)
        self.assertEqual(width({0x4b}), 70)
        self.assertEqual(width({0x4a, 0x4b}), 260)

    def test_base_movie_hit_takes_the_wheel(self):
        # The recorded Lorencia case: every memory-held guard clear; base.swf under the cursor takes it.
        e, state = env(hits=[1, 0])
        stage, c, m, flag = self.wheel(e)
        self.assertEqual((stage, c.zoom_index, m.wheel, flag), (1, 2, 1, 1))
        self.assertEqual(state['log'][0], ('dispatch', 0, (300 << 16) | 600))   # client point 600,300
        self.assertEqual(state['log'][1][:2], ('event', 4))
        self.assertEqual(state['log'][1][4], 3.0)                              # three lines per notch
        self.assertNotIn('window', [t[0] for t in state['log']])

    def test_raw_lparam_hit_takes_the_wheel(self):
        e, state = env(hits=[0, 1])
        stage, c, m, flag = self.wheel(e)
        self.assertEqual((stage, c.zoom_index), (1, 2))
        self.assertEqual(state['log'][3][1:], (1020.0, 597.0))

    def test_zooms_where_the_original_allows_it(self):
        e, state = env()
        stage, c, m, flag = self.wheel(e)
        self.assertEqual((stage, c.zoom_index, c.fov_to, m.wheel, flag), (4, 1, 30.0, 1, 0))
        e, state = env(hero_busy=1)                # the UI layer declines without asking base.swf
        stage, c, m, flag = self.wheel(e, delta=-120)
        self.assertEqual((stage, c.zoom_index), (4, 2))
        self.assertNotIn('hit', [t[0] for t in state['log']])

    def test_game_case_and_handler_guards(self):
        for kw, stage in [({'chat_in_view': 1}, 2), ({'gfx_window6': 1}, 2), ({'gfx_input': 0}, 2),
                          ({'dispatch': [0, 1]}, 2), ({'window3e': 1}, 3)]:
            e, state = env(**kw)
            got, c, m, flag = self.wheel(e)
            self.assertEqual((got, c.zoom_index, m.wheel), (stage, 2, 1), kw)


class PrivateWheelValidation(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned client captures')
    def test_instruction_comparison(self):
        text = os.environ.get('MU_CLIENT_TEXT', str(ROOT / 'evidence/x86-text-capture-09/client-text.bin'))
        data = os.environ.get('MU_IMAGE_DATA',
                              str(ROOT / 'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'wheel.json'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_wheel_route.py'), '--text', text,
                                     '--data', data, '--cases', '60', '--mutations', '--output', str(report)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
            parsed = json.loads(report.read_text())
        self.assertTrue(all(r['mismatches'] == 0 for r in parsed['results'].values()))
        self.assertTrue(all(m['mismatches'] > 0 for m in parsed['mutations']))
        self.assertEqual(len(parsed['mutations']), 10)


if __name__ == '__main__':
    unittest.main()
