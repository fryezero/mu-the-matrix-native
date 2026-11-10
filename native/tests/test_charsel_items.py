"""CHARSEL-ITEMS-001: authored selection records, fallback and original callers."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_charsel_items as validation
import native_fixtures as nf
from test_native_charsel import Build as SceneBuild, run


class Adapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lib = validation.build(Path(cls.tmp.name), validation.HEADER.read_text(), 'portable')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_record_and_slot_boundaries(self):
        for slot in range(-2, 12):
            for active in (0, 1):
                r = validation.Record(active, 15, 1, 255, 8191)
                g = validation.Glow(type=-37, level=-19)
                result = self.lib.record_glow(ctypes.byref(r), slot, ctypes.byref(g))
                self.assertEqual(result, int(bool(active) and 1 <= slot < 9))
                if result:
                    self.assertEqual((g.type, g.level, g.option, g.ext),
                                     (0xae6 + 8191, 15, 1, 255 if slot < 6 else 0))
                else:
                    self.assertEqual((g.type, g.level), (-37, -19))


class SelectionItems(SceneBuild):
    def listing(self, text):
        item = self.root / 'Data/Item'
        item.mkdir(exist_ok=True)
        (item / 'Synthetic.bmd').write_bytes(nf.envelope_v15(nf.character_layout(17, bones=50,
                                                                                 actions=3, keys=(3, 2))))
        path = self.out('records.txt')
        path.write_text(text)
        return path

    def scene(self, text, out, *extra):
        listing = self.listing(text)
        frames, summary, entries, p = run(self.root, '--marker', self.marker, '--list', listing, '--no-ui',
                                           '--frames', '3', '--every', '2', '--width', '160', '--height', '100',
                                           '--out-dir', self.out(out), *extra)
        records = [json.loads(line) for line in p.stdout.splitlines() if line.startswith('{')]
        return frames, summary, entries, [r for r in records if r.get('selection_items')]

    def test_record_propagation_and_link_ext(self):
        f, _, entries, records = self.scene('7 1 10 Demo armor=Item/Synthetic.bmd@8:0:11:0:2 '
                                           'weapon0=Item/Synthetic.bmd@0:4:9:1:255 '
                                           'wing=Item/Synthetic.bmd@12:1:7:1:255\n', 'propagate')
        self.assertEqual(len(entries), 1)
        slots = {s['item']: s for s in records[0]['slots']}
        self.assertEqual(records[0]['record_entry'], 0)
        for slot, want in {2: (0x1ae6, 11, 0, 2), 6: (0xaea, 9, 1, 0), 8: (0x22e7, 7, 1, 0)}.items():
            got = slots[slot]
            self.assertEqual(tuple(got[k] for k in ('type', 'level', 'option', 'ext')), want)
            self.assertGreater(got['passes'], 0)
            self.assertEqual(got['special'], 0)
        self.assertEqual((f[-1]['selected'], f[-1]['drawn_entry']), (7, 0))

    def test_level_and_excellent_passes(self):
        counts = []
        for suffix in ('@0:4:0', '@0:4:9', '@0:4:9:1'):
            _, _, _, records = self.scene('0 1 10 Demo weapon0=Item/Synthetic.bmd' + suffix + '\n',
                                          'passes-' + str(len(counts)))
            counts.append(records[0]['slots'][0]['passes'])
        self.assertLess(counts[0], counts[1])
        self.assertLess(counts[1], counts[2])

    def test_file_only_fallback_is_deterministic(self):
        text = '0 1 10 Demo weapon0=Item/Synthetic.bmd\n'
        a = self.scene(text, 'plain-a')
        b = self.scene('# no authored record\n' + text, 'plain-b')
        self.assertEqual(a[3], [])
        self.assertEqual(b[3], [])
        self.assertEqual([f['sha256'] for f in a[0]], [f['sha256'] for f in b[0]])

    def test_selected_entry_and_undrawn_records(self):
        _, summary, entries, records = self.scene(
            '7 1 10 DemoA weapon0=Item/Synthetic.bmd@0:4:9:1\n'
            '3 1 10 DemoB weapon0=Item/Synthetic.bmd@0:4:7\n', 'entry', '--slot', '3', '--enter', '0')
        self.assertEqual(len(entries), 2)
        self.assertEqual(records[0]['slots'][0]['passes'], 0)
        self.assertGreater(records[1]['slots'][0]['passes'], 0)
        self.assertGreaterEqual(summary['enter_requests'], 1)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'needs private pinned instructions')
class InstructionComparison(unittest.TestCase):
    def test_original_selection_item_callers(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / 'report.json'
            # The registry owns the one full-count/mutant run; 8d gets a small private smoke.
            command = [sys.executable, str(ROOT / 'scripts/validate_charsel_items.py'), '--cases', '200',
                       '--output', str(report)]
            subprocess.run(command, check=True, capture_output=True, cwd=ROOT)
            data = json.loads(report.read_text())
            self.assertTrue(all(f['cases'] and not f['mismatches'] for f in data['families'].values()))
            self.assertTrue(all(data.get('mutants', {'no_mutants': 1}).values()))


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT'),
                     'needs MU_GAME_ROOT and private installed item textures')
class PrivateTextures(unittest.TestCase):
    def test_level_and_excellent_reach_pixels(self):
        subprocess.run(['make', '-C', str(ROOT / 'native'), 'charsel'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            binary = folder / 'mu-charsel-window'
            shutil.copy2(ROOT / 'native/build/mu-charsel-window', binary)
            env = dict(os.environ)
            if env.get('MU_NATIVE_DATA_DIR'):
                env['MU_LANG_DIR'] = str(Path(env['MU_NATIVE_DATA_DIR']) / 'lang')
            images, passes, clocks = [], [], []
            for n, suffix in enumerate(('@0:68:0', '@0:68:9', '@0:68:9:1')):
                listing = folder / 'list.txt'
                listing.write_text('1 0x01 400 Ironclad weapon0=Item/CookriShortSword.bmd' + suffix + '\n')
                out = folder / str(n)
                p = subprocess.run([str(binary), '--game-root', env['MU_GAME_ROOT'], '--list', str(listing),
                                    '--slot', '1', '--headless', '--no-ui', '--backend', 'gl', '--frames', '12',
                                    '--every', '11', '--width', '640', '--height', '400', '--out-dir', str(out)],
                                   capture_output=True, text=True, check=True, cwd=ROOT, env=env)
                rows = [json.loads(line) for line in p.stdout.splitlines() if line.startswith('{')]
                draw = next(row for row in rows if row.get('selection_items'))['slots'][0]
                self.assertEqual((draw['special'], draw['refused']), (0, 0))
                passes.append(draw['passes'])
                clocks.append([row['tick'] for row in rows if 'frame' in row])
                images.append((out / 'frame-0011.png').read_bytes())
            self.assertEqual(passes, [2, 6, 8])
            self.assertEqual(clocks, [clocks[0]] * 3)
            self.assertNotEqual(images[0], images[1], 'level glow produced no pixels')
            self.assertNotEqual(images[1], images[2], 'excellent produced no pixels')

if __name__ == '__main__':
    unittest.main()
