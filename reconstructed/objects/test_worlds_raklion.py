"""RENDER-WORLDS-RAKLION: Raklion 57/58's custom (0x00e949f8) and after (0x00e96536) render slots, Test Area 121's
code with Raklion's row (the world test 0x00ea233c, type 0x52's frame restart behind the handler byte +0x22).
Portable checks on synthetic objects; the instruction comparison is private."""
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
import validate_worlds_slots as ws  # noqa: E402
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
BODY, MESH, PARTICLE, VERTEX_LIGHT = 0x966def, 0x966e4a, 0x168fafd, 0x06fd0918


class SlotModel(C.Structure):   # mu_slot_model with RENDER-WORLDS-121's bone and action counts
    _fields_ = ws.SlotModel._fields_ + [('bone_count', C.c_int32), ('action_count', C.c_int32)]


class WorldsRaklionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.dll = ws.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}').dll
        cls.dll.mu_world_after_gate.argtypes = [C.c_int32, C.c_int]
        cls.dll.mu_world_class_after.argtypes = [C.c_int32]
        cls.dll.mu_world_defer.argtypes = [C.c_void_p, C.c_int32]

    def obj(self, typ, action=0, frame=0.0):
        o = C.create_string_buffer(v.OBJ_SIZE)
        o[0] = 1
        struct.pack_into('<i', o, 0x5c, typ)
        struct.pack_into('<H', o, 0x2a, action)
        struct.pack_into('<ff', o, 0xd0, frame, frame - 1.0)
        struct.pack_into('<i', o, 0x68, -1)
        struct.pack_into('<i', o, 0x74, 3)
        struct.pack_into('<f', o, 0xdc, 1.0)
        return o

    def slot(self, o, world=57, gate=1, after=False, cls=57, bones=2):
        log = v.new_log()
        sub = (C.c_int16 * 16)()
        bone = ws.BONE(lambda ctx, k, local, out: [out.__setitem__(q, float(100 * k + q)) for q in range(3)])
        m = SlotModel(0, sub, 0, v.RAND_FN(lambda ctx: 0), None, gate, bone, None, bones, 4)
        b = C.create_string_buffer(0x100)
        b[0x94] = 0xff
        if after:
            self.dll.mu_class_after(cls, o, b, 0, world, 1000.0, C.byref(m), C.byref(log))
            return None, v.log_events(log)
        return self.dll.mu_class_custom(cls, o, b, 0, world, 1000.0, C.byref(m), C.byref(log)), v.log_events(log)

    def test_dispatch_world_test_and_after_gate(self):
        self.assertTrue(self.dll.mu_class_slots(57) and self.dll.mu_class_slots(58))
        self.assertFalse(self.dll.mu_class_slots(56) or self.dll.mu_class_slots(59))
        for world in (57, 58):
            self.assertEqual(self.slot(self.obj(9), world=world)[0], 1)
            self.assertTrue(self.dll.mu_world_after_gate(world, self.dll.mu_world_class_after(world)))   # it runs
        for world in (56, 59, 121, 0):   # 0x00ea233c: nothing drawn, nothing written
            o = self.obj(0x2e)
            self.assertEqual(self.slot(o, world=world), (0, []))
            self.assertEqual(o[0xa], b'\x00')
        o = self.obj(0x2e)   # the after flag comes from the class slot now, not mu_world_defer
        self.assertEqual(self.dll.mu_world_defer(o, 57), 0)
        self.assertEqual((self.slot(o)[0], o[0xa]), (1, b'\x01'))

    def test_vertex_light_particles_and_meshes(self):
        o = self.obj(9)
        _, events = self.slot(o)
        self.assertEqual([e[0] for e in events], [VERTEX_LIGHT, BODY])
        self.assertEqual(struct.unpack_from('<3f', o, 0xec), (1.0, 1.0, 1.0))
        _, events = self.slot(self.obj(0x13, frame=3.0))
        self.assertEqual([(e[2], e[12]) for e in events if e[0] == PARTICLE], [(0x801e, 7)] * 2 + [(0x801c, 8)] * 2)
        _, events = self.slot(self.obj(0x14))
        self.assertEqual([e[9] for e in events if e[0] == MESH], [0xffffffff, 0xffffffff, 0x800a, 0x800a])
        o = self.obj(0x53)
        _, events = self.slot(o)
        self.assertEqual([(e[2], e[3]) for e in events if e[0] == MESH], [(0, 2), (1, 2), (2, 0x42), (3, 0x42)])
        self.assertEqual(o[0xa], b'\x01')
        self.assertEqual([(e[0], e[2]) for e in self.slot(self.obj(0x53), after=True)[1]], [(MESH, 4)])
        self.assertEqual([(e[0], e[2]) for e in self.slot(self.obj(0x5c), after=True)[1]], [(MESH, 1)])

    def test_frame_gate(self):
        for gate, want in ((1, (7.5, 6.5)), (2, (7.5, 6.5)), (0, (0.0, 0.0))):
            o = self.obj(0x52, frame=7.5)
            answer, events = self.slot(o, gate=gate)
            self.assertEqual((answer, [e[0] for e in events]), (1, [BODY]))
            self.assertEqual(struct.unpack_from('<ff', o, 0xd0), want)
        o = self.obj(0x52, frame=7.5)   # 121's row has no gate
        self.slot(o, world=121, gate=0, cls=121)
        self.assertEqual(struct.unpack_from('<f', o, 0xd0)[0], 7.5)

    def test_bitmap(self):
        path, flt, wrap = C.c_char_p(), C.c_uint32(), C.c_uint32()
        out = (C.c_int32 * 36)()
        for world in (57, 58):
            self.assertTrue(self.dll.mu_world_slot_bitmap(world, 0x800a, C.byref(path), C.byref(flt), C.byref(wrap)))
            self.assertEqual((path.value, flt.value, wrap.value), (b'Effect\\Chrome08.jpg', 0x2601, 0x2900))
            self.assertEqual(list(out[:self.dll.mu_world_slot_bitmaps(world, 0x14, out)]), [0x800a])
        self.assertFalse(self.dll.mu_world_slot_bitmap(56, 0x800a, C.byref(path), C.byref(flt), C.byref(wrap)))

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_raklion.py'), '--cases', '200',
                            '--output', str(out)], check=True)
            report = json.loads(out.read_text())
            self.assertTrue(report['ok'])
            self.assertEqual(sorted(report['families']), ['actions_raklion', 'after_raklion', 'custom_raklion'])


if __name__ == '__main__':
    unittest.main()
