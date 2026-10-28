"""Recorded world consumers through native dispatch, asset and fixed-pool paths."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from test_native_particles import ozj_jpeg


class WorldsL(unittest.TestCase):
    def test_consumers_registrations_producers_and_boundaries(self):
        subprocess.run(['make', '-s', '-C', str(ROOT/'native'), 'build/worlds-l-host'],
                       check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            effect = root/'Data/Effect'
            effect.mkdir(parents=True)
            for name in ('Shiny04', 'firehik_mono01', 'firehik_mono02', 'firehik_mono03',
                         'WATERFALL2', 'WATERFALL3', 'WATERFALL5'):
                (effect/(name+'.OZJ')).write_bytes(ozj_jpeg(32, 32))
            chunks = [b'BMD\x0a', b'worlds-l'.ljust(32, b'\0'), struct.pack('<HHH', 0, 15, 1),
                      struct.pack('<hB', 2, 0)]
            for bone in range(15):
                chunks += [b'\0'+f'bone{bone}'.encode().ljust(32, b'\0')+struct.pack('<h', -1),
                           struct.pack('<6f', bone*10, 2, 3, bone*10+4, 2, 3), bytes(24)]
            model = root/'lamps.bmd'
            model.write_bytes(b''.join(chunks))
            p = subprocess.run([str(ROOT/'native/build/worlds-l-host'), tmp, str(model)],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn('absent assets: OK', p.stdout)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
    def test_original_instructions(self):
        subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/particles')], check=True)
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_worlds_l.py'), '--cases', '60',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            r = json.loads(report.read_text())
            self.assertTrue(r['all_equal'])
            self.assertEqual(len(r['mutants']), 13)
            self.assertTrue(r['all_mutants_caught'])
