"""Private comparison of NATIVE-FIDELITY-002's world reconstructions with the client (Unicorn).

scripts/validate_world_fidelity.py runs the client's instructions against the authored C (MU_RECOVERY_INTEGRATION=1
and the pinned restored text and run10 image data). Portable checks: native/tests/test_native_fidelity2.py.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' if (ROOT / 'evidence').exists() else Path.home() / 'Documents/main-exe-study/evidence'
TEXT = Path(os.environ.get('MU_CLIENT_TEXT', EVIDENCE / 'x86-text-capture-09/client-text.bin'))
DATA = Path(os.environ.get('MU_IMAGE_DATA', EVIDENCE / 'image-data-run10/data-capture-10/client-image-data.bin'))


def have_unicorn():
    try:
        import unicorn  # noqa: F401
        return True
    except ImportError:
        return False


class WorldFidelityPrivateTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and TEXT.exists() and DATA.exists() and
                         have_unicorn(), 'private pinned client captures and Unicorn')
    def test_routines_match_client(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_world_fidelity.py'), '--text', str(TEXT),
                            '--data', str(DATA), '--cases', '200', '--mutations', '--mutation-cases', '200',
                            '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        self.assertTrue(report['ok'])
        for name, family in report['families'].items():
            self.assertGreater(family['cases'], 0, name)
            self.assertEqual(family['equal'], family['cases'], name)


if __name__ == '__main__':
    unittest.main()
