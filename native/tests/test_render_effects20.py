"""RENDER-EFFECTS-020: portable native routes of the item-owned particles; pinned instruction comparisons run
separately (scripts/validate_render_effects20.py)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]


def build_host(tmp):
    """effects20_host.c against the native libraries."""
    native = ROOT/'native'
    subprocess.run(['make', '-s', '-C', str(native), 'build/libmunative.a', 'build/libmusession_world.a'],
                   check=True, capture_output=True)
    host, obj = Path(tmp)/'host', Path(tmp)/'host.o'
    command = ['clang', '-std=c11', '-O2', '-ffp-contract=off', '-I', str(native/'build/gen'), '-I', str(native/'session'),
               '-iquote', str(native/'core'), '-c', str(native/'tests/effects20_host.c'), '-o', str(obj)]
    p = subprocess.run(command, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr)
    command = ['clang++', str(obj), str(native/'build/libmunative.a'), str(native/'build/libmusession_world.a'), '-lm',
               '-o', str(host)]
    if sys.platform == 'darwin':
        command += ['-L/opt/homebrew/opt/cryptopp/lib', '-lcryptopp', '-L/opt/homebrew/opt/jpeg-turbo/lib', '-ljpeg',
                    '-framework', 'CoreText', '-framework', 'CoreGraphics', '-framework', 'CoreFoundation']
    else:
        command += ['-lcryptopp', '-ljpeg']
    p = subprocess.run(command, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr)
    return host


class Native(unittest.TestCase):
    def test_item_owned_particles_and_owner_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = build_host(tmp)
            p = subprocess.run([str(host)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('item-owned particle kinds 0x810a/0x11, 0x81cf/0 and the item OBJECT owner slots through native '
                      'routes: OK', p.stdout)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions_and_compiled_mutants(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects20.py'),
                            '--cases', '20', '--mutations', '--output', str(out)], check=True, capture_output=True)
            report = json.loads(out.read_text())
        self.assertTrue(report['all_equal'])
        self.assertTrue(report['all_mutants_caught'])
        self.assertEqual(report['instruction_cases'], CASES)
        self.assertEqual(len(report['mutants']), MUTANTS)


CASES, MUTANTS = 148, 14   # the registry row (scripts/validators.toml)


if __name__ == '__main__':
    unittest.main()
