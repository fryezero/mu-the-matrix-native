"""Presentation controllers cannot reach requests, item state or legacy UI audio."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PresentationWindows(unittest.TestCase):
    def test_production_firewall_navigation_focus_and_sound_owner(self):
        with tempfile.TemporaryDirectory(prefix='mu-ui-windows-') as folder:
            tmp = Path(folder)
            cc = os.environ.get('CC', 'cc')
            lib = tmp / ('libmugfx.dylib' if sys.platform == 'darwin' else 'libmugfx.so')
            subprocess.run([cc, '-std=c11', '-O1', '-shared', '-fPIC',
                            str(ROOT/'native/tests/gfx_stub_mugfx.c'), '-o', str(lib)], check=True, capture_output=True)
            sources = ['native/tests/ui_windows_host.c', 'reconstructed/hud/tooltip_html.c',
                       'reconstructed/hud/inv_grid.c', 'reconstructed/hud/item_slots.c']
            host = tmp/'host'
            build = subprocess.run([cc, '-std=c11', '-O1', '-I', str(ROOT/'reconstructed/hud'),
                                    *[str(ROOT/p) for p in sources], '-lm',
                                    *([] if sys.platform == 'darwin' else ['-ldl']), '-o', str(host)],
                                   capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            movies = tmp/'movies'
            movies.mkdir()
            for name in ('main', 'InventoryFrame', 'InfoPopup', 'CharacterInfoFrame', 'chat',
                         'CommandWindow', 'MatchingSelect', 'GensRanking', 'PetInventoryFrame', 'GremoryCase'):
                (movies/(name+'.swf')).write_bytes(b'authored stub fixture')
            run = subprocess.run([str(host), str(movies), str(lib)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
            self.assertIn('115 inert callbacks', run.stdout)
