"""RENDER-WORLDS-AFTER2: class custom/after render slots, pre-move slot 0x74 and the slot bitmaps; private
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
import validate_worlds_after2 as wa2  # noqa: E402
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
BODY, MESH, SOUND, STREAM = 0x966def, 0x966e4a, 0x00a6ac96, 0x017ffef3


class WorldsAfter2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.lib = wa2.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')
        cls.dll = cls.lib.dll

    def obj(self, typ, hidden=-1, after=0):
        o = C.create_string_buffer(v.OBJ_SIZE)
        struct.pack_into('<i', o, 0x5c, typ)
        struct.pack_into('<i', o, 0x68, hidden)
        struct.pack_into('<i', o, 0x74, 3)
        struct.pack_into('<f', o, 0xdc, 1.0)
        o[0xa] = after
        return o

    def model(self):
        b = C.create_string_buffer(0x100)
        b[0x94] = 0xff
        return b

    def custom(self, world, o, flags=(), cls=None):
        log = v.new_log()
        sub = (C.c_int16 * 16)(*(list(flags) + [0] * (16 - len(flags))))
        m = wa2.SlotModel(len(flags), sub)
        answer = self.dll.mu_class_custom(cls or world, o, self.model(), 0, world, 1000.0, C.byref(m), C.byref(log))
        return answer, v.log_events(log)

    def test_classes(self):
        self.assertEqual([w for w in range(0, 200) if self.dll.mu_class_slots(w)],
                         [91, 113, 131, 132, 134, 135, 136, 137, 138, 139, 140, 142])

    def test_kanturu_flags_leave_the_first_pass(self):
        o = self.obj(8)
        answer, events = self.custom(137, o)
        self.assertEqual((answer, events, o[0xa]), (1, [], b'\x01'))
        o = self.obj(0x23)
        answer, events = self.custom(137, o)
        self.assertEqual((answer, o[0xa], struct.unpack_from('<i', o, 0x68)[0]), (1, b'\x01', 1))
        self.assertEqual([(e[0], e[8]) for e in events], [(BODY, 1)])
        self.assertEqual(self.custom(136, self.obj(8), cls=137), (0, []))   # its own world test

    def test_acheron_world_92_and_flags(self):
        for world in (91, 92):
            o = self.obj(0x1c)
            self.assertEqual(self.custom(world, o, cls=91), (1, []))
            self.assertEqual(o[0xa], b'\x01')
        answer, events = self.custom(91, self.obj(0x30))
        self.assertEqual([e[-1] for e in events], [0xffffffff, 0x8150, 0x814f, 0x814f, 0xffffffff])

    def test_burning_kethotum_mesh_loop(self):
        answer, events = self.custom(136, self.obj(0x9a), flags=[-1, 1, 0, 1])
        self.assertEqual(answer, 1)
        self.assertEqual([(e[2], e[3]) for e in events], [(0, 2), (1, 0x42), (2, 2), (3, 0x42)])

    def test_stream_byte(self):
        answer, events = self.custom(140, self.obj(0x1f))
        self.assertEqual([e[2] for e in events if e[0] == STREAM], [3, 0xff])

    def test_bitmaps(self):
        out = (C.c_int32 * 4)()
        n = self.dll.mu_world_slot_bitmaps(137, 7, out)
        self.assertEqual(out[:n], [0x7f1f, 0x802e, 0x802d, 0x802c])
        path, filt, wrap = C.c_char_p(), C.c_uint32(), C.c_uint32()
        self.assertTrue(self.dll.mu_world_slot_bitmap(129, 0x82df, C.byref(path), C.byref(filt), C.byref(wrap)))
        self.assertEqual((path.value, filt.value, wrap.value), (b'Object131\\so_light01.jpg', 0x2601, 0x2901))
        self.assertTrue(self.dll.mu_world_slot_bitmap(136, 0x8341, C.byref(path), C.byref(filt), C.byref(wrap)))
        self.assertEqual(path.value, b'Object137\\hsBurntwoodA01_R.jpg')
        self.assertFalse(self.dll.mu_world_slot_bitmap(0, 0x8341, C.byref(path), C.byref(filt), C.byref(wrap)))

    def test_premove(self):
        def run(cls, world, o, state=0):
            log = v.new_log()
            self.dll.mu_class_premove(cls, o, 0, world, state, v.RAND_FN(lambda c: 0), None, C.byref(log))
            return [e[2] for e in v.log_events(log) if e[0] == SOUND]
        self.assertEqual(run(69, 0x48, self.obj(0)), [0x38f])
        self.assertEqual(run(71, 0x46, self.obj(0), 2), [0x38d])
        self.assertEqual(run(71, 0x46, None, 2), [])
        self.assertEqual(run(80, 80, self.obj(0x42)), [0x3db])
        self.assertEqual(run(122, 122, self.obj(0xa1)), [0x4d3])
        self.assertEqual(run(122, 122, self.obj(0x1a)), [0x4d4])   # rand() % 50 == 0
        self.assertEqual(self.dll.mu_class_premove(92, None, 0, 92, 0, v.RAND_FN(lambda c: 0), None, None), 0)

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-after2-orig-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_after2.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(sum(r['cases'] for r in result['families'].values()), 32216)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), 33)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))


if __name__ == '__main__':
    unittest.main()
