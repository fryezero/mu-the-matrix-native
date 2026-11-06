"""HiddenMesh recipe copies, admission, and inventory/ground defaults."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import test_renderchar as base
import validate_item_hiddenmesh as hidden


class ItemHiddenMesh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib, cls.v = base.lib(), hidden.v
    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def test_attributes_and_domain(self):
        for t in hidden.TYPES + hidden.VISIBILITY_TYPES + hidden.CONTROLS:
            self.assertEqual(self.lib.mu_rc_item_hidden_mesh(t), hidden.EXCEPTIONS.get(t, -1))
            for h in (0, -1):
                self.assertEqual(self.draws(self.item(type=t, object_hidden=h))[0], 0, (hex(t), h))
            self.assertEqual(self.draws(self.item(type=t, object_hidden=3))[0], 2, hex(t))
        for t, h in hidden.EXCEPTIONS.items():
            self.assertEqual(self.lib.mu_rc_item_hidden_mesh(t), h)
        self.assertEqual(self.draws(self.item(type=0x10f0, object_hidden=1))[0], 0)
        for h in (-1, 0, 2):
            self.assertEqual(self.draws(self.item(type=0x2322, object_hidden=h))[0], 0)

    def test_texture_and_body_hidden_copy_independently(self):
        for t in hidden.TYPES:
            found = False
            for level in (0, 7, 13):
                for h in (0, -1):
                    status, draws = self.draws(self.item(type=t, item_level=level << 3, object_hidden=h))
                    self.assertEqual(status, 0)
                    meshes = [d for d in draws if d.entry == 2 and d.texture == h]
                    found |= bool(meshes)
                    if t in (0x0eee, 0x2537):
                        self.assertTrue(any(d.entry == 1 and d.hidden == h for d in draws))
            self.assertTrue(found, hex(t))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'pinned original required')
    def test_private_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_hiddenmesh.py'),
                            '--output', str(report)], check=True, capture_output=True)
            data = json.loads(report.read_text())
            self.assertEqual(data['families']['affected']['cases'], 23 * 292 * 2)
            self.assertTrue(all(f['mismatches'] == 0 for f in data['families'].values()))


if __name__ == '__main__':
    unittest.main()
