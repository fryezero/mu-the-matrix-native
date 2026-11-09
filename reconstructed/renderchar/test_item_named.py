"""Rank-5 part texture-name inputs, without changing the original classification fixture."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base
import gen_item_owner_fx as fxgen
import validate_item_named as named
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[2]


class ItemNamed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = base.lib()

    def test_named_mesh_indices_and_missing_results(self):
        for t in v.NAMED_ARMOUR_TYPES:
            case = dict(v.classify_case(t, v.CLASSIFY[0]), named_meshes=(4, 5, 3))
            status, stream = v.c_stream(self.lib, case)
            self.assertEqual(status, 0, hex(t))
            blue = [draw for draw in stream if draw[0] == 'MESH' and draw[1][7] == 0x84d9]
            self.assertEqual(len(blue), 1, hex(t))
            self.assertEqual((blue[0][1][0], blue[0][1][3]), (4, 4), hex(t))
            missing = dict(case, named_meshes=(-1, -1, -1))
            missing_status, missing_stream = v.c_stream(self.lib, missing)
            self.assertEqual(missing_status, 0, hex(t))
            missing_blue = [draw for draw in missing_stream if draw[0] == 'MESH' and draw[1][7] == 0x84d9]
            self.assertEqual((missing_blue[0][1][0], missing_blue[0][1][3]), (0xffffffff, 0xffffffff))
            self.assertEqual(len(missing_stream), len(stream), 'the original emits the -1 mesh call')
            without_context = dict(case)
            without_context.pop('named_meshes')
            self.assertEqual(v.c_stream(self.lib, without_context), (0, missing_stream))

    def test_blue_black_and_skirt_are_independent(self):
        for t, other, slot in ((0x1a26, -1, 1), (0x1e26, 0x84dd, 2)):
            case = dict(v.classify_case(t, v.CLASSIFY[0]), named_meshes=(4, 5, 3))
            _, stream = v.c_stream(self.lib, case)
            target = [draw for draw in stream if draw[0] == 'MESH' and draw[1][7] == (other & 0xffffffff)]
            self.assertEqual(target[0][1][0], case['named_meshes'][slot])
            changed = list(case['named_meshes'])
            changed[slot] = 0
            _, moved = v.c_stream(self.lib, dict(case, named_meshes=tuple(changed)))
            self.assertNotEqual(stream, moved)

    def test_weapon_names_and_counter_input(self):
        for t, first in ((0x0b5c, 3), (0x0b62, 11), (0x0b68, 17)):
            values = [-1] * len(v.NAMED_MESH_NAMES)
            values[first] = 4
            case = dict(v.classify_case(t, v.CLASSIFY[0]), named_meshes=tuple(values))
            status, stream = v.c_stream(self.lib, case)
            self.assertEqual(status, 0)
            values[first] = 1
            _, moved = v.c_stream(self.lib, dict(case, named_meshes=tuple(values)))
            self.assertNotEqual(stream, moved)
        values = (1,) * len(v.NAMED_MESH_NAMES)
        case = dict(v.classify_case(0x0b68, v.CLASSIFY[0]), named_meshes=values)
        self.assertNotEqual(v.c_stream(self.lib, dict(case, frame=0)),
                            v.c_stream(self.lib, dict(case, frame=7)))

    def test_zero_frequency_wave_operand_case(self):
        def interpreter(a, b):
            it = fxgen.Interpreter.__new__(fxgen.Interpreter)
            it.pre, it.p, it.reg = True, fxgen.Program(), {}
            it.stack = [('c', b), ('c', a)]
            return it
        it = interpreter(0, 0xc0800000)
        it.call(fxgen.WAVE)
        self.assertEqual(it.st0, ('c', 0))
        self.assertEqual(it.p.ops, [])
        self.assertEqual(len(it.stack), 2, 'wave is cdecl')
        for a, b in ((0, 0), (0, 0x40800000), (0x80000000, 0xc0800000)):
            with self.assertRaises(fxgen.Refused):
                interpreter(a, b).call(fxgen.WAVE)
        normal = interpreter(0xc0800000, 0)
        normal.call(fxgen.WAVE)
        self.assertEqual(normal.p.ops[0][0], fxgen.OP['wave'])

    def test_clock_reader_continues_after_signed_modulo_one(self):
        import struct
        import gen_item_bodies as g
        # Authored x86: tick % 415 / 83, save cell; U = cell % 1; V = cell * .2.
        text = (b'\xf3\x0f\x2c\x05' + struct.pack('<I', g.CLOCK) +
                bytes.fromhex('99 b9 9f010000 f7f9 89d0 99 b9 53000000 f7f9 8945f8 '
                              '2500000080 7905 48 83c8ff 40 f30f2ac0 f30f1145fc '
                              'f30f2a45f8 f30f5905') + struct.pack('<I', 0x01a7c000) +
                bytes.fromhex('f30f1145f4 c3'))
        wa = (text, struct.pack('<f', .2), b'', b'')
        g._slices.clear()
        try:
            entry, outputs = g.slice_block(wa, 0x00401000)
            self.assertEqual(entry, ())
            self.assertEqual(len(outputs), 2, 'the V store follows the signed modulo-one idiom')
            programs = [g.resolve_clock(wa, output[2], {}) for output in outputs]
            self.assertTrue(all(programs))
            for clock in (-830.0, -416.0, -1.0, 0.0, 82.0, 83.0, 414.0, 415.0, 123456.0):
                remainder = int(clock) - int(int(clock) / 415) * 415
                cell = int(remainder / 83)
                self.assertEqual(g.clock_value(programs[0], clock), 0)
                self.assertEqual(g.clock_value(programs[1], clock),
                                 v.f2u(v.u2f(v.f2u(float(cell))) * v.u2f(v.f2u(.2))))
        finally:
            g._slices.clear()

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'pinned client inputs are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'named.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_item_named.py'),
                            '--output', str(output)], check=True, cwd=ROOT)
            report = json.loads(output.read_text())
            self.assertEqual(sum(row['cases'] for row in report['families'].values()), 20057)
            self.assertTrue(all(row['mismatches'] == 0 for row in report['families'].values()))


if __name__ == '__main__':
    unittest.main()
