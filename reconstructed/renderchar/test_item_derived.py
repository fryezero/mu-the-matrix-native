"""Part 16 bodies: draw words one binary32 operation away from another input (kind-6 derived programs)."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_renderchar as base
import gen_item_bodies as gen
import validate_item_derived as derived
import validate_item_quality as quality

F32 = lambda x: ctypes.c_float(x).value


class ItemDerived(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = base.lib()
        cls.v = quality.v
    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def generic(self, it):
        model, out, count = quality.v.CModel(), (quality.v.CDraw * 32)(), ctypes.c_int32()
        status = self.lib.mu_rc_item_draws_generic(ctypes.byref(it), ctypes.byref(model), out, 32, ctypes.byref(count))
        return status, list(out[:count.value])

    def test_admissions_and_existing_domain(self):
        self.assertEqual(len(gen.DERIVED_TYPES), 57)
        self.assertTrue(set(gen.DERIVED_CARRY) <= set(gen.DERIVED_TYPES))
        earlier = set(gen.ALL_TYPES) - set(gen.DERIVED_TYPES)
        self.assertFalse(set(gen.DERIVED_TYPES) & earlier)
        self.assertFalse(set(gen.DERIVED_CARRY) & set(gen.CARRY_TYPES))
        for t in gen.DERIVED_TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0], 0, hex(t))
            for args in ({'a10': 0}, {'a11': 0}, {'select': 1}, {'object_shadow': 1}):
                self.assertEqual(self.draws(self.item(type=t, **args))[0], 2, (hex(t), args))

    def test_programs_read_earlier_inputs(self):
        """Every type has a kind-6 program, and each reads a float input or an earlier program."""
        for t in gen.DERIVED_TYPES:
            programs = quality.table_programs(t)
            self.assertTrue(derived.derived_programs(t), hex(t))
            for index, (kind, a) in enumerate(programs):
                if kind == 6:
                    self.assertTrue(a in gen.DERIVED_SOURCES or 35 <= a < 35 + index, (hex(t), index, a))

    def test_light_from_generic_light(self):
        """0x1afa scales the generic body light of its body draw by the constants of its own code
        (0.85, 0.85, 1.2; binary32 mulss)."""
        it = self.item(type=0x1afa, quality=9)
        status, draws = self.draws(it)
        self.assertEqual(status, 0)
        status, generic = self.generic(self.item(type=0x1afa, quality=9))
        self.assertEqual(status, 0)
        light = [F32(F32(x) * F32(k)) for x, k in zip(generic[0].body_light, (0.85, 0.85, 1.2))]
        self.assertIn(light, [[F32(x) for x in d.body_light] for d in draws])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'derived.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_derived.py'),
                            '--mutations', '--output', str(path)], check=True, capture_output=True)
            report = json.loads(path.read_text())
            self.assertEqual(report['families']['bodies']['cases'], 292*len(derived.TYPES))
            self.assertEqual(report['families']['derived']['cases'], 88*len(derived.TYPES))
            self.assertEqual(report['families']['records']['cases'], 256*len(derived.TYPES))
            self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
            self.assertEqual(len(report['mutants']), len(derived.MUTANTS))
            self.assertTrue(all(report['mutants'].values()))


if __name__ == '__main__':
    unittest.main()
