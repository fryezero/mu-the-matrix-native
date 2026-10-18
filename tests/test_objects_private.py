"""Private actual-instruction comparison of the static-object loader and model table.

Runs scripts/validate_objects.py only with MU_RECOVERY_INTEGRATION=1 and
MU_GAME_ROOT pointing at the matching installation (read-only) and the pinned
captures present (restored text, run10 image data, x86-linux-capture-04 third
section). Portable synthetic checks live in reconstructed/objects/test_objects.py.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEXT = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
DATA = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
SECTION3 = Path(os.environ.get('MU_SECTION3', ROOT/'evidence/x86-linux-capture-04/main-01ced000.bin'))


class ObjectsPrivateTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT') and
                         TEXT.exists() and DATA.exists() and SECTION3.exists(),
                         'private pinned client captures and installation')
    def test_loader_and_model_table_match_client(self):
        subprocess.run(['make', '-C', str(ROOT/'reconstructed/objects')], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_objects.py'), '--text', str(TEXT),
                            '--data', str(DATA), '--section3', str(SECTION3), '--game-root',
                            os.environ['MU_GAME_ROOT'], '--synthetic', '200', '--worlds', '0-149',
                            '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        synthetic = report['loader_synthetic']
        self.assertEqual(synthetic['failure_count'], 0)
        self.assertTrue(all(synthetic['negative_controls'].values()))
        installed = report['loader_installed']
        self.assertGreaterEqual(installed['files'], 80)
        self.assertEqual(installed['matching_authored'], installed['files'])
        # The finding: the client's own instructions refuse every installed file.
        self.assertEqual(installed['openworld_would_accept'], 0)
        self.assertEqual(report['model_table']['failure_count'], 0)
        self.assertEqual(report['model_table']['totals']['types_compared'], 150*300)


if __name__ == '__main__':
    unittest.main()
