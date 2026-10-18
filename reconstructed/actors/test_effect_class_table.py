"""Checks for the extracted effect-attaching classes (NATIVE-WORLD-002).

Portable: the generated table effect_class_table.h is well formed (attachment
ranges, client effect paths, bones and NPC models of the six classes).
Private (MU_RECOVERY_INTEGRATION=1): scripts/extract_effect_classes.py,
run over the restored client, regenerates the same header.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TABLE = HERE/'effect_class_table.h'


def parse():
    text = TABLE.read_text()
    attaches = re.findall(r'\{"([^"]+)", \{([^}]*)\}, \{([^}]*)\}, ([^,]+), (\d+), (\d+), ([^,]+), (-?\d+), (\d+), '
                          r'(\d+), ([^}]+)\}', text)
    classes = re.findall(r'\{(\d+), (0x[0-9a-f]+), (-?(?:0x)?[0-9a-f]+), ([^,]+), (\d+), (\d+)\}', text)
    return attaches, classes


class EffectClassTableTests(unittest.TestCase):
    def test_rows_and_ranges(self):
        attaches, classes = parse()
        self.assertEqual(len(classes), 6)
        self.assertEqual(len(attaches), 11)
        expected = {750: 0xa89, 751: 0xa89, 752: 0xa89, 753: 0xa89, 758: 0xa88, 873: 0xa52}
        cursor = 0
        for server_class, model, npc, scale, first, count in classes:
            self.assertEqual(int(model, 16), expected[int(server_class)])
            self.assertEqual(int(npc, 0), int(model, 16))          # the case opens its own NPC model
            self.assertEqual(int(first), cursor)
            cursor += int(count)
        self.assertEqual(cursor, len(attaches))

    def test_attachments(self):
        attaches, _ = parse()
        for path, position, rotation, scale, template, tint, start, bone, follow, timed, lifetime in attaches:
            self.assertTrue(path.startswith('Data\\\\Effect\\\\') and path.endswith('.ein'), path)
            self.assertEqual((template, tint, bone, follow, timed), ('0', '0', '1', '1', '0'))
            self.assertGreater(float(scale.rstrip('f')), 0)
        leaf = [a for a in attaches if 'leaf_particle' in a[0]]
        self.assertEqual(len(leaf), 1)
        self.assertEqual(leaf[0][1], '0.0f, 0.0f, 70.0f')
        self.assertEqual(leaf[0][3], '9.0f')

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'extraction from the restored client is opt-in')
    def test_extraction_regenerates_the_table(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        if not text.exists() or not data.exists():
            self.skipTest('restored text or image data not present')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'table.h'
            result = subprocess.run([sys.executable, str(ROOT/'scripts/extract_effect_classes.py'), '--text',
                                     str(text), '--data', str(data), '--emit-c', str(out)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(out.read_text(), TABLE.read_text())


if __name__ == '__main__':
    unittest.main()
