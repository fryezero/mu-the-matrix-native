"""RENDER-WORLDS-AFTER3: the custom/after render slots of 133, 141, 143, 144, 145 and their bitmaps; private
instruction comparisons."""
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
import validate_worlds_after3 as wa3  # noqa: E402
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
BODY, MESH, SOUND, STREAM, LIGHT = 0x966def, 0x966e4a, 0x00a6ac96, 0x017ffef3, 0x016cacfc


class WorldsAfter3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.lib = wa3.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')
        cls.dll = cls.lib.dll

    def obj(self, typ, alpha=1.0, live=1):
        o = C.create_string_buffer(v.OBJ_SIZE)
        o[0] = live
        struct.pack_into('<i', o, 0x5c, typ)
        struct.pack_into('<i', o, 0x68, -1)
        struct.pack_into('<i', o, 0x74, 3)
        struct.pack_into('<f', o, 0xdc, alpha)
        return o

    def model(self, action=0, frame=0.0, whole=0):
        b = C.create_string_buffer(0x100)
        b[0x94] = 0xff
        struct.pack_into('<H', b, 0xa8, action)
        struct.pack_into('<f', b, 0xac, frame)
        struct.pack_into('<h', b, 0xb4, whole)
        return b

    def slot(self, world, o, b=None, after=False, frames=0, rand=None, time=1000.0):
        log = v.new_log()
        sub = (C.c_int16 * 16)()
        fn = v.RAND_FN(rand or (lambda c: 0))
        m = wa3.SlotModel(0, sub, frames, fn if rand else v.RAND_FN(), None)
        b = b or self.model()
        if after:
            self.dll.mu_class_after(world, o, b, 0, world, time, C.byref(m), C.byref(log))
            return None, v.log_events(log)
        return self.dll.mu_class_custom(world, o, b, 0, world, time, C.byref(m), C.byref(log)), v.log_events(log)

    def test_world_tests(self):
        for world in (133, 141, 143, 144):
            self.assertEqual(self.dll.mu_class_custom(world, self.obj(0x99), self.model(), 0, world + 1, 0.0, None,
                                                      None), 0)
        answer, events = self.slot(145, self.obj(0x13, alpha=0.5))   # 145's custom: no world test, alpha < 0.9
        self.assertEqual((answer, events), (1, []))

    def test_arnil_stream_meshes(self):
        answer, events = self.slot(133, self.obj(0x91))
        self.assertEqual(answer, 1)
        self.assertEqual([e[2] for e in events if e[0] == STREAM], [1, 2, 3, 4, 5, 0xff])
        self.assertEqual([e[2] for e in events if e[0] == MESH], [0, 1, 2, 3, 4, 5])
        answer, events = self.slot(133, self.obj(0x94))
        self.assertEqual([e[2] for e in events if e[0] == STREAM], [1, 2, 3])   # left set

    def test_water_bitmaps(self):
        for world, typ, base, time in ((133, 0x8f, 0x8320, 1000.0), (144, 0x40, 0x8348, 2200.0),
                                       (145, 0x31, 0x838a, 0.0), (143, 0x1c, 0x8589, 3000.0)):
            _, events = self.slot(world, self.obj(typ), after=True, time=time)
            self.assertEqual([(e[0], e[-1]) for e in events], [(BODY, base + int(time * 0.015) % 32)])
        out = (C.c_int32 * 36)()
        self.assertEqual(self.dll.mu_world_slot_bitmaps(141, 0x41, out), 32)
        path, filt, wrap = C.c_char_p(), C.c_uint32(), C.c_uint32()
        self.assertTrue(self.dll.mu_world_slot_bitmap(141, 0x84ad, C.byref(path), C.byref(filt), C.byref(wrap)))
        self.assertEqual((path.value, filt.value, wrap.value), (b'Object142\\wt31_R.jpg', 0x2601, 0x2901))
        self.assertTrue(self.dll.mu_world_slot_bitmap(144, 0x8341, C.byref(path), C.byref(filt), C.byref(wrap)))
        self.assertEqual(path.value, b'Object145\\hsBurntwoodA01_R.jpg')

    def test_swamp_after_needs_live(self):
        self.assertEqual(self.slot(144, self.obj(0x50, live=0), after=True)[1], [])
        self.assertEqual([e[0] for e in self.slot(144, self.obj(0x50), after=True)[1]], [BODY])

    def test_145_fade_and_sound(self):
        o = self.obj(0x99)
        struct.pack_into('<f', o, 0x188, 0.99)
        answer, events = self.slot(145, o, self.model(action=2, whole=2))
        self.assertEqual([e[2] for e in events if e[0] == SOUND], [0x5b4])
        self.assertEqual(struct.unpack_from('<f', o, 0x188)[0], 1.0)

    def test_tormenta_frame_window(self):
        self.assertEqual(self.slot(141, self.obj(0x2c), self.model(frame=0.5), frames=10)[1], [])
        self.assertEqual(len(self.slot(141, self.obj(0x2c), self.model(frame=5.0), frames=10)[1]), 1)

    def test_kardamahal_light(self):
        _, events = self.slot(143, self.obj(0x71), after=True, rand=lambda c: 1)
        self.assertEqual([e[0] for e in events], [LIGHT])
        self.assertAlmostEqual(struct.unpack('<f', struct.pack('<I', events[0][4]))[0], 0.56, places=5)
        self.assertEqual(self.slot(143, self.obj(0x71), after=True)[1], [])   # no rand: no request

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-after3-orig-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_after3.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(sum(r['cases'] for r in result['families'].values()), 10212)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), 51)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))


if __name__ == '__main__':
    unittest.main()
