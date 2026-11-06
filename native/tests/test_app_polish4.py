"""APP-POLISH-004: the original's window name and the inventory item render info.

Portable (synthetic data only):
  * scripts/live_lang_to_plain.py reads ItemTRSData (0x06fbb624, map +0x38, record node +0x14) out of a
    synthetic langread snapshot as six signed binary32 words per code;
  * native/core/mu_lang.c + mu_hud_item_trs (native/core/mu_hud.c), compiled with the reconstructed
    RenderItem3D: a listed code gives its record unscaled, an absent code the client's default record
    (0x06fbaa40: 0.5, 0.5, -90, 0, 0, 0.55), a lang folder without the table the itemtrsdata.bmd stand-in;
  * native/client/main.c: the window title is --title or the original's "MU"; the scene/fps suffix is only
    set behind --title-stats / MU_TITLE_STATS=1.
Private (MU_RECOVERY_INTEGRATION=1, pinned text/data and the lang3 snapshot): scripts/validate_app_polish4.py
with small samples (the validator row runs every code and the mutants).
"""
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT/'scripts'))
import live_lang_to_plain as plain  # noqa: E402
import validate_app_polish4 as v  # noqa: E402
from test_native_lang import Memory  # noqa: E402

CC = shutil.which(os.environ.get('CC', 'cc')) or shutil.which('clang')
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
WING = (0.5, 0.44, 270.0, 0.0, 2.0, 0.44)


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def words(values):
    return struct.unpack('<6i', struct.pack('<6f', *values))


@unittest.skipUnless(CC, 'a C compiler is needed')
class AppPolish4(unittest.TestCase):
    def test_converter_reads_itemtrsdata(self):
        m = Memory()
        m.map(plain.ITEMTRS + 0x38, {0x19ab: struct.pack('<6f', *WING), 3: struct.pack('<6f', 0.67, 0.75, 180, 270,
                                                                                         15, 0.55)})
        rows = plain.read_itemtrs(plain.Snapshot(m.snapshot()))
        self.assertEqual(plain.ITEMTRS, 0x06fbb624)
        self.assertEqual(rows, [(3, *words((0.67, 0.75, 180, 270, 15, 0.55))), (0x19ab, *words(WING))])

    def test_render_info_follows_the_lang_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = v.sources()
            nat = v.Native(Path(tmp)/'with', src, [(0x19ab, *words(WING)), (-5, *words((1, 2, 3, 4, 5, 6)))])
            found, t = nat.resolve(0x19ab)
            self.assertEqual(found, 1)
            self.assertEqual((t.offset_x, t.offset_y, *t.rotation, t.scale), tuple(f32(x) for x in WING))
            self.assertEqual(nat.lookup(-5), (1, struct.pack('<6f', 1, 2, 3, 4, 5, 6)))
            for absent in (0, 0x19aa, 0x7fffffff):
                found, t = nat.resolve(absent)
                self.assertEqual(found, 0)
                self.assertEqual((t.offset_x, t.offset_y, *t.rotation, t.scale),
                                 (0.5, 0.5, -90.0, 0.0, 0.0, f32(0.55)))       # the default record 0x06fbaa40
                self.assertEqual(nat.lookup(absent), (0, None))
            self.assertEqual(nat.title, 'MU')
            # no itemtrs.tsv: mu_lang_item_trs is -1 and the bmd stand-in (here none: the default record) applies
            bare = v.Native(Path(tmp)/'without', src, None)
            self.assertEqual(bare.lookup(0x19ab)[0], -1)
            self.assertEqual(bare.resolve(0x19ab)[0], 0)

    def test_window_title_has_no_diagnostics_by_default(self):
        main = (ROOT/'native/client/main.c').read_text()
        self.assertIn('#define MU_WINDOW_TITLE "MU"', main)
        body = v.function(main, 'static void window_title(')
        with tempfile.TemporaryDirectory() as tmp:
            c = Path(tmp)/'title.c'
            c.write_text('#include <stdio.h>\n#define MU_WINDOW_TITLE "MU"\n' + body + r'''
int main(int argc, char **argv) {
    char t[400];
    window_title(t, sizeof t, argc > 1 ? argv[1] : NULL, argc > 2, 6, 25.0);
    puts(t);
    return 0;
}''')
            exe = Path(tmp)/'title'
            subprocess.run([CC, '-std=c11', '-o', str(exe), str(c)], check=True, capture_output=True)
            run = lambda *a: subprocess.run([str(exe), *a], capture_output=True, text=True, check=True).stdout
            self.assertEqual(run(), 'MU\n')
            self.assertEqual(run('Mu The Matrix Native Preview'), 'Mu The Matrix Native Preview\n')
            self.assertEqual(run('X', 'stats'), 'X  scene 6 world  25.0 fps\n')
        # the per-frame title update only runs behind the diagnostic switch
        loop = main[main.index('NATIVE-PERF-001: the rate of the last 25 frames') - 200:]
        self.assertRegex(loop[:400], r'if \(f->title_stats && frames % 25 == 0\)')
        self.assertIn('getenv("MU_TITLE_STATS")', main)
        self.assertIn('"--title-stats"', main)
        self.assertEqual(len(re.findall(r'SDL_SetWindowTitle\(', main)), 1)

    @unittest.skipUnless(PRIVATE, 'private original instructions')
    def test_original_instructions(self):
        from types import SimpleNamespace
        r = v.run(SimpleNamespace(text=None, data=None, snapshot=None, absent=40, item_cases=40, mutants=False))
        self.assertTrue(r['ok'])
        self.assertEqual(r['families']['window_name']['client'][0], ['MU', 'MU'])
        self.assertEqual(r['wing']['model'], '0x2491')
        self.assertAlmostEqual(r['wing']['scale'] / r['wing']['geometry'][-1], 0.44, places=5)   # x frame scale


if __name__ == '__main__':
    unittest.main()
