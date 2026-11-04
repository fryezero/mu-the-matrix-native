"""RENDER-WORLDS-AFTER6: the action registry's tick handlers 4, 6 (the mouse over the object's OBB) and 8 (the
camera -> hero fade) in reconstructed/objects/action_registry.c: portable synthetic checks, and the private
instruction comparison (validate_worlds_after6)."""
import ctypes as C
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_object_render as v  # noqa: E402
import validate_worlds_after5 as wa5  # noqa: E402
import validate_worlds_after6 as wa6  # noqa: E402
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
LANG_DIR = os.environ.get('MU_ANIM_LANG_DIR')   # optional: a local lang dir with mapanim.tsv (live_rows)

FADE = (200, 200, 400, 0, 0, 0, 7)   # size x, y, z; offset x, y, z; rate


def row(kind, action, speed, handler, param=300, extra=()):
    return {'type': kind, 'action': action, 'speed': v.f32(speed), 'handler': handler, 'param': param,
            'extra': list(extra)}


def vec(values):
    return C.cast((C.c_float * 3)(*values), wa6.FPTR) if values is not None else None


class WorldsAfter6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = wa6.build(ROOT / 'reconstructed')

    def tick(self, entries, kind=13, current=0, frame=0.0, records=((20, 0), (10, 1)), hero=(0.0, 0.0, 0.0),
             camera=None, mouse=None, latch=0, angle_z=0.0, scale=1.0):
        obj = bytearray(v.OBJ_SIZE)
        struct.pack_into('<i', obj, 0x5c, kind)
        struct.pack_into('<H', obj, 0x2a, current)
        struct.pack_into('<f', obj, 0xd0, frame)
        struct.pack_into('<f', obj, 0xbc, 0.16)
        struct.pack_into('<ii', obj, 0x30, 0, latch)
        struct.pack_into('<3f', obj, 0x158, 1000.0, 1000.0, 0.0)
        struct.pack_into('<3f', obj, 0x164, 0.0, 0.0, angle_z)
        struct.pack_into('<f', obj, 0xa0, scale)
        struct.pack_into('<f', obj, 0xd8, 0.5)
        # the OBB +0x31c: 900..1100 x 900..1100 x 0..400
        struct.pack_into('<12f', obj, 0x31c, 900, 900, 0, 200, 0, 0, 0, 200, 0, 0, 0, 400)
        entries = [dict(e) for e in entries]
        keep = []
        table = (wa5.AnimEntry * len(entries))()
        for i, e in enumerate(entries):
            extra = (C.c_int32 * max(1, len(e['extra'])))(*e['extra'])
            keep.append(extra)
            table[i] = wa5.AnimEntry(e['type'], e['action'], e['speed'], e['handler'], e['param'], len(e['extra']),
                                     C.cast(extra, C.POINTER(C.c_int32)))

        def model(ctx, k, action, count, keys, lock):
            count[0] = len(records)
            if 0 <= action < len(records):
                keys[0], lock[0] = records[action]
            return 1
        model_fn, rand_fn = wa5.MODEL_FN(model), v.RAND_FN(lambda c: 0)
        start, end = (mouse if mouse else (None, None))
        pointers = [vec(camera), vec(start), vec(end)]
        inputs = wa6.AnimInputs(C.cast(table, C.POINTER(wa5.AnimEntry)), len(entries), model_fn, rand_fn, None,
                                (C.c_float * 3)(*hero), *pointers)
        buf = C.create_string_buffer(bytes(obj), v.OBJ_SIZE)
        found = C.c_int(0)
        status = self.lib.dll.mu_action_tick(buf, C.byref(inputs), C.byref(found))
        out = buf.raw
        get = lambda fmt, off: struct.unpack_from(fmt, out, off)[0]   # noqa: E731
        return status, {'action': get('<H', 0x2a), 'latch': get('<i', 0x34), 'alpha_target': get('<f', 0xd8),
                        'velocity': get('<f', 0xbc)}

    def test_fade_face_hit(self):
        # coarse box 600..1400 x 600..1400 x 0..400; the segment crosses the face x = 1100
        status, o = self.tick([row(13, 0, 0.16, 8, extra=FADE)], hero=(1300.0, 1000.0, 100.0),
                              camera=(500.0, 1000.0, 300.0))
        self.assertEqual((status, o['alpha_target']), (1, v.f32(0.1)))

    def test_fade_coarse_only(self):
        # above the hero: inside the coarse box's x/y but beside the object's box
        status, o = self.tick([row(13, 0, 0.16, 8, extra=FADE)], hero=(1300.0, 1000.0, 100.0),
                              camera=(1300.0, 1000.0, 2000.0))
        self.assertEqual((status, o['alpha_target']), (1, 1.0))

    def test_fade_turned_box(self):
        # the box turned by 90 degrees about z still covers 900..1100 (square); a 400 x 100 box turned by 90
        # covers 950..1050 in x, so the segment at y = 1150 misses it but crosses the unturned one
        thin = (400, 100, 400, 0, 0, 0, 7)
        hero, camera = (1000.0, 1300.0, 100.0), (1000.0, 600.0, 300.0)
        _, plain = self.tick([row(13, 0, 0.16, 8, extra=thin)], hero=(1150.0, 1300.0, 100.0),
                             camera=(1150.0, 600.0, 300.0))
        _, turned = self.tick([row(13, 0, 0.16, 8, extra=thin)], hero=(1150.0, 1300.0, 100.0),
                              camera=(1150.0, 600.0, 300.0), angle_z=90.0)
        self.assertEqual((plain['alpha_target'], turned['alpha_target']), (v.f32(0.1), 1.0))
        _, centre = self.tick([row(13, 0, 0.16, 8, extra=thin)], hero=hero, camera=camera, angle_z=90.0)
        self.assertEqual(centre['alpha_target'], v.f32(0.1))

    def test_fade_far_and_sizes(self):
        status, o = self.tick([row(13, 0, 0.16, 8, extra=FADE)], hero=(5000.0, 5000.0, 0.0),
                              camera=(5000.0, 4000.0, 1000.0))
        self.assertEqual((status, o['alpha_target']), (1, 0.5))   # no coarse hit: unchanged
        for extra in (FADE[:6], FADE + (1,), ()):
            status, o = self.tick([row(13, 0, 0.16, 8, extra=extra)], hero=(1300.0, 1000.0, 100.0),
                                  camera=(500.0, 1000.0, 300.0))
            self.assertEqual((status, o['alpha_target']), (1, 0.5))   # not seven extras: nothing
        status, _ = self.tick([row(13, 0, 0.16, 8, extra=FADE)], hero=(1300.0, 1000.0, 100.0), camera=None)
        self.assertEqual(status, 2)   # no camera: unsupported

    def test_hover_handler_4(self):
        through = ((1000.0, 1000.0, 1000.0), (1000.0, 1000.0, -100.0))
        beside = ((2000.0, 1000.0, 1000.0), (2000.0, 1000.0, -100.0))
        entries = [row(13, 0, 0.16, 4, extra=(0, 1)), row(13, 1, 0.3, 1, extra=(0,))]
        self.assertEqual(self.tick(entries, mouse=through)[1]['action'], 1)
        self.assertEqual(self.tick(entries, mouse=beside)[1]['action'], 0)
        leave = [row(13, 0, 0.16, 4, extra=(2, 1)), row(13, 1, 0.3, 1, extra=(0,))]
        self.assertEqual(self.tick(leave, mouse=through)[1]['action'], 0)
        status, o = self.tick(leave, mouse=beside)
        self.assertEqual((status, o['action'], o['velocity']), (1, 1, v.f32(0.3)))
        self.assertEqual(self.tick(entries, mouse=None)[0], 2)   # no mouse segment: unsupported

    def test_hover_handler_6_latch(self):
        through = ((1000.0, 1000.0, 1000.0), (1000.0, 1000.0, -100.0))
        entries = [row(13, 0, 0.16, 6, extra=(0, 1)), row(13, 1, 0.3, 1, extra=(0,))]
        _, o = self.tick(entries, mouse=through)
        self.assertEqual((o['action'], o['latch']), (1, 1))
        _, o = self.tick(entries, mouse=through, latch=1)
        self.assertEqual((o['action'], o['latch']), (0, 0))   # latched: cleared, no switch
        _, o = self.tick(entries, mouse=((0.0, 0.0, 10.0), (1.0, 0.0, 10.0)), latch=3)
        self.assertEqual((o['action'], o['latch']), (0, 0))

    def test_handler_6_locked_end(self):
        # step 2 waits for keys - 1 - speed when the action record locks positions (record 1: lock 1)
        entries = [row(13, 1, 0.16, 6, extra=(2, 0)), row(13, 0, 0.3, 0)]
        self.assertEqual(self.tick(entries, current=1, frame=10 - 1 - v.f32(0.16))[1]['action'], 0)
        self.assertEqual(self.tick(entries, current=1, frame=10 - 1 - v.f32(0.16) - 0.01)[1]['action'], 1)

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-after6-orig-') as td:
            report = Path(td) / 'report.json'
            args = [sys.executable, str(ROOT / 'scripts/validate_worlds_after6.py'), '--cases', '3000',
                    '--mutations', '--output', str(report)] + (['--lang-dir', LANG_DIR] if LANG_DIR else [])
            subprocess.run(args, check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(result['families']['hover']['cases'], 3000)
            self.assertEqual(result['families']['camera']['cases'], 3000)
            self.assertEqual(result['families']['sprite_visible']['cases'], 300)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), len(wa6.MUTATIONS))
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))


if __name__ == '__main__':
    unittest.main()
