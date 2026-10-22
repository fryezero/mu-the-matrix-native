"""Synthetic checks for the authored world-object routines (object_render.c, NATIVE-OBJECTS-002).

Worked examples with authored inputs only: light grids, records and object images built here. The
actual-instruction comparison is scripts/validate_object_render.py (tests/test_object_render_private.py
runs it with MU_RECOVERY_INTEGRATION=1).
"""
import ctypes
import math
from pathlib import Path
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
OBJ = 0x3d8
sys.path.insert(0, str(HERE.parents[1] / 'scripts'))


def library():
    subprocess.run(['make', '-s', '-C', str(HERE)], check=True)
    suffix = 'dylib' if sys.platform == 'darwin' else 'so'
    import validate_object_render as v   # ctypes declarations shared with the validator (no Unicorn needed)
    return v, v.Library(HERE / f'libobjects.{suffix}')


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


class ObjectRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v, cls.lib = library()

    def grid(self, fn):
        g = (ctypes.c_float * (256 * 256 * 3))()
        for y in range(256):
            for x in range(256):
                for c in range(3):
                    g[3 * (256 * y + x) + c] = fn(x, y, c)
        return g

    def light(self, grid, x, y, scene=6, ready=1):
        out = (ctypes.c_float * 3)()
        self.lib.dll.mu_obj_terrain_light(ctypes.cast(grid, ctypes.c_void_p), scene, ready, x, y, out)
        return list(out)

    def test_terrain_light_is_bilinear_and_bounded(self):
        g = self.grid(lambda x, y, c: x * 0.01 + y * 0.001 + c)
        out = self.light(g, 1050.0, 2025.0)            # tile (10, 20), fx 0.5, fy 0.25
        for c in range(3):
            self.assertAlmostEqual(out[c], 10.5 * 0.01 + 20.25 * 0.001 + c, places=5)
        self.assertEqual(self.light(g, 25500.0, 100.0), [0.0, 0.0, 0.0])   # xi 255 > 254
        self.assertEqual(self.light(g, -150.0, 100.0), [0.0, 0.0, 0.0])   # (int)-0.01 is 0: still inside
        self.assertEqual(self.light(g, 1050.0, 2025.0, scene=4), [0.0, 0.0, 0.0])
        self.assertEqual(self.light(g, 1050.0, 2025.0, ready=0), [0.0, 0.0, 0.0])
        self.assertEqual(self.light(g, math.nan, 5.0), [0.0, 0.0, 0.0])

    def obj(self, type_, x=1050.0, y=2025.0, flags=(1, 1, 1), light=(0.0, 0.0, 0.0)):
        o = bytearray(OBJ)
        struct.pack_into('<i', o, 0x5c, type_)
        o[5:8] = bytes(flags)
        struct.pack_into('<3f', o, 0x158, x, y, 0.0)
        struct.pack_into('<3f', o, 0xec, *light)
        return o

    def body_light(self, o, frame_value=0.5, primary_value=0.25):
        frame = self.grid(lambda x, y, c: frame_value)
        primary = self.grid(lambda x, y, c: primary_value)
        inputs = self.v.LightInputs(ctypes.cast(primary, ctypes.c_void_p), ctypes.cast(frame, ctypes.c_void_p), 6, 1,
                                    0.0, self.v.SIN_FN(lambda c, x: math.sin(x)), None)
        co = ctypes.create_string_buffer(bytes(o), OBJ)
        model = ctypes.create_string_buffer(0xd0)
        self.lib.dll.mu_obj_body_light(co, model, ctypes.byref(inputs))
        return co.raw, model.raw

    def test_body_light_flags(self):
        o, m = self.body_light(self.obj(5, light=(0.1, 0.0, -0.1)))
        self.assertEqual(m[0x50], 1)
        self.assertEqual([round(v, 5) for v in struct.unpack_from('<3f', m, 0x54)], [0.6, 0.5, 0.4])
        self.assertEqual(o[0x1e8:0x1f4], m[0x54:0x60])                    # copied when +5 or +6
        o, m = self.body_light(self.obj(5, flags=(1, 1, 0)))             # +7 clear: primary light
        self.assertAlmostEqual(struct.unpack_from('<f', m, 0x54)[0], 0.25)
        o, m = self.body_light(self.obj(5, flags=(1, 0, 1)))             # +6 clear: scaled by 0.1
        self.assertAlmostEqual(struct.unpack_from('<f', m, 0x54)[0], f32(0.1) * 0.5, places=6)
        o, m = self.body_light(self.obj(5, flags=(0, 0, 1)))
        self.assertEqual(m[0x50], 0)
        self.assertEqual(o[0x1e8:0x1f4], bytes(12))                       # no copy
        o, m = self.body_light(self.obj(0x7dc))
        self.assertAlmostEqual(struct.unpack_from('<f', m, 0x54)[0], 0.6, places=6)

    def create(self, world, type_, scale=1.0, hidden=0, x=14550.0, y=13450.0):
        r = self.v.Record()
        r.type, r.scale, r.hidden = type_, scale, hidden
        r.position[0], r.position[1] = x, y
        r.flag_2c = r.flag_2d = r.flag_2e = 1
        r.value_30, r.value_34 = 0.8, 0.2
        o = ctypes.create_string_buffer(OBJ)
        sector = ctypes.c_int32(-1)
        status = self.lib.dll.mu_obj_create(ctypes.byref(r), world, o, ctypes.byref(sector), 0, None)
        return status, sector.value, o.raw

    def field(self, o, offset, fmt='<f'):
        return struct.unpack_from(fmt, o, offset)[0]

    def test_create_generic_and_lorencia(self):
        status, sector, o = self.create(0, 9)
        self.assertEqual((status, sector), (0, (9 << 4) + 8))
        self.assertAlmostEqual(self.field(o, 0xbc), 0.16, places=6)
        self.assertEqual(self.field(o, 0xc0), -30.0)
        self.assertEqual(self.field(o, 0x74, '<i'), -1)
        self.assertEqual(self.field(o, 0x68, '<i'), -1)
        self.assertAlmostEqual(self.field(self.create(0, 1, scale=1.6)[2], 0xbc), f32(1 / f32(1.6)) * f32(0.4), places=6)
        self.assertEqual(self.field(self.create(0, 0x85)[2], 0x68, '<i'), -2)      # PoseBox01
        self.assertEqual(self.field(self.create(0, 0x5a)[2], 0x74, '<i'), 1)       # StreetLight01
        self.assertEqual(self.field(self.create(0, 0x50)[2], 0xc0), -50.0)         # Bridge01
        self.assertEqual(self.field(self.create(0, 9, hidden=1)[2], 0x68, '<i'), -2)
        self.assertEqual(self.create(0, 9, x=-1700.0)[0], 1)                       # outside the map (sector -1)
        self.assertEqual(self.create(4, 9)[0], 2)                                  # world case not reconstructed
        self.assertEqual(self.field(self.create(3, 9)[2], 0x74, '<i'), 3)          # Noria (NATIVE-FIDELITY-002)

    def test_create_tormenta_handler(self):
        self.assertEqual(self.field(self.create(0x8d, 0x27)[2], 0xc0), -300.0)
        self.assertEqual(self.field(self.create(0x8d, 0xc0)[2], 0x68, '<i'), -2)
        o = self.create(0x8d, 0x26)[2]
        self.assertEqual(o[7], 0)
        o = self.create(0x8d, 0x1f)[2]
        self.assertEqual((o[0x0a], self.field(o, 0xc0)), (1, -1000.0))

    def move(self, o, world=0, hero_tile=0, seed=1, time=12345.0):
        rnd = self.v.MsvcRand(seed)
        inputs = self.v.MoveInputs(world, 6, hero_tile, time, (ctypes.c_float * 3)(0, 0, 0), 1, 1,
                                   self.v.SPEED_FN(lambda c, t, a: 0.5), self.v.RAND_FN(lambda c: rnd()), None)
        co = ctypes.create_string_buffer(bytes(o), OBJ)
        log = self.v.new_log()
        status = self.lib.dll.mu_obj_move(co, 3, ctypes.byref(inputs), ctypes.byref(log))
        return status, co.raw, self.v.log_events(log)

    def lorencia(self, type_):
        o = bytearray(self.create(0, type_)[2])
        struct.pack_into('<f', o, 0xe0, 0.1)
        return o

    def test_move_street_light_and_tick(self):
        status, o, events = self.move(self.lorencia(0x5a))
        self.assertEqual(status, 0)
        self.assertEqual(events[0][0], 0x012b4dd3)
        self.assertAlmostEqual(struct.unpack('<f', struct.pack('<I', events[0][2]))[0], 0.3, places=6)
        light = events[1]
        self.assertEqual((light[0], light[1], light[-1]), (0x016cacfc, 3, 3))
        r = (1 * 214013 + 2531011) & 0xffffffff                                  # first MSVC rand
        level = f32(f32((((r >> 16) & 0x7fff) % 2) + 6) * f32(0.1))
        self.assertAlmostEqual(struct.unpack('<f', struct.pack('<I', light[4]))[0], level, places=6)

    def test_move_fire_creates_particles_and_light(self):
        seen = set()
        for seed in range(1, 40):
            status, o, events = self.move(self.lorencia(0x34), seed=seed)
            seen.update(e[0] for e in events)
            light = [e for e in events if e[0] == 0x016cacfc]
            self.assertEqual(len(light), 1)
            self.assertEqual(light[0][-1], 4)
            bl = struct.unpack_from('<f', o, 0xa8)[0]
            self.assertTrue(0.39 < bl < 1.0)
        self.assertIn(0x0168fafd, seen)

    def test_roof_fades_in_the_pub(self):
        o = self.lorencia(0x7d)
        status, out, _ = self.move(o, hero_tile=4)
        self.assertEqual(struct.unpack_from('<f', out, 0xd8)[0], 0.0)
        self.assertAlmostEqual(struct.unpack_from('<f', out, 0xdc)[0], 0.9, places=6)
        status, out, _ = self.move(o, hero_tile=0)
        self.assertEqual(struct.unpack_from('<f', out, 0xd8)[0], 1.0)

    def test_light_markers_hide(self):
        status, out, events = self.move(self.lorencia(0x83))
        self.assertEqual(struct.unpack_from('<i', out, 0x68)[0], -2)

    def world(self, positions, visible=None):
        objects = []
        for x, y in positions:
            o = bytearray(self.create(0, 9, x=x, y=y)[2])
            o[0x0b] = 1
            objects.append(o)
        heads, nxt, tails = [-1] * 256, [-1] * len(objects), [-1] * 256
        for k, o in enumerate(objects):
            s = o[0x46]
            if heads[s] < 0:
                heads[s] = k
            else:
                nxt[tails[s]] = k
            tails[s] = k
        return self.v.c_world(objects, heads, nxt, visible)

    def test_render_pass_culls_by_frustum(self):
        w, bufs = self.world([(14550.0, 13450.0), (2000.0, 2000.0), (14600.0, 13500.0)])
        x2d = (ctypes.c_float * 4)(135.0, 155.0, 155.0, 135.0)
        y2d = (ctypes.c_float * 4)(145.0, 145.0, 125.0, 125.0)
        inputs = self.v.RenderInputs(0, 6, 0, x2d, y2d, self.v.ANSWER_FN(lambda c, k: 0),
                                     self.v.ANSWER_FN(lambda c, k: 0), None, 0.1)
        counter = ctypes.c_int32(41)
        log = self.v.new_log()
        self.lib.dll.mu_obj_render_pass(ctypes.byref(w), ctypes.byref(inputs), ctypes.byref(counter), ctypes.byref(log))
        drawn = [e[1] for e in self.v.log_events(log) if e[0] == 0x016d4fe4]
        self.assertEqual(drawn, [0, 2])
        self.assertEqual(counter.value, 1)
        self.assertEqual(bufs[1].raw[0x0b], 1)        # its sector is not visible: the byte is left as it was

    def test_move_pass_clears_invisible_sectors(self):
        visible = [0] * 256
        w, bufs = self.world([(14550.0, 13450.0), (2000.0, 2000.0)], visible)
        w.block_visible[(9 << 4) + 8] = 1
        log = self.v.new_log()
        self.lib.dll.mu_obj_move_pass(ctypes.byref(w), 0, self.v.ANSWER_FN(lambda c, k: 0), None, ctypes.byref(log))
        moved = [e[1] for e in self.v.log_events(log) if e[0] == 0x017ff238]
        self.assertEqual(moved, [0])
        self.assertEqual(bufs[1].raw[0x0b], 0)

    def test_render_object_hidden_and_body(self):
        o = bytearray(self.create(0, 0x5a)[2])
        frame = self.grid(lambda x, y, c: 0.5)
        light = self.v.LightInputs(ctypes.cast(frame, ctypes.c_void_p), ctypes.cast(frame, ctypes.c_void_p), 6, 1, 0.0,
                                   self.v.SIN_FN(lambda c, x: 0.0), None)
        inputs = self.v.DrawInputs(0, 6, 1, 0, 0, 0, light, self.v.ANSWER_FN(lambda c, k: 0),
                                   self.v.ANSWER_FN(lambda c, k: 0), None)
        co, model, log = ctypes.create_string_buffer(bytes(o), OBJ), ctypes.create_string_buffer(0x100), self.v.new_log()
        self.assertEqual(self.lib.dll.mu_obj_render(co, 0, model, 0, ctypes.byref(inputs), ctypes.byref(log)), 0)
        body = [e for e in self.v.log_events(log) if e[0] == 0x00966def][0]
        self.assertEqual((body[2], body[4], body[8]), (2, 1, 0xffffffff))      # flags 2, blend mesh 1, hidden -1
        struct.pack_into('<i', o, 0x68, -2)
        co, log = ctypes.create_string_buffer(bytes(o), OBJ), self.v.new_log()
        self.assertEqual(self.lib.dll.mu_obj_render(co, 0, model, 0, ctypes.byref(inputs), ctypes.byref(log)), 1)
        self.assertFalse([e for e in self.v.log_events(log) if e[0] == 0x00966def])


if __name__ == '__main__':
    unittest.main()
