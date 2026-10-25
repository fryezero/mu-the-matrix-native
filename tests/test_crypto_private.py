"""Private actual-instruction comparison of the C3/C4 CryptoModule (NET-CRYPTO-001).

Runs scripts/validate_crypto.py only with MU_RECOVERY_INTEGRATION=1 and the pinned restored
text and image-data captures present (the same private inputs as the other Unicorn checks).
Portable synthetic checks live in native/tests/test_crypto.py.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _inputs():
    text = os.environ.get('MU_CLIENT_TEXT', str(ROOT/'evidence/x86-text-capture-09/client-text.bin'))
    data = os.environ.get('MU_IMAGE_DATA', str(ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
    feature = os.environ.get('MU_CPU_FEATURES', str(ROOT/'evidence/image-data-run10/math-capture-10/cpu-features.bin'))
    return text, data, feature


class CryptoPrivateTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'private pinned client captures (set MU_RECOVERY_INTEGRATION=1)')
    def test_module_matches_client_instructions(self):
        text, data, feature = _inputs()
        for path in (text, data, feature):
            if not Path(path).is_file():
                self.skipTest(f'missing private input: {path}')
        subprocess.run(['make', '-C', str(ROOT/'native'), 'build/libmucrypto.' +
                        ('dylib' if sys.platform == 'darwin' else 'so')], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as folder:
            report_path = Path(folder)/'crypto.json'
            proc = subprocess.run([sys.executable, str(ROOT/'scripts/validate_crypto.py'), '--text', text,
                                   '--data', data, '--feature', feature, '--scale', '2', '--mutations',
                                   '--report', str(report_path)], capture_output=True, text=True)
            self.assertTrue(report_path.is_file(), proc.stdout + proc.stderr)
            report = json.loads(report_path.read_text())
        self.assertTrue(report['ok'], json.dumps(report.get('coverage_problems')) + ' ' + proc.stdout[-3000:])
        # Every family matched the client's instructions.
        for name, fam in report['families'].items():
            self.assertEqual(fam['mismatches'], 0, name)
            self.assertGreater(fam['calls'], 0, name)
        self.assertEqual(report['coverage_problems'], [])
        # Every one of the 17 factory cases reached by the encrypt and decrypt families.
        for name in ('encrypt', 'decrypt', 'set_key', 'factory'):
            for case in range(17):
                key = next(k for k in report['families'][name]['coverage'] if k.startswith(f'case {case:02d} '))
                self.assertGreater(report['families'][name]['coverage'][key], 0, f'{name} {key}')
        # At least 8 planted mistakes caught (all 14 required here).
        caught = sum(1 for v in report['mutations'].values() if v['caught'])
        self.assertGreaterEqual(caught, 8, report['mutations_caught'])
        self.assertEqual(caught, len(report['mutations']), report['mutations_caught'])


if __name__ == '__main__':
    unittest.main()
