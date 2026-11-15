"""Bodies split by the helper's level word: packed (>= 9) and guarded, decoded (>= 11)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base
import gen_item_bodies as gen
import validate_item_level_guards as check
import validate_renderchar as v


class ItemLevelGuards(unittest.TestCase):
    def test_decoded_guard_starts_at_level_eleven(self):
        lib = base.lib()
        case = v.classify_case(0x239a, v.CLASSIFY[0])
        case.update(quality=9, record=(0, 0, 0))
        counts = {}
        for packed in (72, 80, 87, 88, 95, 104, 127, -1):
            status, stream = v.c_stream(lib, dict(case, item_level=packed))
            self.assertEqual(status, 0)
            counts[packed] = [draw[0] for draw in stream[:8]]
        self.assertEqual(counts[72][0], 'BODY')
        self.assertEqual(counts[80], counts[72])
        self.assertEqual(counts[87], counts[72])
        self.assertEqual(counts[88], ['MESH'] * 8)
        self.assertEqual(counts[95], counts[88])
        self.assertEqual(counts[104], counts[88])
        self.assertEqual(counts[127], counts[88])
        # The low callers and a packed word of -1 never reach the decode.
        self.assertEqual(counts[-1][0], 'BODY')

    def test_packed_guard_is_the_undecoded_word(self):
        lib = base.lib()
        case = v.classify_case(0x0b34, v.CLASSIFY[0])
        case.update(quality=2, record=(0, 0x26, 0))
        lengths = [len(v.c_stream(lib, dict(case, item_level=packed))[1]) for packed in (8, 9, 15, 16)]
        self.assertEqual(lengths[1:], [lengths[1]] * 3)
        self.assertEqual(lengths[1] - lengths[0], 1)

    def test_lists_and_clock_operations(self):
        lib = base.lib()
        self.assertEqual(len(gen.PACKED_GUARD_TYPES), 7)
        self.assertEqual(len(gen.DECODED_GUARD_TYPES), 11)
        for t in gen.GUARD_TYPES:
            self.assertEqual(lib.mu_rc_item_special(t), 0, hex(t))
        for t in (0x0b38, 0x0b39, 0x239e, 0x23a1, 0x23a5):
            self.assertEqual(lib.mu_rc_item_special(t), 1, hex(t))
        one, three = v.f2u(1.0), v.f2u(0.03)
        chain = ((gen.C_TICK, 0), (gen.C_I_MOD, 540), (gen.C_I_DIV, 15), (gen.C_I2F, 0), (gen.C_F_MUL, three),
                 (gen.C_F_MIN_K, one))
        self.assertEqual(gen.clock_value(chain, 15.0 * 20), v.f2u(base.f32(20 * base.f32(0.03))))
        self.assertEqual(gen.clock_value(chain, 15.0 * 35), one)
        mirror = ((gen.C_TICK, 0), (gen.C_I_MIRROR, 16), (gen.C_I2F, 0))
        self.assertEqual([v.u2f(gen.clock_value(mirror, float(tick))) for tick in (0, 15, 16, 17, 31)],
                         [0.0, 15.0, 15.0, 14.0, 0.0])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'level-guards.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_level_guards.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        n = len(gen.GUARD_TYPES)
        for name, per_type in (('bodies', 292), ('records', 512), ('packed', 1644), ('clocks', 24),
                               ('ticks', 800), ('exits', 64), ('original_guards', 10)):
            self.assertEqual(report['families'][name]['cases'], per_type * n, name)
        self.assertEqual(report['families']['reader_refusals']['cases'], 6)
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(set(report['mutants']), set(check.MUTANTS))
        self.assertTrue(all(report['mutants'].values()))
