"""Matrix-bracket bodies, scalar forms and flag programs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base
import gen_item_bodies as gen
import validate_item_brackets as check
import validate_renderchar as v


class ItemBrackets(unittest.TestCase):
    def test_lists(self):
        lib = base.lib()
        self.assertEqual((len(gen.MATRIX_TYPES), len(gen.TAIL_TYPES), len(gen.FLAG_TYPES)), (9, 16, 3))
        for t in check.TYPES:
            self.assertEqual(lib.mu_rc_item_special(t), 0, hex(t))
        for t in (0x0afc, 0x0ef0, 0x24ed, 0x26ed, 0x1710, 0x10fd):
            self.assertEqual(lib.mu_rc_item_special(t), 1, hex(t))

    def test_scalar_operations(self):
        f = base.f32
        half, one, tenth = v.f2u(0.5), v.f2u(1.0), v.f2u(0.1)
        # Upper clamp keeps a value at or below k; the ternary minimum has the helper's comparison order.
        self.assertEqual(gen.scalar_value((2, v.f2u(0.0), ((2, one), (7, half))), 0.0), half)
        self.assertEqual(gen.scalar_value((2, v.f2u(0.0), ((2, tenth), (7, half))), 0.0), tenth)
        self.assertEqual(gen.scalar_value((2, v.f2u(0.0), ((2, one), (17, half))), 0.0), half)
        self.assertEqual(gen.scalar_value((2, v.f2u(0.0), ((2, tenth), (17, half))), 0.0), tenth)
        # Binary32 operation, binary64 run with one rounding, then a binary32 clamp.
        import struct
        wide = struct.unpack('<Q', struct.pack('<d', 0.15))[0]
        expected = f(float(f(f(0.25) * f(0.85))) + 0.15)
        program = (2, v.f2u(0.0), ((2, v.f2u(0.25)), (1, v.f2u(0.85)), (2 | 8, wide)))
        self.assertEqual(gen.scalar_value(program, 0.0), v.f2u(expected))
        self.assertEqual(gen.scalar_value(program[:2] + (program[2] + ((7, tenth),),), 0.0), tenth)

    def test_flag_programs_follow_the_helper_argument(self):
        lib = base.lib()
        flags = {}
        for render_type in (2, 0x102):
            case = v.classify_case(0x24e3, v.CLASSIFY[0])
            case.update(render_type=render_type)
            status, stream = v.c_stream(lib, case)
            self.assertEqual(status, 0)
            flags[render_type] = [draw[1][1] for draw in stream if draw[0] == 'MESH']
        self.assertEqual(flags[2][2:5], [0x240, 0x48, 0x44])
        self.assertEqual(flags[0x102][2:5], [0x340, 0x148, 0x144])
        case = v.classify_case(0x231b, v.CLASSIFY[0])
        for render_type, expected in ((2, 0x42), (0x102, 0x142)):
            status, stream = v.c_stream(lib, dict(case, render_type=render_type))
            self.assertEqual((status, stream[1][0], stream[1][1][0]), (0, 'BODY', expected))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'brackets.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_brackets.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        n = len(check.TYPES)
        for name, per_type in (('bodies', 292), ('records', 512), ('clocks', 24), ('ticks', 600), ('exits', 64)):
            self.assertEqual(report['families'][name]['cases'], per_type * n, name)
        self.assertGreater(report['families']['brackets']['cases'], 0)
        self.assertEqual(report['families']['reader_refusals']['cases'], 5)
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(set(report['mutants']), set(check.MUTANTS))
        self.assertTrue(all(report['mutants'].values()))
