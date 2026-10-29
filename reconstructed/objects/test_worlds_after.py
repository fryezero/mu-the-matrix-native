"""RENDER-WORLDS-AFTER: second-pass world test, Abyss custom/after slots, chain predicates, frame time; private
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
import validate_worlds_after as wa  # noqa: E402
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
BODY, MESH, AFTER_DRAW = 0x966def, 0x966e4a, 0x16d6791
# The 48 class worlds (docs/research/world-handler-coverage.json).
CLASS_WORLDS = [57, 58, 62, 63, 64, 82, 69, 70, 71, 72, 79, 80, 81, 91, 92, 96, 101, 111, 93, 94, 95, 100, 110,
                112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127] + list(range(128, 146))


class WorldsAfterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/particles')], check=True)
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.tmp = tempfile.TemporaryDirectory(prefix='worlds-after-test-')
        cls.lib = wa.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}', wa.build_frame(cls.tmp.name))
        cls.dll = cls.lib.dll
        cls.dll.mu_world_after_gate.argtypes = [C.c_int32, C.c_int]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def obj(self, typ, **fields):
        o = C.create_string_buffer(v.OBJ_SIZE)
        struct.pack_into('<i', o, 0x5c, typ)
        struct.pack_into('<i', o, 0x68, -1)
        struct.pack_into('<i', o, 0x74, fields.get('blend', 3))
        struct.pack_into('<f', o, 0xdc, 1.0)
        struct.pack_into('<H', o, 0x2a, fields.get('action', 0))
        struct.pack_into('<f', o, 0xd0, fields.get('frame', 0.0))
        return o

    def test_gate_and_class_flag(self):
        for w in (3, 8, 0x25, 0x2a, 0x33, 0x39, 0x50, 0x5e, 0x7a, 0x80, 0x82, 0x85):
            self.assertTrue(self.dll.mu_world_after_gate(w, 0), w)
        for w in (0, 1, 2, 4, 10, 0x24, 0x2b, 0x86, 0x91):
            self.assertFalse(self.dll.mu_world_after_gate(w, 0), w)
            self.assertTrue(self.dll.mu_world_after_gate(w, 1), w)
        self.assertEqual([w for w in range(0, 200) if self.dll.mu_world_class_after(w)], list(range(134, 146)))

    def test_chain_hooks_inactive_in_class_worlds(self):
        predicates = sorted({p for ps, _ in wa.CHAIN.values() for p in ps})
        active = [(w, hex(p)) for w in CLASS_WORLDS for p in predicates if self.dll.mu_world_chain_predicate(p, w)]
        self.assertEqual(active, [])
        self.assertTrue(self.dll.mu_world_chain_predicate(0xe74a3b, 0x25))

    def test_abyss_custom_and_after(self):
        rand = v.RAND_FN(lambda c: 9)
        for w in (128, 129, 130):
            for typ in (0x17, 0x26, 0x28, 0x2c, 0x32):
                log = v.new_log()
                self.assertEqual(self.dll.mu_abyss_custom(w, self.obj(typ), 0, w, 0.0, rand, None, C.byref(log)), 1)
                self.assertEqual(v.log_events(log), [])   # skipped by the first pass
                log = v.new_log()
                self.assertEqual(self.dll.mu_abyss_after(w, self.obj(typ), 0, w, C.byref(log)), 1)
                events = v.log_events(log)
                self.assertEqual([(e[0], e[2]) for e in events], [(BODY, 2)])
            log = v.new_log()
            self.assertEqual(self.dll.mu_abyss_custom(w, self.obj(0x29), 0, w, 0.0, rand, None, C.byref(log)), 0)
            log = v.new_log()
            self.dll.mu_abyss_after(w, self.obj(0x29), 0, w, C.byref(log))
            self.assertEqual([(e[0], e[3], e[-1]) for e in v.log_events(log)], [(MESH, 0x42, 0x82de)])
            o = self.obj(7, action=0, frame=20.0)
            log = v.new_log()
            self.dll.mu_abyss_custom(w, o, 0, w, 0.0, rand, None, C.byref(log))
            self.assertEqual(struct.unpack_from('<H', o.raw, 0x2a)[0], 1)   # 9 % 10 >= 8 and the frame limit
            self.assertEqual([e[0] for e in v.log_events(log)], [BODY])
            log = v.new_log()
            self.dll.mu_abyss_custom(w, self.obj(0x34), 0, w, 1000.0, rand, None, C.byref(log))
            self.assertEqual([(e[0], e[-1]) for e in v.log_events(log)], [(MESH, 0xffffffff), (MESH, 0x82df)])
        log = v.new_log()   # world 129's slot has no world test; 128's does
        self.assertEqual(self.dll.mu_abyss_custom(129, self.obj(0x17), 0, 0, 0.0, rand, None, C.byref(log)), 1)
        self.assertEqual(self.dll.mu_abyss_custom(128, self.obj(0x17), 0, 0, 0.0, rand, None, C.byref(log)), 0)

    def test_after_pass_selects_abyss_types(self):
        import random
        x2d, y2d = v.frustum_polygon(random.Random(3))
        cx, cy = sum(x2d) / 4, sum(y2d) / 4
        objects = []
        for k, (typ, flag) in enumerate([(0x17, 1), (0x26, 1), (0x05, 1), (0x05, 0), (0x29, 0)]):
            o = bytearray(v.OBJ_SIZE)
            o[0], o[0xa] = 1, flag
            struct.pack_into('<i', o, 0x5c, typ)
            struct.pack_into('<3f', o, 0x158, cx * 100, cy * 100, 0.0)
            struct.pack_into('<f', o, 0xc0, -600.0)
            objects.append(o)
        heads = [-1] * 256
        heads[int(cx) // 16 * 16 + int(cy) // 16] = 0
        w, bufs = v.c_world(objects, heads, [1, 2, 3, 4, -1])
        inputs = wa.render_inputs(0x80, 6, 1, x2d, y2d)   # top view: every sector
        log = v.new_log()
        status = self.dll.mu_world_after_pass_ex(C.byref(w), C.byref(inputs), C.byref(wa.AfterInputs(0, 0, 0, 0)),
                                                 None, C.byref(log))
        self.assertEqual(status, 0)
        self.assertEqual([e[1] for e in v.log_events(log) if e[0] == AFTER_DRAW], [0, 1, 2, 4])
        inputs = wa.render_inputs(0x86, 6, 0, x2d, y2d)   # no world test, no class answer: closed
        self.assertNotEqual(self.dll.mu_world_after_pass_ex(C.byref(w), C.byref(inputs),
                                                            C.byref(wa.AfterInputs(0, 0, 0, 0)), None,
                                                            C.byref(v.new_log())), 0)

    def test_frame_time(self):
        f = wa.FrameTime()
        self.lib.frame.mu_frame_time_init(C.byref(f))
        self.assertEqual(struct.pack('<f', f.frame_time), struct.pack('<f', 0.1))
        clock = iter([1000, 1000, 1000, 1040, 1040, 1040, 1040])
        get = wa.TIME_FN(lambda c: next(clock))
        self.lib.frame.mu_frame_time_update(C.byref(f), get, None)   # first frame: base, clock, now
        self.lib.frame.mu_frame_time_update(C.byref(f), get, None)
        self.assertAlmostEqual(f.frame_time, 0.04, places=6)
        self.lib.frame.mu_frame_time_update(C.byref(f), get, None)
        self.assertEqual(struct.pack('<f', f.frame_time).hex(), '18b7d138')   # clock unchanged
        self.lib.frame.mu_frame_time_value.restype = C.c_float
        self.lib.frame.mu_frame_time_reset()
        self.assertEqual(struct.pack('<f', self.lib.frame.mu_frame_time_value()), struct.pack('<f', 0.1))

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-after-orig-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_after.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(sum(r['cases'] for r in result['families'].values()), 13424)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), 21)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))


if __name__ == '__main__':
    unittest.main()
