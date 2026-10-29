"""Part 12 clock-chain and level-split bodies and two link table additions."""
import ctypes as C
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import test_renderchar as base
import gen_item_bodies as gen
import validate_item_chains as chains


class ItemChains(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = base.lib()
    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def test_admissions_and_existing_domain(self):
        self.assertEqual(len(gen.CHAIN_TYPES), 66)
        self.assertEqual(len(gen.LEVEL_TYPES), 20)
        for t in chains.TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0], 0, hex(t))
            for args in ({'a10': 0}, {'a11': 0}, {'select': 1}, {'object_shadow': 1}):
                self.assertEqual(self.draws(self.item(type=t, **args))[0], 2, (hex(t), args))
        for t in chains.LINKS:
            self.assertEqual(self.lib.mu_rc_link_supported(t), 1, hex(t))

    def test_every_chain_reaches_a_draw(self):
        first = chains.programs()
        self.assertEqual(len(first), 59)
        for ops, t in first.items():
            for time in (-2147483648.0, -1200.5, -0.0, 3.0, 1999.0, 123456.75, 1999999.0, 2147483648.0):
                expected = gen.clock_value(ops, time)
                status, draws = self.draws(self.item(type=t, time=time))
                self.assertEqual(status, 0)
                words = {struct.unpack('<I', struct.pack('<f', x))[0]
                         for d in draws for x in (d.blend_light, d.alpha, d.u, d.v, *d.body_light)}
                self.assertIn(expected, words, (hex(t), ops, time))

    def test_signed_idioms(self):
        """Truncating remainder/quotient, indefinite tick and wrapping integer steps."""
        tick = ((gen.C_TICK, 0),)
        cases = [
            (tick + ((gen.C_I_MOD, 8), (gen.C_I2F, 0)), -13.5, -5.0),
            (tick + ((gen.C_I_DIV, 4), (gen.C_I2F, 0)), -13.5, -3.0),
            (tick + ((gen.C_I2F, 0),), 2147483648.0, -2147483648.0),
            (tick + ((gen.C_I_RSUB, 1000), (gen.C_I2F, 0)), 1500.0, -500.0),
            (tick + ((gen.C_I_NEG, 0), (gen.C_I2F, 0)), -2147483648.0, -2147483648.0),
            (((gen.C_TIME_D, 0), (gen.C_D_MUL, struct.unpack('<Q', struct.pack('<d', 0.5))[0]),
              (gen.C_D2I, 0), (gen.C_I2F, 0)), -3.0, -1.0),
        ]
        for ops, time, value in cases:
            self.assertEqual(gen.clock_value(ops, time), struct.unpack('<I', struct.pack('<f', value))[0], ops)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'chains.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_chains.py'),
                            '--mutations', '--output', str(path)], check=True, capture_output=True)
            report = json.loads(path.read_text())
            self.assertEqual(report['families']['bodies']['cases'], 292*len(chains.TYPES))
            self.assertEqual(report['families']['clocks']['cases'], 2714)
            self.assertEqual(report['families']['levels']['cases'], 6720)
            self.assertEqual(report['families']['links']['cases'], 800)
            self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
            self.assertEqual(len(report['mutants']), 17)
            self.assertTrue(all(report['mutants'].values()))
