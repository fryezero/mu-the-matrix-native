"""Part 11 per-type wave/sine scalar bodies."""
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
import validate_item_scalars as scalars


def program(entry):
    """Header entry text back to the generator's (kind, a, ops) tuple."""
    import re
    kind, count, a = re.match(r'\{(\d), (\d), (0x[0-9a-f]{8})u', entry).groups()
    ops = [int(x) for x in re.search(r', \{([0-9, ]+)\}, ', entry).group(1).split(', ')]
    ks = [int(x[:-3], 16) for x in re.search(r'\{(0x[^{}]*)\}\}$', entry).group(1).split(', ')]
    return int(kind), int(a, 16), tuple(zip(ops[:int(count)], ks[:int(count)]))


class ItemScalars(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = base.lib()
        cls.v = scalars.v
    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def test_admissions_and_existing_domain(self):
        self.assertEqual(len(gen.SCALAR_TYPES), 87)
        for t in gen.SCALAR_TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0], 0, hex(t))
            for args in ({'a10': 0}, {'a11': 0}, {'select': 1}, {'object_shadow': 1}):
                self.assertEqual(self.draws(self.item(type=t, **args))[0], 2, (hex(t), args))

    def test_every_program_reaches_a_draw(self):
        entries, first = scalars.programs()
        self.assertEqual(len(entries), 89)
        for entry, t in first.items():
            p = program(entry)
            for time in (-1570.5, -0.0, 3.0, 1047.0, 123456.75, 1999999.0):
                expected = gen.scalar_value(p, time)
                status, draws = self.draws(self.item(type=t, time=time))
                self.assertEqual(status, 0)
                words = {struct.unpack('<I', struct.pack('<f', x))[0]
                         for d in draws for x in (d.blend_light, d.alpha, d.u, d.v, *d.body_light)}
                self.assertIn(expected, words, (hex(t), entry, time))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'scalars.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_scalars.py'),
                            '--mutations', '--output', str(path)], check=True, capture_output=True)
            report = json.loads(path.read_text())
            self.assertEqual(report['families']['bodies']['cases'], 292*len(gen.SCALAR_TYPES))
            self.assertEqual(report['families']['clocks']['cases'], 750)
            self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
            self.assertEqual(len(report['mutants']), 11)
            self.assertTrue(all(report['mutants'].values()))
