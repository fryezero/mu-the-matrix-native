"""RENDER-WORLDS-PICK-001: the map object's box OBJECT +0x31c (object_pick.c) and the mouse-over tick handlers 4
and 6 that read it (action_registry.c): portable synthetic checks, and the private instruction comparison
(validate_worlds_pick)."""
import ctypes as C
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
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_object_render as v  # noqa: E402
import validate_worlds_after5 as wa5  # noqa: E402
import validate_worlds_after6 as wa6  # noqa: E402
import validate_worlds_pick as wp  # noqa: E402
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
CASES = 1000


def obj(position=(1000.0, 2000.0, 50.0), low=(-40.0, -40.0, 0.0), high=(40.0, 40.0, 80.0), angle=(0.0, 0.0, 0.0),
        scale=1.0):
    raw = bytearray(v.OBJ_SIZE)
    struct.pack_into('<3f', raw, 0x158, *position)
    struct.pack_into('<3f', raw, 0x164, *angle)
    struct.pack_into('<f', raw, 0xa0, scale)
    struct.pack_into('<3f', raw, wp.BOX_MIN, *low)
    struct.pack_into('<3f', raw, wp.BOX_MAX, *high)
    return raw


class WorldsPickTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = wp.build(ROOT / 'reconstructed')

    def write(self, raw, origin, mode=0, vertices=None):
        buffer = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        low, high = (C.c_float * 3)(), (C.c_float * 3)()
        if vertices is not None:
            self.lib.dll.mu_obj_vertex_bounds_begin(low, high)
            for p in vertices:
                self.lib.dll.mu_obj_vertex_bounds_add(low, high, wp.vec(p))
        self.lib.dll.mu_obj_obb_write(buffer, wp.vec(origin), mode, low if vertices is not None else None,
                                      high if vertices is not None else None)
        return buffer, struct.unpack_from('<12f', buffer.raw, wp.OBB)

    def test_box_is_the_object_box_at_the_origin(self):
        # CreateObject's default box (-40, -40, 0)..(40, 40, 80) at the position
        raw = obj()
        buffer, box = self.write(raw, (1000.0, 2000.0, 50.0))
        self.assertEqual(box, (960.0, 1960.0, 50.0, 80.0, 0.0, 0.0, 0.0, 80.0, 0.0, 0.0, 0.0, 80.0))
        self.assertEqual(buffer.raw[:wp.OBB], bytes(raw[:wp.OBB]))            # nothing else is written
        self.assertEqual(buffer.raw[wp.OBB + 48:v.OBJ_SIZE], bytes(raw[wp.OBB + 48:]))

    def test_turn_and_scale_do_not_enter_the_box(self):
        plain = self.write(obj(), (1000.0, 2000.0, 50.0))[1]
        turned = self.write(obj(angle=(10.0, 20.0, 135.0), scale=14.84), (1000.0, 2000.0, 50.0))[1]
        self.assertEqual(plain, turned)
        for mode in (1, 3, -1):   # only 2 selects the vertex bounds
            self.assertEqual(self.write(obj(), (1000.0, 2000.0, 50.0), mode)[1], plain)

    def test_type_boxes_and_stale_axes(self):
        # Lorencia's types 0 / 1 (-150..150, 0..500); stale off-diagonal terms are cleared
        raw = obj(low=(-150.0, -150.0, 0.0), high=(150.0, 150.0, 500.0))
        struct.pack_into('<12f', raw, wp.OBB, *([7.0] * 12))
        box = self.write(raw, (0.0, 0.0, 0.0))[1]
        self.assertEqual(box, (-150.0, -150.0, 0.0, 300.0, 0.0, 0.0, 0.0, 300.0, 0.0, 0.0, 0.0, 500.0))

    def test_mode_2_bounds_the_vertices(self):
        vertices = [(10.0, -5.0, 3.0), (-20.0, 40.0, 0.0), (5.0, 5.0, 90.0)]
        box = self.write(obj(), (100.0, 200.0, 300.0), 2, vertices)[1]
        self.assertEqual(box, (80.0, 195.0, 300.0, 30.0, 0.0, 0.0, 0.0, 45.0, 0.0, 0.0, 0.0, 90.0))
        # no vertex: the start values 999999 / -999999
        empty = self.write(obj(), (0.0, 0.0, 0.0), 2, [])[1]
        self.assertEqual((empty[0], empty[3]), (999999.0, v.f32(-999999.0 - 999999.0)))
        # a NaN component changes neither bound
        nan = self.write(obj(), (0.0, 0.0, 0.0), 2, [(1.0, 2.0, 3.0), (math.nan, 5.0, 6.0)])[1]
        self.assertEqual((nan[0], nan[3], nan[1], nan[7]), (1.0, 0.0, 2.0, 3.0))

    def over(self, buffer, p1, p2):
        return self.lib.dll.mu_obj_segment_obb(buffer, wp.vec(p1), wp.vec(p2))

    def test_segment_hit_miss_boundary(self):
        buffer, _ = self.write(obj(), (1000.0, 2000.0, 50.0))   # 960..1040 x 1960..2040 x 50..130
        self.assertEqual(self.over(buffer, (1000.0, 2000.0, 900.0), (1000.0, 2000.0, -100.0)), 1)   # through
        self.assertEqual(self.over(buffer, (1041.0, 2000.0, 900.0), (1041.0, 2000.0, -100.0)), 0)   # beside
        self.assertEqual(self.over(buffer, (1040.0, 2000.0, 900.0), (1040.0, 2000.0, -100.0)), 1)   # on a face plane
        self.assertEqual(self.over(buffer, (1000.0, 2000.0, 900.0), (1000.0, 2000.0, 130.0)), 1)    # ends on the top
        self.assertEqual(self.over(buffer, (1000.0, 2000.0, 900.0), (1000.0, 2000.0, 131.0)), 0)    # one unit short
        self.assertEqual(self.over(buffer, (1040.0, 2040.0, 900.0), (1040.0, 2040.0, -100.0)), 1)   # along an edge
        self.assertEqual(self.over(buffer, (960.0, 1960.0, 50.0), (960.0, 1960.0, 50.0)), 1)        # the corner point
        self.assertEqual(self.over(buffer, (959.0, 1960.0, 50.0), (959.0, 1960.0, 50.0)), 0)
        self.assertEqual(self.over(buffer, (1000.0, 2000.0, math.nan), (1000.0, 2000.0, -100.0)), 0)

    def tick(self, buffer, entries, mouse, latch=0):
        raw = bytearray(buffer.raw[:v.OBJ_SIZE])
        struct.pack_into('<i', raw, 0x5c, 13)
        struct.pack_into('<f', raw, 0xbc, 0.16)
        struct.pack_into('<ii', raw, 0x30, 0, latch)
        keep, table = [], (wa5.AnimEntry * len(entries))()
        for i, e in enumerate(entries):
            extra = (C.c_int32 * max(1, len(e['extra'])))(*e['extra'])
            keep.append(extra)
            table[i] = wa5.AnimEntry(e['type'], e['action'], e['speed'], e['handler'], e['param'], len(e['extra']),
                                     C.cast(extra, C.POINTER(C.c_int32)))

        def model(ctx, k, action, count, keys, lock):
            count[0] = 2
            if 0 <= action < 2:
                keys[0], lock[0] = 20, 0
            return 1
        model_fn, rand_fn = wa5.MODEL_FN(model), v.RAND_FN(lambda c: 0)
        start, end = (wp.vec(mouse[0]), wp.vec(mouse[1])) if mouse else (None, None)
        inputs = wa6.AnimInputs(C.cast(table, C.POINTER(wa5.AnimEntry)), len(entries), model_fn, rand_fn, None,
                                (C.c_float * 3)(0.0, 0.0, 0.0), None, start, end)
        out = C.create_string_buffer(bytes(raw), v.OBJ_SIZE)
        found = C.c_int(0)
        status = self.lib.dll.mu_action_tick(out, C.byref(inputs), C.byref(found))
        return status, struct.unpack_from('<H', out.raw, 0x2a)[0], struct.unpack_from('<i', out.raw, 0x34)[0]

    def test_written_box_feeds_the_mouse_handlers(self):
        def row(action, handler, extra):
            return {'type': 13, 'action': action, 'speed': v.f32(0.16 if action == 0 else 0.3), 'handler': handler,
                    'param': 300, 'extra': list(extra)}
        through = ((1000.0, 2000.0, 900.0), (1000.0, 2000.0, -100.0))
        beside = ((1041.0, 2000.0, 900.0), (1041.0, 2000.0, -100.0))
        grazing = ((1040.0, 2000.0, 900.0), (1040.0, 2000.0, -100.0))
        unwritten = C.create_string_buffer(bytes(obj()), v.OBJ_SIZE)   # the initialiser's zero box
        written, _ = self.write(obj(), (1000.0, 2000.0, 50.0))
        over = [row(0, 4, (0, 1)), row(1, 1, (0,))]
        # no box yet: all six axis projections of a zero box are 0, so every segment is over it (as in the client:
        # validate_worlds_pick's `unwritten` class)
        self.assertEqual(self.tick(unwritten, over, through)[1], 1)
        self.assertEqual(self.tick(unwritten, over, beside)[1], 1)
        self.assertEqual(self.tick(written, over, through)[1], 1)     # handler 4, step 0: over -> back()
        self.assertEqual(self.tick(written, over, beside)[1], 0)
        self.assertEqual(self.tick(written, over, grazing)[1], 1)     # the boundary counts as over
        leave = [row(0, 4, (2, 1)), row(1, 1, (0,))]
        self.assertEqual(self.tick(written, leave, through)[1], 0)    # step 2: leaves when not over
        self.assertEqual(self.tick(written, leave, beside)[1], 1)
        latch = [row(0, 6, (0, 1)), row(1, 1, (0,))]
        self.assertEqual(self.tick(written, latch, through)[1:], (1, 1))            # handler 6: latch += 1, back()
        self.assertEqual(self.tick(written, latch, through, latch=1)[1:], (0, 0))   # latched: cleared
        self.assertEqual(self.tick(written, over, None)[0], 2)                      # no mouse segment: unsupported

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-pick-orig-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_pick.py'), '--cases', str(CASES),
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(sorted(result['families']), ['box', 'pick', 'segment'])
            self.assertTrue(all(r['cases'] == CASES and r['cases'] == r['equal'] and r['stopped'] == 0
                                for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), len(wp.MUTATIONS))
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))
            self.assertTrue(result['bounds_mode_references']['all_compares'])


if __name__ == '__main__':
    unittest.main()
