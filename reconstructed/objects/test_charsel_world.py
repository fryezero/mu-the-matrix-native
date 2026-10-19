"""Synthetic checks for the character-select world's object handler (charsel_world.c, NATIVE-CHARSEL-002).

Worked examples with authored object images only. The actual-instruction comparison is
scripts/validate_charsel_world.py (tests/test_charsel_world_private.py runs it with MU_RECOVERY_INTEGRATION=1).
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


class Scene(ctypes.Structure):
    _fields_ = [('position', (ctypes.c_float * 3) * 5), ('angle', (ctypes.c_float * 3) * 5)]


class CharselWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(HERE)], check=True)
        import validate_object_render as v
        cls.v = v
        cls.lib = v.Library(HERE / ('libobjects.dylib' if sys.platform == 'darwin' else 'libobjects.so'))
        d = cls.lib.dll
        P = ctypes.c_void_p
        cls.BONE = ctypes.CFUNCTYPE(None, P, ctypes.c_int32, ctypes.POINTER(ctypes.c_float),
                                    ctypes.POINTER(ctypes.c_float))
        cls.SIN = ctypes.CFUNCTYPE(ctypes.c_double, P, ctypes.c_double)
        d.mu_csw_create.argtypes = [P, ctypes.c_int32, ctypes.POINTER(Scene), ctypes.POINTER(v.Log)]
        d.mu_csw_create.restype = None
        d.mu_csw_move.argtypes = [P, ctypes.c_int32, v.RAND_FN, P, ctypes.POINTER(v.Log)]
        d.mu_csw_visual.argtypes = [P, ctypes.c_int32, ctypes.c_float, v.RAND_FN, cls.BONE, cls.SIN, P,
                                    ctypes.POINTER(v.Log)]
        d.mu_csw_custom_render.argtypes = [P, ctypes.c_int32, ctypes.POINTER(v.Log)]
        d.mu_csw_after_render.argtypes = [P, ctypes.c_int32, ctypes.POINTER(v.Log)]
        d.mu_login_after_pass.argtypes = [ctypes.POINTER(v.World), ctypes.POINTER(v.RenderInputs),
                                          ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(v.Log)]

    def obj(self, type_, **fields):
        o = bytearray(OBJ)
        struct.pack_into('<i', o, 0x5c, type_)
        o[0] = 1
        struct.pack_into('<f', o, 0xdc, 1.0)
        struct.pack_into('<i', o, 0x64, 7)
        struct.pack_into('<i', o, 0x68, -1)
        struct.pack_into('<i', o, 0x74, -1)
        struct.pack_into('<f', o, 0xa8, 1.0)
        struct.pack_into('<f', o, 0xa0, 1.0)
        struct.pack_into('<3f', o, 0x158, 13629.3, 12338.5, 164.5)
        for offset, value in fields.items():
            struct.pack_into('<f' if isinstance(value, float) else '<i', o, int(offset[2:], 16), value)
        return ctypes.create_string_buffer(bytes(o), OBJ)

    def record(self, type_, x=13629.3, y=12338.5):
        r = self.v.Record()
        r.type = type_
        r.position[0], r.position[1], r.position[2] = x, y, 164.5
        r.scale = 1.0
        r.flag_2c = r.flag_2d = r.flag_2e = 1
        r.value_30, r.value_34 = 0.8, 0.2
        return r

    def test_create_markers_and_hidden_emitters(self):
        v = self.v
        for type_, hidden, range_ in ((0x0e, -2, -30.0), (0x26, -2, -30.0), (0x37, -2, -30.0), (0x50, -2, -30.0),
                                      (0x3c, -1, f32(-3000 / 7)), (0x3d, -1, f32(-3000 / 7)), (0x1f, -1, -30.0)):
            o = ctypes.create_string_buffer(OBJ)
            log = v.new_log(8)
            status = self.lib.dll.mu_obj_create(ctypes.byref(self.record(type_)), 0x5d, o, None, 3, ctypes.byref(log))
            self.assertEqual(status, 0)
            self.assertEqual(struct.unpack_from('<i', o.raw, 0x68)[0], hidden, hex(type_))
            self.assertEqual(struct.unpack_from('<f', o.raw, 0xc0)[0], range_, hex(type_))
            self.assertEqual(struct.unpack_from('<i', o.raw, 0x64)[0], 0)
            events = v.log_events(log)
            self.assertEqual(events == [(0x00da9ff3, 3, 1)], type_ == 0x0e, events)
        # the marker vectors: position of the object, yaw from the table
        scene = Scene()
        for k in range(5):
            o = self.obj(0x0d + k)
            self.lib.dll.mu_csw_create(o, k, ctypes.byref(scene), None)
        self.assertEqual([scene.angle[k][2] for k in range(5)], [115.0, 90.0, 75.0, 60.0, 35.0])
        self.assertEqual(list(scene.position[1]), [f32(13629.3), f32(12338.5), 164.5])

    def test_move_scroll_and_lamp_light(self):
        v = self.v
        for type_, step in ((0x18, 0.02), (0x19, 0.03), (0x1a, 0.03)):
            o = self.obj(type_, f_b0=1.0)
            self.assertEqual(self.lib.dll.mu_csw_move(o, 0, v.RAND_FN(lambda c: 0), None, None), 1)
            self.assertEqual(struct.unpack_from('<f', o.raw, 0xb0)[0], f32(1.0 - f32(step)))
        log = v.new_log(4)
        o = self.obj(0x49)
        self.assertEqual(self.lib.dll.mu_csw_move(o, 2, v.RAND_FN(lambda c: 9), None, ctypes.byref(log)), 1)
        l = f32(f32(9 % 4 + 3) * f32(0.1))
        self.assertEqual(v.log_events(log), [(0x016cacfc, 2, bits(13629.3), bits(12338.5), bits(f32(l * f32(0.2))),
                                              bits(f32(l * f32(0.6))), bits(l), 3)])
        self.assertEqual(self.lib.dll.mu_csw_move(self.obj(0x22), 0, v.RAND_FN(lambda c: 0), None, None), 0)

    def visual(self, type_, rands, world_time=0.0, sine=None, **fields):
        v = self.v
        values = list(rands)
        rnd = v.RAND_FN(lambda c: values.pop(0) if values else 1)

        def bone(c, b, local, out):
            out[0], out[1], out[2] = 100.0 * b, 10.0, 50.0
        keep = (rnd, self.BONE(bone), self.SIN(sine or (lambda c, x: math.sin(x))))
        log = v.new_log(32)
        handled = self.lib.dll.mu_csw_visual(self.obj(type_, **fields), 0, world_time, keep[0], keep[1], keep[2], None,
                                             ctypes.byref(log))
        return handled, v.log_events(log)

    def test_visual_sprites_particles_effects(self):
        handled, events = self.visual(0x1f, [])
        sprites = [e for e in events if e[0] == 0x01692eb7]
        self.assertEqual((handled, len(sprites)), (1, 3))
        self.assertEqual([e[2] for e in sprites], [0x8155] * 3)
        self.assertEqual([e[6] for e in sprites], [bits(1.0), bits(1.2), bits(0.8)])
        self.assertEqual([e[3] for e in sprites], [bits(600.0), bits(700.0), bits(800.0)])   # bones 6, 7, 8
        # the falls: WATERFALL3 every frame at twice the scale, WATERFALL2 on rand() % 3 == 0
        handled, events = self.visual(0x37, [], f_a0=1.5)
        self.assertEqual(events[0][2:3] + events[0][12:], (0x801c, 0xe, bits(3.0), 0))
        self.assertEqual(self.visual(0x38, [3])[1][0][12], 2)
        self.assertEqual(self.visual(0x38, [4])[1], [])
        # the sky: stardr01 0x5ac subtype 1 on rand() % 200 == 0
        handled, events = self.visual(0x28, [400])
        self.assertEqual((events[0][0], events[0][2], events[0][12], events[0][13]), (0x013c0eaa, 0x5ac, 1, 1))
        self.assertEqual(self.visual(0x28, [100])[1], [])

    def test_visual_lamp(self):
        t = f32(12345.0)
        handled, events = self.visual(0x49, [15, 0], world_time=t, sine=lambda c, x: 0.5, f_a0=2.0)
        shiny, ground = events[1], events[2]
        rotation = f32(f32(12345 % 3600) * f32(0.1))
        self.assertEqual((shiny[2], shiny[6]), (0x7f67, bits(f32(1.2 + f32(15 / 90.0)))))
        self.assertEqual(shiny[8], bits(f32(f32(f32(f32(0.5) * f32(0.2)) + f32(0.3)) + f32(0.5))))
        self.assertEqual(shiny[10], bits(-rotation))
        self.assertEqual((ground[2], ground[6], ground[10]), (0x8145, bits(0.2), bits(rotation)))
        particle = events[3]
        self.assertEqual((particle[2], particle[5], particle[12], particle[13]), (0x8017, bits(65.0), 0, bits(3.6)))

    def test_custom_and_after_render(self):
        v = self.v
        for type_, handled in ((0x18, 1), (0x47, 1), (0x3c, 1), (0x36, 0), (0x49, 0)):
            o = self.obj(type_)
            log = v.new_log(4)
            self.assertEqual(self.lib.dll.mu_csw_custom_render(o, 0, ctypes.byref(log)), handled, hex(type_))
            self.assertEqual(o.raw[0xa], handled)
            events = v.log_events(log)
            self.assertEqual(events == [(0x00966e4a, 0, 1, 2, bits(1.0), 0xffffffff, bits(1.0), 0, 0, 0xffffffff)],
                             type_ == 0x3c, events)
        log = v.new_log(4)
        self.lib.dll.mu_csw_after_render(self.obj(0x3c), 0, ctypes.byref(log))
        self.assertEqual(v.log_events(log), [(0x00966e4a, 0, 0, 2, bits(1.0), 0xfffffffe, bits(1.0), 0, 0, 0xffffffff)])
        log = v.new_log(4)
        self.lib.dll.mu_csw_after_render(self.obj(0x1f, i_68=-2), 0, ctypes.byref(log))
        self.assertEqual(v.log_events(log), [(0x00966def, 0, 2, bits(1.0), 0xffffffff, bits(1.0), 0, 0, 0xfffffffe,
                                              0xffffffff)])

    def test_after_pass_serves_world_0x5d(self):
        v = self.v
        world = v.World()
        for s in range(256):
            world.head[s] = -1
        inputs = v.RenderInputs(0x5d, 5, 0, None, None, v.ANSWER_FN(lambda c, k: 0), v.ANSWER_FN(lambda c, k: 0), None,
                                0.0)
        xs = (ctypes.c_float * 4)(0.0, 256.0, 256.0, 0.0)
        ys = (ctypes.c_float * 4)(0.0, 0.0, 256.0, 256.0)
        inputs.x2d, inputs.y2d = ctypes.cast(xs, ctypes.POINTER(ctypes.c_float)), ctypes.cast(ys, ctypes.POINTER(ctypes.c_float))
        counter = ctypes.c_int32(0)
        log = v.new_log(16)
        self.assertEqual(self.lib.dll.mu_login_after_pass(ctypes.byref(world), ctypes.byref(inputs),
                                                          ctypes.byref(counter), ctypes.byref(log)), 0)
        inputs.world = 0x5c
        self.assertEqual(self.lib.dll.mu_login_after_pass(ctypes.byref(world), ctypes.byref(inputs),
                                                          ctypes.byref(counter), ctypes.byref(log)), 2)


if __name__ == '__main__':
    unittest.main()
