"""Portable checks of the reconstructed character-select scene (no client
bytes). The instruction comparison against the client is
scripts/validate_charsel.py; its private run is gated by MU_RECOVERY_INTEGRATION."""
import ctypes
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('validate_charsel', ROOT / 'scripts/validate_charsel.py')
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)

RECORD, OBJECT = 0x3670, 0x3254


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def fb(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


class Table:
    def __init__(self, count=20):
        self.buffers = [ctypes.create_string_buffer(RECORD) for _ in range(count)]
        self.fn = V.CHARFN(lambda context, index: ctypes.addressof(self.buffers[index]))

    def f(self, index, offset, n=1):
        values = struct.unpack_from(f'<{n}f', self.buffers[index].raw, offset)
        return values if n > 1 else values[0]

    def setf(self, index, offset, *values):
        struct.pack_into(f'<{len(values)}f', self.buffers[index], offset, *values)

    def u16(self, index, offset):
        return struct.unpack_from('<H', self.buffers[index].raw, offset)[0]


def events(log):
    return V.c_events(log)


class CharselTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = V.load_library()

    def scene(self):
        scene = V.Scene()
        for k in range(5):
            for i in range(3):
                scene.position[k][i] = 1000.0 * k + i
                scene.angle[k][i] = 10.0 * k + i
        return scene

    def test_every_slot_takes_marker_one(self):
        table, scene = Table(), self.scene()
        for slot in (0, 3, 4, 9):
            self.assertEqual(self.lib.mu_charsel_set_character_position(ctypes.byref(scene), slot, table.fn, None), 1)
            self.assertEqual(table.f(slot, OBJECT + 0x158, 3), (1000.0, 1001.0, 1002.0))
            self.assertEqual(table.f(slot, OBJECT + 0x164, 3), (10.0, 11.0, 12.0))
        for slot in (-1, 400, 0x7fffffff):
            self.assertEqual(self.lib.mu_charsel_set_character_position(ctypes.byref(scene), slot, table.fn, None), 0)

    def test_create_object_markers(self):
        table, scene = Table(), V.Scene()
        yaws = []
        for k, type_ in enumerate(range(0x0d, 0x12)):
            obj = V.MapObject(type_, (100.0 * k, 200.0 * k, 169.5), 7, 7, 3.0)
            self.assertEqual(self.lib.mu_charsel_create_object(ctypes.byref(scene), 0x5d, ctypes.byref(obj),
                                                               table.fn, None), 1)
            self.assertEqual((obj.field_64, obj.field_68, obj.field_c0), (0, -2, 3.0))
            self.assertEqual(list(scene.position[k]), [100.0 * k, 200.0 * k, 169.5])
            yaws.append(scene.angle[k][2])
        self.assertEqual(yaws, [115.0, 90.0, 75.0, 60.0, 35.0])
        # every character sits on marker 1 once it has been created
        self.assertEqual(table.f(4, OBJECT + 0x158, 3), (100.0, 200.0, 169.5))
        self.assertEqual(table.f(4, OBJECT + 0x164 + 8), 90.0)
        obj = V.MapObject(0x3c, (0, 0, 0), 7, 7, 3.0)
        self.lib.mu_charsel_create_object(ctypes.byref(scene), 0x5d, ctypes.byref(obj), table.fn, None)
        self.assertEqual((obj.field_68, obj.field_c0), (7, f32(-428.571442)))
        obj = V.MapObject(0x0d, (0, 0, 0), 7, 7, 3.0)
        self.assertEqual(self.lib.mu_charsel_create_object(ctypes.byref(scene), 0x5c, ctypes.byref(obj),
                                                           table.fn, None), 0)
        self.assertEqual((obj.field_64, obj.field_68), (7, 7))

    def test_scale(self):
        table = Table()
        for cls, expect_part1 in ((0x01, 0.0), (0x0b, f32(0.95))):
            buf = table.buffers[2]
            buf[0x12] = cls
            log = V.Log()
            inputs = V.ScaleInputs(5, 0x5d, 0, 0, 0)
            self.lib.mu_charsel_character_scale(ctypes.addressof(buf), 0x40020000, ctypes.byref(inputs),
                                                ctypes.byref(log))
            self.assertEqual(table.f(2, OBJECT + 0xa0), f32(1.7))
            self.assertEqual(table.f(2, 0x1c4 + 0x3fc + 0xc4), expect_part1)
            self.assertEqual(table.u16(2, 0x1c4), 0xffff)        # helm 0: no face
            self.assertEqual(events(log), [(0x009dacb8, (0x5d,))])
        # in the world: class table, then the 0x1a8/0x1a9 buff checks
        buf = table.buffers[3]
        buf[0x12] = 0x0e
        struct.pack_into('<H', buf, 0x1c4 + 0x3fc, 0x192a)       # a helm that shows the face
        log = V.Log()
        inputs = V.ScaleInputs(6, 0, 0, 0, 1)
        self.lib.mu_charsel_character_scale(ctypes.addressof(buf), 0x40030000, ctypes.byref(inputs),
                                            ctypes.byref(log))
        self.assertEqual(table.f(3, OBJECT + 0xa0), f32(1.1))
        self.assertEqual(table.u16(3, 0x1c4), 0x3700 + 0x0e)
        self.assertEqual([e[1] for e in events(log)][1:], [(0x400335ac, 0x1a8), (0x400335ac, 0x1a9)])

    def test_create_hero_parts_and_order(self):
        table = Table()
        log = V.Log()
        inputs = V.ScaleInputs(5, 0x5d, 0, 0, 0)
        address = self.lib.mu_charsel_create_hero(2, 0x21, 0, 8000.0, 19000.0, 90.0, ctypes.byref(inputs), table.fn,
                                                  None, ctypes.byref(log))
        self.assertEqual(address, ctypes.addressof(table.buffers[2]))
        skin = 0x01 + 16 * 2      # class 0x21: base 1, tier 3
        self.assertEqual([table.u16(2, 0x1c4 + 0x3fc * k) for k in range(1, 6)],
                         [0x3700 + skin, 0x3750 + skin, 0x37a0 + skin, 0x37f0 + skin, 0x3840 + skin])
        self.assertEqual([table.u16(2, o) for o in (0x19ac, 0x19ac + 0x3fc, 0x21a4, 0x299c)], [0xffff] * 4)
        self.assertEqual(table.f(2, OBJECT + 0xec, 3), (f32(0.3),) * 3)
        self.assertEqual(table.f(2, OBJECT + 0xa0), f32(1.7))
        self.assertEqual([e[0] for e in events(log)],
                         [0x0137d8a1, 0x01295f18, 0x0129dc78, 0x0128ed7d, 0x009dacb8, 0x0138fe69])
        self.assertEqual(events(log)[0][1], (0x40020000, 0xa91, 0, 0, fb(90.0)))

    def frame(self, selected=1, shown=1, t=12345.0):
        f = V.Frame()
        f.initialised, f.protocol, f.selected, f.shown, f.world_time = 1, 0x35, selected, shown, t
        f.pick, f.screen_width = -1, 1024
        return f

    def test_render_selection(self):
        table = Table()
        for i in range(10):
            table.buffers[i][OBJECT] = 1            # live
            table.buffers[i][OBJECT + 0x0b] = 1     # visible
            struct.pack_into('<i', table.buffers[i], OBJECT + 0x5c, 0xa91)
            table.setf(i, OBJECT + 0xec, 0.5, 0.5, 0.5)
        struct.pack_into('<H', table.buffers[3], 0x322e, 0x1a03)
        fog, log = ctypes.c_uint8(1), V.Log()
        f = self.frame(selected=1, shown=1)
        self.assertEqual(self.lib.mu_charsel_render(ctypes.byref(f), table.fn, None, ctypes.byref(fog),
                                                    ctypes.byref(log)), 1)
        self.assertEqual(fog.value, 0)
        self.assertEqual(table.f(3, OBJECT + 0x160), 194.5)
        self.assertEqual(table.f(4, OBJECT + 0x160), 169.5)
        self.assertEqual(table.f(1, OBJECT + 0xec, 3), (f32(0.15),) * 3)   # after the highlight
        self.assertEqual(table.f(2, OBJECT + 0xec, 3), (0.0, 0.0, 0.0))
        ev = events(log)
        decals = [e[1] for e in ev if e[0] == 0x016cdd5f]
        self.assertEqual(len(decals), 2)
        lum = f32(f32(f32(math.sin(f32(12345.0 * f32(0.0015)))) * f32(0.3)) + 0.5)
        self.assertEqual(decals[0][5], fb(lum))
        self.assertEqual((decals[0][3], decals[1][3]), (fb(1.8), fb(1.2)))
        self.assertEqual((decals[0][8], decals[1][8]), (fb(f32(12345.0 * f32(0.01))), fb(f32(-12345.0 * f32(0.01)))))
        self.assertIn((0x01363260, (0x40010000, 0x40013254, 0)), ev)
        # only the shown character is drawn; none when it is not visible
        table.buffers[1][OBJECT + 0x0b] = 0
        log = V.Log()
        self.lib.mu_charsel_render(ctypes.byref(f), table.fn, None, ctypes.byref(fog), ctypes.byref(log))
        self.assertNotIn(0x01363260, [e[0] for e in events(log)])
        # no character list yet
        f.protocol = 0x32
        self.assertEqual(self.lib.mu_charsel_render(ctypes.byref(f), table.fn, None, ctypes.byref(fog),
                                                    ctypes.byref(log)), 0)

    def test_tick_enter_takes_shown(self):
        t = V.Tick()
        t.scene, t.initialised, t.protocol, t.selected, t.shown, t.key_enter = 5, 1, 0x35, 0, 3, 1
        log = V.Log()
        self.lib.mu_charsel_tick_step(ctypes.byref(t), ctypes.byref(log))
        self.assertEqual(t.selected, 3)
        calls = [e[0] for e in events(log)]
        self.assertEqual(calls[-3:], [0x00a6ac96, 0x009a5029, 0x0185a75a])
        t.selected, t.enter_refused = 0, 1
        log = V.Log()
        self.lib.mu_charsel_tick_step(ctypes.byref(t), ctypes.byref(log))
        self.assertNotIn(0x0185a75a, [e[0] for e in events(log)])
        t.selected = -1
        log = V.Log()
        self.lib.mu_charsel_tick_step(ctypes.byref(t), ctypes.byref(log))
        self.assertEqual(t.selected, -1)   # nothing selected: Enter does nothing


class PrivateCharselValidation(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned client captures')
    def test_instruction_comparison(self):
        text = os.environ.get('MU_CLIENT_TEXT', str(ROOT / 'evidence/x86-text-capture-09/client-text.bin'))
        data = os.environ.get('MU_IMAGE_DATA',
                              str(ROOT / 'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'charsel.json'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_charsel.py'), '--text', text,
                                     '--data', data, '--cases', '60', '--mutations', '--output', str(report)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
            parsed = json.loads(report.read_text())
        self.assertTrue(all(r['mismatches'] == 0 for r in parsed['results'].values()))
        self.assertTrue(all(m['mismatches'] > 0 for m in parsed['mutations']))


if __name__ == '__main__':
    unittest.main()
