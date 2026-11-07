"""RENDER-WORLDS-SLOTS: the custom/after render slots of Loren Market 79, Event square 114, Ferea 112, Swamp of
Darkness 122 and Kubera 123..127, the invisible-move slots of 142..145 and the trivial slots; private instruction
comparisons."""
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
BODY, MESH, STREAM, COLOR = 0x966def, 0x966e4a, 0x017ffef3, 0x54


class WorldsSlotsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.lib = ws.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')
        cls.dll = cls.lib.dll
        cls.dll.mu_obj_handler_moves.argtypes = [C.c_void_p, C.c_int32, C.POINTER(C.c_float),
                                                 C.POINTER(C.c_float), C.c_int32]
        cls.dll.mu_obj_handler_moves.restype = C.c_uint8
        cls.dll.mu_slots_more_handler.argtypes = [C.c_int32, C.POINTER(C.c_int32)]

    def obj(self, typ, action=0, frame=0.0):
        o = C.create_string_buffer(v.OBJ_SIZE)
        o[0] = 1
        struct.pack_into('<i', o, 0x5c, typ)
        struct.pack_into('<i', o, 0x68, -1)
        struct.pack_into('<i', o, 0x74, 3)
        struct.pack_into('<f', o, 0xdc, 1.0)
        struct.pack_into('<H', o, 0x2a, action)
        struct.pack_into('<f', o, 0xd0, frame)
        return o

    def slot(self, cls, world, o, after=False, meshes=0, frames=0, state=0, time=1000.0):
        log = v.new_log()
        sub = (C.c_int16 * 16)()
        m = ws.SlotModel(meshes, sub, frames, v.RAND_FN(), None, state)
        b = C.create_string_buffer(0x100)
        b[0x94] = 0xff
        if after:
            self.dll.mu_class_after(cls, o, b, 0, world, time, C.byref(m), C.byref(log))
            return None, v.log_events(log), b
        answer = self.dll.mu_class_custom(cls, o, b, 0, world, time, C.byref(m), C.byref(log))
        return answer, v.log_events(log), b

    def test_dispatch(self):
        for world in (79, 112, 114, 122, 123, 124, 125, 126, 127):
            self.assertTrue(self.dll.mu_class_slots(world), world)
        for world in (73, 115, 116, 120, 128 - 100):   # 121: RENDER-WORLDS-121
            self.assertFalse(self.dll.mu_class_slots(world), world)

    def test_market_flags(self):
        for world in (79, 114):
            o = self.obj(0x1e)
            answer, events, _ = self.slot(world, world, o)
            self.assertEqual((answer, events, o[0xa]), (1, [], b'\x01'))
        o = self.obj(8)
        self.assertEqual(self.slot(79, 114, o)[0], 0)   # Loren Market's slot in Event square's world: no
        self.assertEqual(o[0xa], b'\x00')
        _, events, _ = self.slot(79, 79, self.obj(8), after=True)
        self.assertEqual([e[2] for e in events if e[0] == MESH], [2, 3, 4, 1, 0])

    def test_kubera_gems_and_bitmaps(self):
        words = (C.c_int32 * 12)()
        self.assertTrue(self.dll.mu_slots_more_handler(124, words))
        self.assertEqual(words[0], 0x82b7)
        self.assertFalse(self.dll.mu_slots_more_handler(122, words))
        _, events, b = self.slot(126, 126, self.obj(0x2f, action=3, frame=5.0), meshes=8, frames=30)
        self.assertEqual([e[2] for e in events if e[0] == MESH], list(range(8)))
        self.assertEqual(b[0x94], b'\x05')   # the gem mesh's StreamMesh byte stays set
        _, events, _ = self.slot(123, 123, self.obj(0x75))
        self.assertEqual([e[-1] for e in events if e[0] == MESH], [0x82af, 0x82b0, 0x829a])
        out = (C.c_int32 * 36)()
        self.assertEqual(list(out[:self.dll.mu_world_slot_bitmaps(127, 0xa0, out)]),
                         [0x82bd, 0x829f, 0x82a0, 0x82a9, 0x82aa])
        path, filt, wrap = C.c_char_p(), C.c_uint32(), C.c_uint32()
        self.assertTrue(self.dll.mu_world_slot_bitmap(125, 0x829a, C.byref(path), C.byref(filt), C.byref(wrap)))
        self.assertEqual((path.value, filt.value, wrap.value), (b'Object124\\sdchrome01.jpg', 0x2601, 0x2901))
        self.assertFalse(self.dll.mu_world_slot_bitmap(122, 0x829a, C.byref(path), C.byref(filt), C.byref(wrap)))

    def test_ferea_statue_and_door(self):
        for state, texture in ((0, 0xffffffff), (2, 0x8225), (3, 0x8225), (4, 0xffffffff)):
            _, events, _ = self.slot(112, 112, self.obj(0x7b), state=state)
            self.assertEqual([(e[0], e[-1]) for e in events], [(BODY, texture)])
        o = self.obj(0x27, action=1)
        self.slot(112, 112, o)
        self.assertAlmostEqual(struct.unpack_from('<f', o, 0xb0)[0], 0.1, places=6)
        self.assertEqual(self.slot(112, 0, self.obj(0x72))[0], 1)   # no world test

    def test_dark_crocodile(self):
        _, events, _ = self.slot(122, 122, self.obj(0x84))
        self.assertEqual([(e[0], e[-1]) for e in events], [(BODY, 0xffffffff)] + [(MESH, 0x8273)] * 3)
        self.assertEqual(self.slot(122, 123, self.obj(0x84))[0], 0)

    def test_invisible_move(self):
        xs = (C.c_float * 4)(0.0, 0.0, 100.0, 100.0)   # the frustum polygon's winding (validate_object_render)
        ys = (C.c_float * 4)(0.0, 100.0, 100.0, 0.0)
        for world, typ, moves in ((142, 0xa0, 1), (142, 0xa2, 0), (143, 0x80, 1), (144, 0xc8, 1), (144, 0xc9, 0),
                                  (141, 0x1f, 1), (140, 0xa0, 0)):
            o = self.obj(typ)
            struct.pack_into('<3f', o, 0x158, 5000.0, 5000.0, 0.0)
            struct.pack_into('<f', o, 0xc0, -30.0)
            self.assertEqual(self.dll.mu_obj_handler_moves(o, world, xs, ys, 6), moves, (world, typ))
        o = self.obj(0x13)
        self.assertEqual(self.dll.mu_obj_handler_moves(o, 145, None, None, 6), 0)
        o[0xb] = 1
        self.assertEqual(self.dll.mu_obj_handler_moves(o, 145, None, None, 6), 1)
        self.assertEqual(self.dll.mu_obj_handler_moves(None, 143, xs, ys, 6), 0)

    def test_trivial_slots(self):
        for world in (62, 64, 95, 100, 115, 116, 117, 118, 119, 120):
            o = self.obj(0x10)
            if world not in (62, 95, 100):   # their custom slots draw (RENDER-WORLDS-SLOTS2); the after slots stay empty
                answer, events, _ = self.slot(world, world, o)
                self.assertEqual((answer, events), (0, []))
            self.assertEqual(self.slot(world, world, o, after=True)[1], [])

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-slots-orig-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_slots.py'), '--cases', '200',
                            '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))


if __name__ == '__main__':
    unittest.main()
