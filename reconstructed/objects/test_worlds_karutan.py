"""RENDER-WORLDS-KARUTAN: Karutan 80/81's custom (0x00e14596) and after (0x00e1543e) render slots, its own code (not
Test Area 121's): the world tests, the after flags, 0x42's action choice, 0x81's pulsed 0x85bb mesh and the ten after
draws. Portable checks on synthetic objects; the instruction comparison is private."""
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
BODY, MESH, COLOR, STREAM = 0x966def, 0x966e4a, 0x54, 0x017ffef3   # STREAM: MU_OBJ_CALL_MODEL_STREAM


class SlotModel(C.Structure):   # mu_slot_model with RENDER-WORLDS-121's bone and action counts
    _fields_ = ws.SlotModel._fields_ + [('bone_count', C.c_int32), ('action_count', C.c_int32)]


class WorldsKarutanTests(unittest.TestCase):
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
        struct.pack_into('<i', o, 0x68, 5)
        struct.pack_into('<i', o, 0x74, 3)
        struct.pack_into('<4f', o, 0xa8, 0.8, 0.25, 0.5, 0.0)
        struct.pack_into('<f', o, 0xdc, 1.0)
        return o

    def slot(self, o, world=80, after=False, roll=0, time=1000.0):
        log = v.new_log()
        sub = (C.c_int16 * 16)()
        self.rolls = 0

        def rand(ctx):
            self.rolls += 1
            return roll
        self.rand = v.RAND_FN(rand)
        self.bone = ws.BONE(lambda ctx, k, local, out: None)   # the slots read no bone
        m = SlotModel(0, sub, 0, self.rand, None, 0, self.bone, None, 0, 4)
        b = C.create_string_buffer(0x100)
        b[0x94] = 0xff
        struct.pack_into('<3f', b, 0x54, 0.9, 0.8, 0.7)
        if after:
            self.dll.mu_class_after(80, o, b, 0, world, time, C.byref(m), C.byref(log))
            return None, v.log_events(log), b
        return self.dll.mu_class_custom(80, o, b, 0, world, time, C.byref(m), C.byref(log)), v.log_events(log), b

    def test_dispatch_world_tests_and_after_gate(self):
        self.assertTrue(self.dll.mu_class_slots(80) and self.dll.mu_class_slots(81))
        self.assertFalse(self.dll.mu_class_slots(3) or self.dll.mu_class_slots(0))
        for world in (80, 81):
            self.assertTrue(self.dll.mu_world_after_gate(world, self.dll.mu_world_class_after(world)))   # it runs
        for world in (80, 81, 102, 103, 106):   # 0x00e18ae9, 0x009dad2c, 0x009d3e63
            o = self.obj(0x38)
            self.assertEqual(self.slot(o, world=world)[0], 1)
            self.assertEqual(o[0xa], b'\x01')
        for world in (79, 82, 101, 107, 142, 0):
            o = self.obj(0x38)
            self.assertEqual(self.slot(o, world=world)[:2], (0, []))
            self.assertEqual(o[0xa], b'\x00')
        o = self.obj(3)   # the after slot tests 80/81 only
        self.assertEqual(self.slot(o, world=102, after=True)[1], [])
        self.assertEqual(self.dll.mu_world_defer(self.obj(3), 80), 0)   # the flag comes from the class slot now

    def test_after_flags_and_action_choice(self):
        for typ in (1, 3, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x3e, 0x3f, 0x77):
            o = self.obj(typ)
            self.assertEqual(self.slot(o)[:2], (1, []))
            self.assertEqual(o[0xa], b'\x01')
        o = self.obj(0x42, frame=18.99)   # below frame 19: no rand, the flag
        self.assertEqual(self.slot(o, roll=10)[:2], (1, []))
        self.assertEqual((self.rolls, o[0xa], struct.unpack_from('<H', o, 0x2a)[0]), (0, b'\x01', 0))
        o = self.obj(0x42, frame=19.0)   # rand() % 10 == 0: SetAction 1 (prior action 0, frame restarts)
        self.slot(o, roll=20)
        self.assertEqual((self.rolls, struct.unpack_from('<HH', o, 0x2a)), (1, (1, 0)))
        self.assertEqual(struct.unpack_from('<f', o, 0xd0)[0], 0.0)
        o = self.obj(0x42, action=1, frame=25.0)   # otherwise SetAction 0
        self.slot(o, roll=7)
        self.assertEqual(struct.unpack_from('<H', o, 0x2a)[0], 0)
        self.assertEqual(self.slot(self.obj(0x2e))[0], 0)   # no case: the generic draw

    def test_0x81_pulsed_mesh(self):
        answer, events, b = self.slot(self.obj(0x81), time=0.0)
        self.assertEqual(answer, 1)
        self.assertEqual([e[0] for e in events], [BODY, COLOR, MESH, COLOR, MESH])
        self.assertEqual(events[0][2:5], (2, struct.unpack('<I', struct.pack('<f', 1.0))[0], 3))
        self.assertEqual(struct.unpack('<i', struct.pack('<I', events[0][8]))[0], -1)   # hidden -1, not +0x68
        grey = struct.unpack('<3f', struct.pack('<3I', *events[1][2:5]))
        self.assertAlmostEqual(grey[0], 0.7)   # wave(-2.5) is 0 at time 0: 0 * 0.3 + 0.7
        self.assertEqual(len(set(grey)), 1)
        self.assertEqual((events[2][2], events[2][3], events[2][5], events[2][9]), (1, 2, 1, 0x85bb))
        self.assertEqual(struct.unpack('<3f', struct.pack('<3I', *events[3][2:5])),
                         struct.unpack('<3f', struct.pack('<3f', 0.9, 0.8, 0.7)))   # the body colour restored
        self.assertEqual((events[4][2], events[4][3], events[4][9]), (1, 0x44, 0xffffffff))
        self.assertEqual(struct.unpack_from('<3f', b, 0x54), struct.unpack('<3f', struct.pack('<3f', 0.9, 0.8, 0.7)))

    def test_after_draws(self):
        want = {1: [(1, 2), (2, 2), (3, 2), (0, 0x42)], 0x36: [(0, 0x42)], 0x37: [(0, 0x42)], 0x39: [(0, 0x42)],
                0x3a: [(0, 2), (1, 0x42), (3, 2), (2, 0x42)], 0x3f: [(0, 0x42), (1, 2), (2, 0x42), (3, 2)],
                0x42: [(0, 2), (1, 0x42)], 0x77: [(0, 2), (1, 0x42)]}
        for typ, meshes in want.items():
            _, events, b = self.slot(self.obj(typ), after=True)
            self.assertEqual([(e[2], e[3]) for e in events if e[0] == MESH], meshes, hex(typ))
            if typ in (0x37, 0x39):   # StreamMesh 0 around the scroll, restored to 0xff
                self.assertEqual([e[2] for e in events if e[0] == STREAM], [0, 0xff])
                self.assertEqual(b[0x94], b'\xff')
        for typ in (3, 0x38, 0x3e):
            _, events, _ = self.slot(self.obj(typ), after=True)
            self.assertEqual([(e[0], e[8]) for e in events], [(BODY, 5)])   # the hidden mesh +0x68
        self.assertEqual(self.slot(self.obj(0x81), after=True)[1], [])

    def test_bitmap(self):
        path, flt, wrap = C.c_char_p(), C.c_uint32(), C.c_uint32()
        out = (C.c_int32 * 36)()
        for world in (80, 81):
            self.assertTrue(self.dll.mu_world_slot_bitmap(world, 0x85bb, C.byref(path), C.byref(flt), C.byref(wrap)))
            self.assertEqual((path.value, flt.value, wrap.value),
                             (b'Object144\\sdsaferzone14B01_R.jpg', 0x2601, 0x2900))
            self.assertEqual(list(out[:self.dll.mu_world_slot_bitmaps(world, 0x81, out)]), [0x85bb])
            self.assertEqual(self.dll.mu_world_slot_bitmaps(world, 0x42, out), 0)
        self.assertFalse(self.dll.mu_world_slot_bitmap(79, 0x85bb, C.byref(path), C.byref(flt), C.byref(wrap)))

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_karutan.py'), '--cases', '200',
                            '--output', str(out)], check=True)
            report = json.loads(out.read_text())
            self.assertTrue(report['ok'])
            self.assertEqual(sorted(report['families']), ['actions_karutan', 'after_karutan', 'custom_karutan'])


if __name__ == '__main__':
    unittest.main()
