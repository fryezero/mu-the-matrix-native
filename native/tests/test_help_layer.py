"""Synthetic file-to-GFx adapter and native Ctrl+H lifecycle checks."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tests'))
import test_help as th


class HelpLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory(prefix='mu-help-layer-')
        cls.path = Path(cls.work.name)
        cls.lib = cls.path/('libmugfx.dylib' if sys.platform == 'darwin' else 'libmugfx.so')
        cc = os.environ.get('CC', 'cc')
        subprocess.run([cc, '-std=c11', '-O1', '-shared', '-fPIC',
                        str(ROOT/'native/tests/gfx_stub_mugfx.c'), '-o', str(cls.lib)],
                       check=True, capture_output=True)
        sources = ['native/tests/help_layer_host.c', 'native/gfx/mu_gfx_layer.c',
                   'native/world/world_gfx_help.c', 'reconstructed/help/help.c',
                   'reconstructed/help/help_controller.c', 'reconstructed/data/data_tables.c',
                   'reconstructed/data/data_codec.c', 'reconstructed/hud/tooltip_html.c',
                   'reconstructed/hud/inv_grid.c', 'reconstructed/hud/item_slots.c']
        cls.host = cls.path/'host'
        subprocess.run([cc, '-std=c11', '-O1', '-DMU_GFX_NO_GL', '-I', str(ROOT/'reconstructed/hud'),
                        *[str(ROOT/p) for p in sources], '-lm',
                        *([] if sys.platform == 'darwin' else ['-ldl']), '-o', str(cls.host)],
                       check=True, capture_output=True)
        cls.movies = cls.path/'movies'
        cls.movies.mkdir()
        for name in ('main', 'InventoryFrame', 'InfoPopup', 'CharacterInfoFrame', 'chat', 'HelpWindow'):
            (cls.movies/(name + '.swf')).write_bytes(b'synthetic stub fixture')

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def run_host(self, image, expected):
        with tempfile.TemporaryDirectory(dir=self.path) as folder:
            root = Path(folder)
            target = root/'Data/Local/helpdata.bmd'
            target.parent.mkdir(parents=True)
            if image is not None:
                target.write_bytes(image)
            log = root/'calls.log'
            result = subprocess.run([str(self.host), str(self.movies), str(self.lib), str(root), str(expected)],
                                    env={**os.environ, 'MUGFX_STUB_LOG': str(log)}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('ok', result.stdout)
            calls = log.read_text()
            self.assertIn('ClearDataProvider', calls)
            return calls

    def test_valid_rows_and_native_key_focus_close_lifecycle(self):
        calls = self.run_host(th.fixture()[1], 1)
        self.assertIn('SetHotKeyData', calls)
        self.assertIn('SetChatHotKeyData', calls)
        self.assertIn('SetPosCenter', calls)

    def test_missing_truncated_and_corrupted_stay_unavailable(self):
        encoded = th.fixture()[1]
        corrupt = bytearray(encoded)
        corrupt[-1] ^= 1
        for image in (None, encoded[:-1], corrupt):
            with self.subTest(kind='missing' if image is None else len(image)):
                calls = self.run_host(image, 0)
                self.assertNotIn('SetHotKeyData', calls)
                self.assertNotIn('SetChatHotKeyData', calls)


if __name__ == '__main__':
    unittest.main()
