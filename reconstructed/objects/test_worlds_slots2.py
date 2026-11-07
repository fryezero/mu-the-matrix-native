"""RENDER-WORLDS-SLOTS2: RenderObjectVisual's outer flicker draw for the class worlds, and the custom/after render
slots of Santa Village 62, Imperial Guardian 69..72, 82, Arca War 92/96/101/111, Debenter 95, Uruk Mountain 100 and
Nars 110; private instruction comparisons."""
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
BODY, MESH, EFFECT = 0x966def, 0x966e4a, 0x13c0eaa


class WorldsSlots2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.lib = ws.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')
        cls.dll = cls.lib.dll
        cls.dll.mu_obj_visual_flicker.argtypes = [C.c_int32, C.c_int]

    def obj(self, typ, frame=0.0, state=0):
        o = C.create_string_buffer(v.OBJ_SIZE)
        o[0] = 1
        struct.pack_into('<i', o, 0x5c, typ)
        struct.pack_into('<i', o, 0x60, state)
        struct.pack_into('<i', o, 0x68, -1)
        struct.pack_into('<i', o, 0x74, 3)
        struct.pack_into('<f', o, 0xdc, 1.0)
        struct.pack_into('<f', o, 0xd0, frame)
        return o

    def slot(self, cls, world, o, after=False, bones=False, time=1000.0):
        log = v.new_log()
        sub = (C.c_int16 * 16)()
        bone = ws.BONE(lambda ctx, k, local, out: None) if bones else ws.BONE()
        m = ws.SlotModel(0, sub, 0, v.RAND_FN(), None, 0, bone, None)
        b = C.create_string_buffer(0x100)
        b[0x94] = 0xff
        if after:
            self.dll.mu_class_after(cls, o, b, 0, world, time, C.byref(m), C.byref(log))
            return None, v.log_events(log), b
        answer = self.dll.mu_class_custom(cls, o, b, 0, world, time, C.byref(m), C.byref(log))
        return answer, v.log_events(log), b

    def test_flicker_worlds(self):
        drawn = [w for w in range(-1, 300) if self.dll.mu_obj_visual_flicker(w, 1)]
        # RENDER-WORLDS-SLOTS3: every world, class or not (Tormenta 141 included); 4/7/8 draw it in mu_builtin_visual
        self.assertEqual(drawn, [w for w in range(-1, 300) if w not in (4, 7, 8)])
        self.assertFalse(any(self.dll.mu_obj_visual_flicker(w, 0) for w in range(-1, 300)))

    def test_dispatch(self):
        for world in (62, 69, 70, 71, 72, 82, 92, 95, 96, 100, 101, 110, 111):
            self.assertTrue(self.dll.mu_class_slots(world), world)
        for world in (73, 74, 90, 102):   # 121: RENDER-WORLDS-121
            self.assertFalse(self.dll.mu_class_slots(world), world)

    def test_santa(self):
        answer, events, b = self.slot(62, 62, self.obj(0x10))
        self.assertEqual((answer, [(e[0], e[2], e[3]) for e in events if e[0] == MESH]),
                         (1, [(MESH, 0, 2), (MESH, 1, 2), (MESH, 2, 2), (MESH, 2, 0x44)]))
        self.assertEqual(struct.unpack_from('<3f', b, 0x54), (0.0, 0.5, 0.5))
        self.assertEqual(self.slot(62, 63, self.obj(0x10))[0], 0)

    def test_imperial_guardian_forward(self):
        for cls, world in ((69, 72), (70, 70), (71, 71), (72, 74)):
            o = self.obj(0)
            self.assertEqual((self.slot(cls, world, o)[0], o[0xa]), (1, b'\x01'), (cls, world))
        self.assertEqual(self.slot(70, 71, self.obj(0))[0], 0)   # 70's own world test first
        answer, events, b = self.slot(72, 72, self.obj(0x61))
        self.assertEqual((answer, [e[0] for e in events if e[0] in (BODY, MESH)]), (1, [BODY]))
        self.assertEqual(self.slot(71, 71, self.obj(0x61))[0], 0)

    def test_imperial_guardian_latch(self):
        o = self.obj(0x73, frame=0.2, state=0x64)
        _, events, _ = self.slot(69, 69, o, bones=True)
        self.assertEqual([e[2] for e in events if e[0] == EFFECT], [0x52d])
        self.assertEqual(struct.unpack_from('<i', o, 0x60)[0], 0x65)
        o = self.obj(0x75, frame=7.2, state=0x65)
        _, events, _ = self.slot(69, 70, o, bones=True)
        self.assertEqual((struct.unpack_from('<i', o, 0x60)[0], [e for e in events if e[0] == EFFECT]), (0x64, []))

    def test_arca_war_forwards(self):
        for world, typ in ((92, 0x30), (96, 0x32), (101, 0x10), (111, 0x22)):
            answer, events, _ = self.slot(world, world, self.obj(typ))
            self.assertEqual(answer, 1, world)
            self.assertTrue(events, world)
        self.assertEqual(self.slot(96, 95, self.obj(0x32))[0], 0)   # the Arca War world test (its world list)
        _, events, _ = self.slot(111, 111, self.obj(0x8e), after=True)
        self.assertEqual([e[0] for e in events if e[0] in (BODY, MESH)], [MESH])

    def test_bitmaps(self):
        named = (C.c_int32 * 36)()
        for world, typ, index in ((82, 0x48, 0x8144), (95, 0x32, 0x81a7), (96, 0x32, 0x81a7), (110, 0x22, 0x7f1f),
                                  (92, 0x30, 0x8150)):
            self.assertIn(index, named[:self.dll.mu_world_slot_bitmaps(world, typ, named)], (world, typ))
            path, filt, wrap = C.c_char_p(), C.c_uint32(), C.c_uint32()
            self.assertTrue(self.dll.mu_world_slot_bitmap(world, index, C.byref(path), C.byref(filt), C.byref(wrap)))

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-slots2-orig-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_slots2.py'), '--cases', '200',
                            '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))


if __name__ == '__main__':
    unittest.main()
