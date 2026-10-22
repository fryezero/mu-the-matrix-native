"""Private comparison of the character-select world's object handler (NATIVE-CHARSEL-002,
docs/research/client-character-select.md section 9).

scripts/validate_charsel_world.py runs CGMCharacterScene_Ex's slots, MoveObject/CreateObject for world 0x5d and
RenderObjects_AfterCharacter in Unicorn against reconstructed/objects/charsel_world.c (MU_RECOVERY_INTEGRATION=1,
the pinned restored text and run10 image data, Unicorn).
With MU_CHARSEL_DUMP_DIR (charsel-a.bin and charsel-d.bin from live-readers/objread at the character-select
screen; decoded game data, local only): creation equals mu_obj_create for every object apart from the values the
handler drives, and those advance as reconstructed (the scroll by 0.02 / 0.03 per logic step for the objects
MoveObjects moved, +0xa for the custom render's types).
Portable checks: reconstructed/objects/test_charsel_world.py.
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
DUMPS = Path(os.environ.get('MU_CHARSEL_DUMP_DIR', '/nonexistent'))


def have_unicorn():
    try:
        import unicorn  # noqa: F401
        return True
    except ImportError:
        return False


class CharselWorldPrivateTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and TEXT.exists() and DATA.exists() and
                         have_unicorn(), 'private pinned client captures and Unicorn')
    def test_routines_match_client(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_charsel_world.py'), '--text', str(TEXT),
                            '--data', str(DATA), '--cases', '200', '--output', str(output)], check=True,
                           capture_output=True)
            report = json.loads(output.read_text())
        self.assertTrue(report['ok'])
        for name, family in report['families'].items():
            self.assertGreater(family['cases'], 0, name)


    @unittest.skipUnless((DUMPS / 'charsel-a.bin').exists() and (DUMPS / 'charsel-d.bin').exists(),
                         'local live character-select snapshots (MU_CHARSEL_DUMP_DIR)')
    def test_live_snapshots(self):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        a, d = DUMPS / 'charsel-a.bin', DUMPS / 'charsel-d.bin'
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'state.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/live_object_state.py'), str(a), str(d), '--pair',
                            str(a), str(d), '--output', str(output)], check=True, capture_output=True)
            reports = json.loads(output.read_text())
        for r in reports[:2]:
            self.assertEqual(r['world'], 0x5d)
            self.assertEqual(r['stats']['objects equal'], r['objects'])
            self.assertEqual(r['mismatched_fields'], {})
        pair = reports[2]
        steps = {k.split(' steps ')[1] for k in pair['charsel_scroll_steps'] if 'visible 11' in k}
        self.assertEqual(len(steps), 1)          # every moved waterfall advanced by the same number of steps
        self.assertTrue(all(' steps 0.0' in k for k in pair['charsel_scroll_steps'] if 'visible 00' in k))
        self.assertTrue(all(' +0xa 1 ' in k for k in pair['after_character_flags']))


if __name__ == '__main__':
    unittest.main()
