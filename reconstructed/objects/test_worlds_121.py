"""RENDER-WORLDS-121: Test Area 121's custom (0x00d58bd8) and after (0x00d5a6cc) render slots, Devias 0x67's action
choice (0x017f9d79) and the shared SetAction 0x012affa4; private instruction comparisons."""
import ctypes as C
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
import validate_worlds_slots as ws  # noqa: E402
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
BODY, MESH, PARTICLE, VERTEX_LIGHT = 0x966def, 0x966e4a, 0x168fafd, 0x06fd0918


class SlotModel(C.Structure):   # mu_slot_model with RENDER-WORLDS-121's bone and action counts
    _fields_ = ws.SlotModel._fields_ + [('bone_count', C.c_int32), ('action_count', C.c_int32)]


class Worlds121Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.lib = ws.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')
        d = cls.dll = cls.lib.dll
        d.mu_obj_set_action.argtypes = [C.c_void_p, C.c_int32, C.c_int32]
        d.mu_obj_set_action.restype = None
        d.mu_devias_action_pick.argtypes = [C.c_void_p, C.c_int16, C.c_int16, C.c_int32, v.RAND_FN, C.c_void_p]
        d.mu_obj_frame_whole.argtypes = [C.c_float]
        d.mu_obj_frame_whole.restype = C.c_int16
        d.mu_world_after_gate.argtypes = [C.c_int32, C.c_int]
        d.mu_world_class_after.argtypes = [C.c_int32]

    def obj(self, typ, action=0, frame=0.0):
        o = C.create_string_buffer(v.OBJ_SIZE)
        o[0] = 1
        struct.pack_into('<i', o, 0x5c, typ)
        struct.pack_into('<H', o, 0x2a, action)
        struct.pack_into('<f', o, 0xd0, frame)
        struct.pack_into('<i', o, 0x68, -1)
        struct.pack_into('<i', o, 0x74, 3)
        struct.pack_into('<f', o, 0xdc, 1.0)
        struct.pack_into('<3f', o, 0x164, 10.0, 20.0, 30.0)
        return o

    def slot(self, o, after=False, bones=2, actions=4, rolls=(), world=121, time=1000.0):
        log = v.new_log()
        sub = (C.c_int16 * 16)()
        values = list(rolls)
        rand = v.RAND_FN(lambda ctx: values.pop(0))
        bone = ws.BONE(lambda ctx, k, local, out: [out.__setitem__(q, float(100 * k + q)) for q in range(3)])
        m = SlotModel(0, sub, 0, rand, None, 0, bone, None, bones, actions)
        b = C.create_string_buffer(0x100)
        b[0x94] = 0xff
        if after:
            self.dll.mu_class_after(121, o, b, 0, world, time, C.byref(m), C.byref(log))
            return None, v.log_events(log)
        return self.dll.mu_class_custom(121, o, b, 0, world, time, C.byref(m), C.byref(log)), v.log_events(log)

    def test_dispatch_and_after_gate(self):
        self.assertTrue(self.dll.mu_class_slots(121))
        # the client's after pass never runs in 121: 0x79 is outside its world list, handler byte +5 stays 0
        self.assertFalse(self.dll.mu_world_after_gate(121, self.dll.mu_world_class_after(121)))
        self.assertEqual(self.slot(self.obj(0x52), world=7)[0], 1)   # no world test

    def test_vertex_light_types(self):
        for typ in range(6, 13):
            o = self.obj(typ)
            answer, events = self.slot(o)
            self.assertEqual((answer, [e[0] for e in events]), (1, [VERTEX_LIGHT, BODY]), typ)
            self.assertEqual(struct.unpack('<f', struct.pack('<I', events[0][2]))[0], 0.5)
            self.assertEqual(struct.unpack_from('<3f', o, 0xec), (1.0, 1.0, 1.0))
        self.assertEqual(self.slot(self.obj(5))[0], 0)
        self.assertNotIn(VERTEX_LIGHT, [e[0] for e in self.slot(self.obj(13))[1]])

    def test_action_choice(self):
        o = self.obj(0x10, action=0, frame=19.0)
        self.assertEqual(self.slot(o, rolls=[7])[0], 1)
        self.assertEqual(struct.unpack_from('<HH', o, 0x2a), (1, 0))   # SetAction(7 % 2): prior action 0
        o = self.obj(0x11, action=1, frame=20.0)
        self.slot(o, rolls=[95])   # 95 % 100 >= 90, odd: action 3
        self.assertEqual(struct.unpack_from('<H', o, 0x2a)[0], 3)
        o = self.obj(0x11, action=1, frame=20.0)
        self.slot(o, actions=3, rolls=[95])   # beyond the model's action count: unchanged
        self.assertEqual(struct.unpack_from('<H', o, 0x2a)[0], 1)
        o = self.obj(0x11, action=3, frame=97.5)   # action 3 waits for frame 98
        self.slot(o, rolls=[])
        self.assertEqual(struct.unpack_from('<H', o, 0x2a)[0], 3)

    def test_particles(self):
        answer, events = self.slot(self.obj(0x13, frame=3.0), bones=3)
        parts = [e for e in events if e[0] == PARTICLE]
        self.assertEqual([(e[2], e[12]) for e in parts], [(0x801e, 7)] * 3 + [(0x801c, 8)] * 3)
        self.assertEqual(struct.unpack('<3f', struct.pack('<3I', *parts[1][3:6])), (100.0, 101.0, 102.0))
        self.assertEqual(struct.unpack('<3f', struct.pack('<3I', *parts[0][6:9])), (10.0, 20.0, 30.0))
        self.assertEqual(events[-1][0], BODY)
        o = self.obj(0x13, frame=20.0)
        self.slot(o, bones=0)
        self.assertEqual(struct.unpack_from('<HH', o, 0x2a), (1, 0))   # a direct write: no prior action change
        events = self.slot(self.obj(0x14, frame=10.0))[1]
        self.assertEqual([e[0] for e in events][:4], [MESH] * 4)
        self.assertEqual([e[9] for e in events[:4]], [0xffffffff, 0xffffffff, 0x800a, 0x800a])
        self.assertEqual(sum(e[0] == PARTICLE for e in events), 5)   # bone 5, then bones 8 and 11 twice each
        self.assertEqual(sum(e[0] == PARTICLE for e in self.slot(self.obj(0x15, frame=6.0))[1]), 10)

    def test_after(self):
        o = self.obj(0x4c)
        self.assertEqual([e[0] for e in self.slot(o, after=True, time=1000.0)[1]], [BODY])
        want = [math.sin(1000.0 * k) * 0.2 + 0.5 for k in (0.002, 0.0015, 0.0014)]
        for got, w in zip(struct.unpack_from('<3f', o, 0xec), want):
            self.assertAlmostEqual(got, w, places=5)
        self.assertEqual([(e[0], e[2]) for e in self.slot(self.obj(0x53), after=True)[1]], [(MESH, 4)])
        self.assertEqual(self.slot(self.obj(0x10), after=True)[1], [])

    def test_bitmap(self):
        path, flt, wrap = C.c_char_p(), C.c_uint32(), C.c_uint32()
        self.assertTrue(self.dll.mu_world_slot_bitmap(121, 0x800a, C.byref(path), C.byref(flt), C.byref(wrap)))
        self.assertEqual((path.value, flt.value, wrap.value), (b'Effect\\Chrome08.jpg', 0x2601, 0x2900))
        out = (C.c_int32 * 36)()
        self.assertEqual(list(out[:self.dll.mu_world_slot_bitmaps(121, 0x14, out)]), [0x800a])
        self.assertEqual(self.dll.mu_world_slot_bitmaps(121, 0x13, out), 0)

    def test_set_action_and_devias(self):
        o = self.obj(0x67, action=2, frame=5.5)
        self.dll.mu_obj_set_action(o, 4, 3)
        self.assertEqual(struct.unpack_from('<HH', o, 0x2a) + struct.unpack_from('<ff', o, 0xd0), (3, 2, 0.0, 5.5))
        self.dll.mu_obj_set_action(o, 4, 4)   # out of range
        self.dll.mu_obj_set_action(o, 4, 3)   # the same action
        self.assertEqual(struct.unpack_from('<HH', o, 0x2a), (3, 2))
        draws = []
        rand = v.RAND_FN(lambda ctx: draws.append(1) or 64)   # 64 % 32 == 0: action 1
        o = self.obj(0x67, action=0, frame=9.0)
        self.assertEqual(self.dll.mu_devias_action_pick(o, 9, 10, 4, rand, None), 1)
        self.assertEqual(struct.unpack_from('<H', o, 0x2a)[0], 1)
        self.assertEqual(self.dll.mu_devias_action_pick(o, 8, 10, 4, rand, None), 0)
        self.assertEqual(self.dll.mu_devias_action_pick(self.obj(0x64), 9, 10, 4, rand, None), 0)
        self.assertEqual(len(draws), 1)
        self.assertEqual([self.dll.mu_obj_frame_whole(f) for f in (37.9, -1.5, 70000.0, float('nan'))],
                         [37, -1, 70000 - 65536, 0])

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_121.py'), '--cases', '200',
                            '--output', str(out)], check=True)
            import json
            report = json.loads(out.read_text())
            self.assertTrue(report['ok'])
            self.assertEqual(sorted(report['families']), ['after_121', 'custom_121', 'devias_67'])


if __name__ == '__main__':
    unittest.main()
