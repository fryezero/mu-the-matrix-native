"""Private comparisons of the world-object routines (NATIVE-OBJECTS-002).

1. scripts/validate_object_render.py runs the client routines in Unicorn against
   reconstructed/objects/object_render.c (MU_RECOVERY_INTEGRATION=1 and the pinned restored text and
   run10 image data).
2. scripts/live_object_state.py compares reconstructed CreateObject with object snapshots read from a
   running client (MU_OBJECTS_DUMP_DIR holding objread snapshots: fryezen2.bin for Lorencia,
   nighty.bin for Tormenta Island; decoded game data, local only).
Portable checks: reconstructed/objects/test_object_render.py.
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
DUMPS = Path(os.environ.get('MU_OBJECTS_DUMP_DIR', '/nonexistent'))


def have_unicorn():
    try:
        import unicorn  # noqa: F401
        return True
    except ImportError:
        return False


class ObjectRenderPrivateTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and TEXT.exists() and DATA.exists() and
                         have_unicorn(), 'private pinned client captures and Unicorn')
    def test_routines_match_client(self):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_object_render.py'), '--text', str(TEXT),
                            '--data', str(DATA), '--cases', '200', '--output', str(output)], check=True,
                           capture_output=True)
            report = json.loads(output.read_text())
        self.assertTrue(report['ok'])
        for name, family in report['families'].items():
            self.assertGreater(family['cases'], 0, name)
            self.assertEqual(family['equal'], family['cases'], name)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and (DUMPS / 'fryezen2.bin').exists() and
                         (DUMPS / 'nighty.bin').exists(), 'local live object snapshots')
    def test_creation_matches_live_objects(self):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'live.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/live_object_state.py'), str(DUMPS / 'fryezen2.bin'),
                            str(DUMPS / 'nighty.bin'), '--output', str(output)], check=True, capture_output=True)
            reports = json.loads(output.read_text())
        for r in reports:
            self.assertEqual(r['stats']['objects equal'], r['objects'], r['snapshot'])
            self.assertFalse(r['mismatched_fields'])
        self.assertEqual(reports[0]['velocity_types_differing'], 0)


if __name__ == '__main__':
    unittest.main()
