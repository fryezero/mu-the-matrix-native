"""Synthetic checks for the login world's object handler (login_world.c, NATIVE-LOGIN-001).

Worked examples with authored object images only. The actual-instruction comparison is
scripts/validate_login_world.py (tests/test_login_world_private.py runs it with MU_RECOVERY_INTEGRATION=1).
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


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


class LoginWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(HERE)], check=True)
        import validate_object_render as v
        cls.v = v
        cls.lib = v.Library(HERE / ('libobjects.dylib' if sys.platform == 'darwin' else 'libobjects.so'))
        d = cls.lib.dll
        P = ctypes.c_void_p
        d.mu_login_pulse.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_uint32, P, P]
        d.mu_login_pulse.restype = ctypes.c_float
        d.mu_login_custom_render.argtypes = [P, ctypes.c_int32, ctypes.POINTER(v.Log)]
        d.mu_login_after_render.argtypes = [P, P, ctypes.c_int32, ctypes.c_uint32, P, P, ctypes.POINTER(v.Log)]
        d.mu_login_after_pass.argtypes = [ctypes.POINTER(v.World), ctypes.POINTER(v.RenderInputs),
                                          ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(v.Log)]
        cls.BONE = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, ctypes.POINTER(ctypes.c_float),
                                    ctypes.POINTER(ctypes.c_float))
        d.mu_login_visual.argtypes = [P, ctypes.c_int32, v.RAND_FN, cls.BONE, P, ctypes.POINTER(v.Log)]

    def obj(self, type_, **fields):
        o = bytearray(OBJ)
        struct.pack_into('<i', o, 0x5c, type_)
        o[0] = 1
        struct.pack_into('<f', o, 0xdc, 1.0)
        struct.pack_into('<i', o, 0x68, -1)
        struct.pack_into('<i', o, 0x74, -1)
        struct.pack_into('<f', o, 0xa8, 1.0)
        struct.pack_into('<f', o, 0xa0, 1.0)
        struct.pack_into('<f', o, 0xbc, 0.16)
        for offset, value in fields.items():
            struct.pack_into('<f' if isinstance(value, float) else '<i', o, int(offset[2:], 16), value)
        return ctypes.create_string_buffer(bytes(o), OBJ)

    def record(self, type_, x=21614.5, y=8734.4):
        r = self.v.Record()
        r.type = type_
        r.position[0], r.position[1], r.position[2] = x, y, 271.0
        r.scale = 1.0
        r.flag_2c = r.flag_2d = r.flag_2e = 1
        r.value_30, r.value_34 = 0.8, 0.2
        return r

    def test_create_defaults(self):
        v = self.v
        for type_, hidden, range_, speed in ((5, -1, -30.0, True), (0x26, -2, -30.0, False), (0x36, -2, -30.0, False),
                                             (1, -1, f32(-3000 / 7), False), (7, -1, f32(-3000 / 7), False)):
            o = ctypes.create_string_buffer(OBJ)
            log = v.new_log(8)
            status = self.lib.dll.mu_obj_create(ctypes.byref(self.record(type_)), 0x5e, o, None, 3, ctypes.byref(log))
            self.assertEqual(status, 0)
            self.assertEqual(struct.unpack_from('<i', o.raw, 0x68)[0], hidden, type_)
            self.assertEqual(struct.unpack_from('<f', o.raw, 0xc0)[0], range_, type_)
            events = v.log_events(log)
            self.assertEqual(events == [(0x00eaaa44, 3, 5, 0, bits(0.23))], speed, events)

    def test_pulse_and_move(self):
        d = self.lib.dll
        self.assertEqual(d.mu_login_pulse(0.2, 0.6, 0.001, 0, None, None), f32(0.6))   # sin 0: the high end
        t = 1571   # 1.571 rad: |sin| ~ 1
        self.assertAlmostEqual(d.mu_login_pulse(0.2, 0.6, 0.001, t, None, None), 0.2, places=5)
        # unsigned time above 2^31 converts as unsigned
        big = d.mu_login_pulse(0.2, 0.6, 0.001, 0x80000000, None, None)
        x = f32(f32(float(0x80000000)) * f32(0.001))
        self.assertEqual(big, f32(f32(f32(1.0 - abs(f32(math.sin(x)))) * f32(f32(0.6) - f32(0.2))) + f32(0.2)))
        v = self.v
        o = self.obj(1, f_b0=-1.33)
        inputs = v.MoveInputs(0x5e, 3, 0, 0.0, (ctypes.c_float * 3)(), 1, 1,
                              v.SPEED_FN(lambda c, t, a: 0.23 if (t, a) == (5, 0) else 0.0),
                              v.RAND_FN(lambda c: 0), None, 1000)
        log = v.new_log()
        self.lib.dll.mu_obj_move(o, 0, ctypes.byref(inputs), ctypes.byref(log))
        self.assertEqual(struct.unpack_from('<f', o.raw, 0xb0)[0], f32(f32(-1.33) - f32(0.005)))
        self.assertEqual(v.log_events(log)[0], (0x012b4dd3, 0, bits(0.16)))
        ship = self.obj(5)
        log = v.new_log()
        self.lib.dll.mu_obj_move(ship, 0, ctypes.byref(inputs), ctypes.byref(log))
        self.assertEqual(v.log_events(log)[0], (0x012b4dd3, 0, bits(0.23)))   # action 0 PlaySpeed
        beam = self.obj(0xd)
        self.lib.dll.mu_obj_move(beam, 0, ctypes.byref(inputs), ctypes.byref(v.new_log()))
        self.assertEqual(struct.unpack_from('<f', beam.raw, 0xa8)[0], d.mu_login_pulse(0.2, 0.6, 0.001, 1000, None, None))

    def test_custom_render_marks_the_after_character_pass(self):
        v = self.v
        for type_, handled, after in ((5, 1, 1), (0xd, 1, 1), (1, 1, 0), (0x38, 1, 0), (0x36, 0, 2)):
            o = self.obj(type_)
            o[0xa] = 2
            log = v.new_log()
            self.assertEqual(self.lib.dll.mu_login_custom_render(o, 0, ctypes.byref(log)), handled)
            self.assertEqual(o.raw[0xa], after)
            self.assertEqual(len(v.log_events(log)), handled)

    def test_ship_after_render_meshes(self):
        v = self.v
        o = self.obj(5, f_ac=0.5, f_b0=0.25)
        model = ctypes.create_string_buffer(0x100)
        log = v.new_log()
        self.assertEqual(self.lib.dll.mu_login_after_render(o, model, 0, 0, None, None, ctypes.byref(log)), 1)
        events = v.log_events(log)
        meshes = [e for e in events if e[0] == 0x00966e4a]
        self.assertEqual([e[2] for e in meshes], [0x12, 2, 2, 2, 0, 0, 0x18, 0x18, 0x19, 0x19, 0x1a, 0x1a, 0x1b, 0x1b,
                                                0x1c, 0x1c])
        self.assertEqual(meshes[0][9], 0x817c)
        self.assertEqual(meshes[8][7:9], (bits(0.25), bits(0.125)))   # mesh 0x19, first pass: half offsets
        self.assertEqual(meshes[4][4], bits(0.7))                       # lantern meshes at alpha 0.7
        self.assertEqual(struct.unpack_from('<3f', model.raw, 0x54), (1.0, 1.0, 1.0))
        self.assertEqual(struct.unpack_from('<f', o.raw, 0xdc)[0], 1.0)

    def test_lanterns_follow_the_bones(self):
        v = self.v
        o = self.obj(5)
        seen = []

        def bone(c, b, local, out):
            seen.append((b, local[2]))
            out[0], out[1], out[2] = 100.0 * b, 0.0, local[2]
        keep = (v.RAND_FN(lambda c: 0), self.BONE(bone))
        log = v.new_log()
        self.lib.dll.mu_login_visual(o, 0, keep[0], keep[1], None, ctypes.byref(log))
        sprites = [e for e in v.log_events(log) if e[0] == 0x01692eb7]
        self.assertEqual(len(sprites), 10)
        self.assertEqual([b for b, _ in seen], [37, 37, 37, 98, 98, 98])
        self.assertEqual(seen[3][1], f32(2.8))                       # rand 0: z = 0 / 20 + 2.8
        self.assertEqual(sprites[0][3], bits(3700.0))
        self.assertEqual(sprites[0][2], 0x7f67)

    def test_after_pass_draws_flagged_objects(self):
        v = self.v
        objects = []
        for k, (flag, live) in enumerate(((1, 1), (0, 1), (1, 0), (1, 1))):
            o = bytearray(OBJ)
            o[0], o[0xa] = live, flag
            struct.pack_into('<3f', o, 0x158, 12800.0 + k, 12800.0, 0.0)
            struct.pack_into('<f', o, 0xc0, -30.0)
            objects.append(o)
        heads = [-1] * 256
        heads[8 * 16 + 8] = 0
        nxt = [1, 2, 3, -1]
        w, bufs = v.c_world(objects, heads, nxt)
        xs = (ctypes.c_float * 4)(100.0, 160.0, 160.0, 100.0)
        ys = (ctypes.c_float * 4)(100.0, 100.0, 160.0, 160.0)
        inputs = v.RenderInputs(0x5e, 3, 0, xs, ys, v.ANSWER_FN(lambda c, k: 0), v.ANSWER_FN(lambda c, k: 0), None, 0.0)
        counter = ctypes.c_int32(41)
        log = v.new_log()
        self.assertEqual(self.lib.dll.mu_login_after_pass(ctypes.byref(w), ctypes.byref(inputs), ctypes.byref(counter),
                                                          ctypes.byref(log)), 0)
        self.assertEqual([e[1] for e in v.log_events(log)], [0, 3])
        self.assertEqual(counter.value, 1)
        inputs.world = 0
        self.assertEqual(self.lib.dll.mu_login_after_pass(ctypes.byref(w), ctypes.byref(inputs), ctypes.byref(counter),
                                                          ctypes.byref(log)), 2)


if __name__ == '__main__':
    unittest.main()
