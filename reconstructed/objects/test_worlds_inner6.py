"""RENDER-WORLDS-PICK-001 step 3: chain hook 11's producer (world_inner6_visual.c): world and model guards, every
named type's requests, the clock window, log overflow; and the private instruction comparison
(validate_worlds_inner6)."""
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
import validate_worlds_inner6 as inner  # noqa: E402
import validate_object_render as v  # noqa: E402
PARTICLE, SPRITE, EFFECT = 0x168fafd, 0x1692eb7, 0xe68c23
CASES = 1000


class Chain11(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = inner.build(ROOT / 'reconstructed')

    def call(self, world, typ, rolls=(), clock=0, model=1, capacity=64):
        o = C.create_string_buffer(v.OBJ_SIZE)
        struct.pack_into('<i', o, 0x5c, typ)
        struct.pack_into('<3f', o, 0x158, 1000.0, 2000.0, 300.0)
        struct.pack_into('<f', o, 0xa0, 2.0)
        log = v.new_log(capacity)
        left = list(rolls)
        rnd = v.RAND_FN(lambda c: left.pop(0))
        answer = self.lib.dll.mu_chain11_inner(o, 0, world, model, clock, rnd, None, C.byref(log))
        return answer, o, [(e[0], e[2], *e[3:]) for e in v.log_events(log)], left, log

    def test_world_and_model_guards(self):
        for world in range(-1, 161):
            answer, _, events, _, _ = self.call(world, 0x4a, rolls=[0])
            taken = world in (45, 46, 47, 48, 49, 50, 98, 99)
            self.assertEqual((answer, len(events), self.lib.dll.mu_chain11_world(world)), (int(taken), int(taken),
                                                                                           int(taken)), world)
        self.assertEqual(self.call(46, 0x4a, model=0)[0], 0)   # no model: before the world test, no roll

    def test_unnamed_types_answer_zero(self):
        for typ in (0, 0x35, 0x37, 0x45, 0x50, 300):
            answer, o, events, _, _ = self.call(98, typ)
            self.assertEqual((answer, events), (0, []))

    def test_request_ids(self):
        ids = lambda events: [(e[0], e[1]) for e in events]   # noqa: E731
        sub = lambda events: [e[11] for e in events if e[0] == PARTICLE]   # noqa: E731
        _, o, events, _, _ = self.call(46, 0x36)
        self.assertEqual((ids(events), sub(events)), ([(PARTICLE, 0x8022)] * 2, [0, 3]))
        self.assertEqual(struct.unpack_from('<3f', o, 0xec), (v.f32(0.15),) * 3)
        self.assertEqual(v.from_bits(events[0][4]), 200.0)   # 100 below the position
        for typ, count in ((0x46, 1), (0x47, 1), (0x48, 2), (0x49, 1)):
            _, _, events, left, _ = self.call(46, typ, rolls=[3, 7])
            self.assertEqual((ids(events), sub(events), left), ([(PARTICLE, 0x7f89)] * count, [15] * count, []))
            self.assertEqual(self.call(46, typ, rolls=[4])[2], [])   # rand % 3 != 0
        self.assertEqual(sub(self.call(46, 0x4a, rolls=[2])[2]), [16])
        self.assertEqual(ids(self.call(46, 0x4b, rolls=[5, 0])[2]), [(PARTICLE, 0x7dea)])
        self.assertEqual(self.call(46, 0x4b, rolls=[0])[2], [])   # rand % 35 == 5 only
        for typ in (0x4c, 0x4d):
            _, _, events, _, _ = self.call(46, typ, rolls=[50])
            self.assertEqual(ids(events), [(PARTICLE, 0x7dec), (SPRITE, 0x7ef7)])
            self.assertEqual((v.from_bits(events[1][4]), v.from_bits(events[1][5])), (320.0, 12.0))   # +20, 6 x scale
        _, _, events, left, _ = self.call(46, 0x4f, rolls=[9] + [1] * 5)
        self.assertEqual((ids(events), sub(events), left), ([(PARTICLE, 0x7f89)] * 5, [17] * 5, []))

    def test_clock_window(self):
        # start = 100; the window is [100 + rand % 5, 100 + rand % 10 + 5)
        inside = self.call(99, 0x4e, rolls=[100, 2, 3, 40, 40, 1], clock=1000 + 105)[2]
        self.assertEqual([e[1] for e in inside], [0x4cc] * 5 + [0x801d, 0x7f5a])
        self.assertEqual([e[11] for e in inside[:5]], [0, 0, 0, 0, 1])
        self.assertEqual(self.call(99, 0x4e, rolls=[100, 2], clock=1000 + 101)[2], [])        # before it
        self.assertEqual(self.call(99, 0x4e, rolls=[100, 2, 3], clock=1000 + 108)[2], [])     # at its end
        self.assertEqual(len(self.call(99, 0x4e, rolls=[100, 2, 3, 0, 0, 0], clock=1000 + 102)[2]), 7)   # at its start

    def test_log_overflow_keeps_the_light_write(self):
        answer, o, events, _, log = self.call(46, 0x36, capacity=1)
        self.assertEqual((answer, len(events), log.overflow), (1, 1, 1))
        self.assertEqual(struct.unpack_from('<f', o, 0xec)[0], v.f32(0.15))


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private original text/data required')
class ClientComparison(unittest.TestCase):
    def test_original(self):
        with tempfile.TemporaryDirectory(prefix='worlds-inner6-orig-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_inner6.py'), '--cases', str(CASES),
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(result['accepted_worlds'], [45, 46, 47, 48, 49, 50, 98, 99])
            self.assertTrue(all(r['cases'] == CASES and r['equal'] == CASES and r['stopped'] == 0
                                for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), len(inner.MUTATIONS))
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))


if __name__ == '__main__':
    unittest.main()
