"""Portable checks of the reconstructed scene manager (no client bytes).

The instruction comparison against the client is scripts/validate_scene.py;
its private run is gated by MU_RECOVERY_INTEGRATION and the pinned captures."""
import ctypes
import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('validate_scene', ROOT / 'scripts/validate_scene.py')
V = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(ROOT / 'scripts'))
spec.loader.exec_module(V)

TEXT = Path(os.environ.get('MU_CLIENT_TEXT', ROOT / 'evidence/x86-text-capture-09/client-text.bin'))
DATA = Path(os.environ.get('MU_IMAGE_DATA', ROOT / 'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'


class Host:
    """A host over a dict memory that records the call stream."""

    def __init__(self, returns=None, memory=None):
        self.calls, self.writes = [], []
        self.returns = returns or {}
        self.memory = memory or {}
        self.c = V.Host(None, V.CALLFN(self.call), V.PEEKFN(self.peek), V.POKEFN(self.poke))

    def call(self, user, pointer):
        c = pointer.contents
        args = tuple(c.args[i] for i in range(c.count))
        self.calls.append((c.routine, c.ecx, args, c.text.decode() if c.text else None))
        value = self.returns.get(c.routine, 0)
        return value(args) if callable(value) else value

    def peek(self, user, address, size):
        return int.from_bytes(bytes(self.memory.get(address + i, 0) for i in range(size)), 'little')

    def poke(self, user, address, value, size):
        self.writes.append((address, size, value))
        for i in range(size):
            self.memory[address + i] = (value >> (8 * i)) & 0xff

    def routines(self):
        return [c[0] for c in self.calls]


class SceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/scene')], check=True)
        cls.lib = V.library()

    def globals(self, **values):
        g = V.Globals()
        g.music_login = 0x1000
        for k, v in values.items():
            setattr(g, k, v)
        return g

    def test_dispatch_targets(self):
        expected = {2: 1, 3: 3, 4: 2, 5: 3, 6: 3}
        for scene in range(-3, 12):
            self.assertEqual(self.lib.mu_scenemgr_dispatch_target(scene), expected.get(scene, 0), scene)
        for scene, routine in ((2, 0x0185ad63), (4, 0x01851adc), (3, 0x01851d39), (5, 0x01851d39),
                               (6, 0x01851d39)):
            h, g = Host(), self.globals(scene=scene)
            self.lib.mu_scenemgr_dispatch(ctypes.byref(h.c), ctypes.byref(g), 0x1234)
            self.assertIn((routine, 0, (0x1234,), None), h.calls)
            self.assertEqual(h.calls[-1][0], 0x00ac9be9)   # observer with the scene value
            self.assertEqual(h.calls[-1][2], (scene,))
        h, g = Host(), self.globals(scene=3, send_counter=40)
        self.lib.mu_scenemgr_dispatch(ctypes.byref(h.c), ctypes.byref(g), 1)
        self.assertIn(V.NET_SEND, h.routines())

    def test_intro_loads_title_and_goes_to_login(self):
        for variant, first in ((0, 'Interface\\lo_back_s5_im01.jpg'), (1, 'Interface\\MuBattle_loading01.jpg')):
            h = Host(returns={0x0095f75d: 0x2000, 0x01a7c49c: 777}, memory={0x2004: variant})
            g = self.globals(scene=2)
            self.lib.mu_scenemgr_intro(ctypes.byref(h.c), ctypes.byref(g), 9)
            loads = [c for c in h.calls if c[0] == 0x0185baac]
            self.assertEqual(len(loads), 15)
            self.assertEqual([c[2][1] for c in loads], list(range(0x7b81, 0x7b8f)) + [0x7c80])
            self.assertEqual(loads[8][3], first)
            self.assertEqual(loads[5][2][3], 0x2901)   # lo_lo.jpg repeats
            render = [c for c in h.calls if c[0] == 0x011e2c8c]
            self.assertEqual(render[0][2], (9, 9, 9))  # the final title frame: progress 9 of 9
            deletes = [c[2][0] for c in h.calls if c[0] == 0x0185bc1b]
            self.assertEqual(deletes, list(range(0x7b81, 0x7b8f)))
            self.assertEqual(g.scene, 3)
            self.assertEqual(g.frame_tick, 777)
            self.assertIn(0x00a05a22, h.routines())
        h, g = Host(), self.globals(scene=3)
        self.lib.mu_scenemgr_intro(ctypes.byref(h.c), ctypes.byref(g), 9)
        self.assertNotIn(0x00a05a22, h.routines())   # already 3: no notification

    def test_login_create(self):
        h = Host(returns={0x0195a4b0: 5})
        g = self.globals(scene=3, protocol=0x33, remember_id=0, id_buffer=0x0b436580)
        self.lib.mu_scenemgr_login_create(ctypes.byref(h.c), ctypes.byref(g))
        self.assertEqual((g.world, g.world_folder, g.protocol), (0x5e, 0x5e, 0))
        self.assertIn((0x0182876e, 0, (0x5e,), None), h.calls)
        self.assertIn((0x0120f602, 0, (0x1000,), None), h.calls)   # PlayMp3(login theme)
        self.assertEqual((g.id_length, g.id_present, g.id_field_1118), (5, 1, 10))
        self.assertEqual(struct.pack('<f', g.login_fade), bytes(4))

    def test_login_tail_needs_protocol_0x14(self):
        for protocol, scene in ((0x13, 3), (0x14, 5), (0x33, 3)):
            h, g = Host(), self.globals(scene=3, protocol=protocol)
            self.lib.mu_scenemgr_login_tick_tail(ctypes.byref(h.c), ctypes.byref(g))
            self.assertEqual(g.scene, scene)
            if scene == 5:
                self.assertEqual(h.calls[0][3], '> Request Character list\r\n')

    def test_frame_music(self):
        for scene in range(0, 8):
            h, g = Host(), self.globals(scene=scene)
            self.lib.mu_scenemgr_frame_music(ctypes.byref(h.c), ctypes.byref(g))
            self.assertEqual(h.calls, [(0x0120f602 if scene in (3, 5) else 0x0120f5a0, 0, (0x1000,), None)])

    def test_start_loading(self):
        record, hero = 0x3000, 0x5000
        memory = {V.HERO_POINTER + i: (hero >> (8 * i)) & 0xff for i in range(4)}
        memory.update({record + 0x12: 0x21, record + 0x13: 3, record + 0x14: 0})
        h = Host(returns={0x009a13f4: record, 0x00ac3bf7: 0x7000, 0x009a595b: 0x8000}, memory=dict(memory))
        g = self.globals(scene=5, selected_hero=2, init_loading=1)
        self.lib.mu_scenemgr_start_loading(ctypes.byref(h.c), ctypes.byref(g), 1)
        self.assertEqual((g.scene, g.init_loading), (4, 0))
        self.assertIn((hero + 0x187, 1, 0x21), h.writes)
        self.assertIn((hero + 0x188, 1, 3), h.writes)
        # a blocked character (flag bit 0) opens message box 0x84 instead
        memory[record + 0x14] = 1
        h = Host(returns={0x009a13f4: record, 0x011e228b: 0x9000}, memory=memory)
        g = self.globals(scene=5, selected_hero=2)
        self.lib.mu_scenemgr_start_loading(ctypes.byref(h.c), ctypes.byref(g), 1)
        self.assertEqual(g.scene, 5)
        self.assertEqual(h.calls[-1][:3], (0x011e3598, 0x9000, (0x84, 0)))
        # start = 0 only asks the server (network send) and stores the selection
        h = Host(returns={0x009a13f4: record, 0x00ac3bf7: 0x7000}, memory={0x7000 + 0x22c: 0x40})
        g = self.globals(scene=5, selected_hero=3)
        self.lib.mu_scenemgr_start_loading(ctypes.byref(h.c), ctypes.byref(g), 0)
        self.assertEqual(g.scene, 5)
        self.assertIn(V.NET_SEND, h.routines())
        self.assertEqual(h.writes, [(0x40 + 0x98, 4, 3)])

    def test_loading_scene(self):
        ui = 0x10000
        h = Host(returns={0x011e228b: ui, 0x0191ba7b: 0x20000, 0x00cdb6ca: 0x20000, 0x01989721: 12345})
        g = self.globals(scene=4, init_loading=0)
        self.lib.mu_scenemgr_loading(ctypes.byref(h.c), ctypes.byref(g), 7)
        paths = [c[3] for c in h.calls if c[0] == 0x0185baac]
        self.assertEqual(paths, [f'Interface\\LSBg01_{i}.JPG' for i in range(1, 5)])
        self.assertIn((0x0120f5a0, 0, (0x1000,), None), h.calls)   # StopMp3(login theme)
        order = [r for r in h.routines() if r in (0x00cdb74c, 0x0184adc7, 0x00cdb94f, 0x01a7c148, 0x56434c4c)]
        self.assertEqual(order, [0x00cdb74c, 0x0184adc7, 0x00cdb94f, 0x01a7c148, 0x56434c4c])
        self.assertEqual((g.scene, g.init_loading, g.loading_world), (6, 1, 9999999))
        self.assertEqual(h.writes[-1], (ui + 0x6598, 4, 0))
        self.assertEqual([c[2][0] for c in h.calls if c[0] == 0x0185bc1b], [0x7b81, 0x7b82, 0x7b83, 0x7b84])

    def test_return_to_character(self):
        g = self.globals(scene=6, init_character=1, init_main=1, protocol=0x33)
        self.lib.mu_scenemgr_return_to_character(ctypes.byref(g))
        self.assertEqual((g.scene, g.init_character, g.init_main, g.protocol), (5, 0, 0, 0))

    @unittest.skipUnless(PRIVATE and TEXT.exists() and DATA.exists(), 'private: MU_RECOVERY_INTEGRATION=1 and the pinned captures')
    def test_private_instruction_comparison(self):
        try:
            import unicorn  # noqa: F401
        except ImportError:
            self.skipTest('unicorn is not installed')
        V.main(['--text', str(TEXT), '--data', str(DATA), '--cases', '25', '--loading-ui-cases', '10'])


if __name__ == '__main__':
    unittest.main()
