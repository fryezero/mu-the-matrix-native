"""The item model loader's texture step 0x00cd558e and the item bitmap tables (RENDER-ITEMS-TEX-001); the wearer skin
(RENDER-ITEMS-TEX-002); every startup LoadBitmap registration and 0x00c97730's re-registration rule
(RENDER-ITEMS-TEX-003)."""
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_item_textures as it  # noqa: E402


class ItemTextureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.lib = it.bind(C.CDLL(str(ROOT / f'reconstructed/objects/libobjects.{it.SUFFIX}')))

    def open(self, name, files=None, cache=None, folder='Data\\Item\\'):
        case = {'names': [name], 'folder': folder, 'file': 'Sword01.bmd', 'files': files or {}, 'cache': cache or {}}
        events, indices, types, field = it.run_c(self.lib, case)
        return events, indices[0], types[0], field

    def test_texture_folder_then_name_map(self):
        events, index, kind, field = self.open('Sword01.jpg', {'Data\\Item\\Texture\\Sword01.jpg': 7})
        self.assertEqual((events, index, kind, field), ([('load', 'Data\\Item\\Texture\\Sword01.jpg', 0x2600, 0x2900)],
                                                        7, 0, 0))
        # no model-folder, Data\Item\ or OpenTexture retry: the name map, then the message
        events, index, _, _ = self.open('bons.jpg', {'Data\\Item\\bons.jpg': 3}, {'bons.jpg': (5, 'Data\\Skill\\b')})
        self.assertEqual(events[1:], [('find', 'bons.jpg'), ('reuse', 5, 'Data\\Skill\\b', 0x2600, 0x2900)])
        self.assertEqual(index, 5)
        events, index, _, _ = self.open('x.jpg')
        self.assertEqual([e[0] for e in events], ['load', 'find', 'error'])
        self.assertEqual(index, 0x7530)
        events, _, _, _ = self.open('x.bmp', {'Data\\Item\\Texture\\x.bmp': 9})   # any extension goes to LoadImage
        self.assertEqual(events[0][1], 'Data\\Item\\Texture\\x.bmp')

    def test_special_names_and_types(self):
        for name, special in (('skin_a.jpg', 0x7725), ('LEVEL1.jpg', 0x7725), ('Hide.jpg', 0x791a),
                              ('hair_r.tga', 0x7776), ('HQskin_a.jpg', 0x77c7), ('hqskin3.jpg', 0x7869),
                              ('HQskin2.jpg', 0x7818), ('HQskinA.jpg', 0x77c7), ('HQlevel1.jpg', 0x77c7),
                              ('HQhairX.jpg', 0x78ba)):
            events, index, _, _ = self.open(name)
            self.assertEqual((events, index), ([], special), name)
        self.assertEqual(self.open('nude_a.jpg')[2], 1)
        self.assertEqual(self.open('cotton2_a.jpg')[2], 3)
        self.assertEqual(self.open('Cotton_a.jpg')[2], 2)
        self.assertEqual(self.open('nude_a.jpg', {'Data\\Item\\Texture\\nude_a.jpg': 6})[1:3], (6, 1))   # typed and loaded

    def test_field_names(self):
        events, index, _, field = self.open('field_Item896_Armor.jpg',
                                            {'Data\\Item\\Texture\\field_Item896_Armor.jpg': 4})
        self.assertEqual([e[1] for e in events], ['Data\\Item\\Texture\\field_Item896_Armor.jpg',
                                                  'Data\\Item\\Texture\\Item896_Armor.tga'])
        self.assertEqual((index, field), (4, 1))
        self.assertEqual(self.open('Field_x.jpgx')[3], 0)   # strncmp: case-sensitive

    def test_bitmap_tables(self):
        entries = {e[0]: e[1:] for e in it.table_entries()}
        self.assertEqual(entries[0x84d9], ('Item\\texture\\Item1161_Blue_render.jpg', 0x2601, 0x2900))
        self.assertEqual(entries[0x8239], ('Item\\Texture\\black_gold_crom05.jpg', 0x2601, 0x2901))
        self.assertNotIn(0, entries)
        self.assertNotIn('not reached', it.TABLE.read_text())
        # RENDER-ITEMS-TEX-002: the wearer skin bitmaps of the startup routine 0x0182a8fe
        self.assertEqual(entries[0x7725], ('Player\\skin_barbarian_01.jpg', 0x2600, 0x2900))
        self.assertEqual(entries[0x77c7], ('Player\\HQSkinClass101.jpg', 0x2600, 0x2900))
        self.assertNotIn(0x7776, entries)   # hair at skin index 0 is not registered
        self.assertEqual(sum(1 for i in entries if it.SKIN_FIRST <= i <= it.SKIN_LAST), 146)

    def registration(self, calls, index):
        keep = [c[1].encode('latin1') for c in calls]
        table = (it.Call * len(calls))(*[it.Call(c[0], keep[k], c[2], c[3]) for k, c in enumerate(calls)])
        b = it.Bitmap()
        if not self.lib.mu_it_registration(table, len(calls), index, C.byref(b)):
            return None
        return b.path.decode('latin1'), b.filter, b.wrap

    def test_every_startup_registration(self):
        # RENDER-ITEMS-TEX-003: the table is every startup LoadBitmap call, not the indices one body probe named, so
        # bodies admitted later find their bitmaps (the 61 indices of #265/#275/#282 were all registered at startup)
        calls = it.table_entries()
        indices = [c[0] for c in calls]
        self.assertEqual(indices, sorted(indices))
        self.assertEqual((len(calls), len(set(indices))), (1553, 1550))
        self.assertNotIn(0, indices)   # index 0 (object +0x68 passed as the mesh texture) is never registered
        for index, path in ((0x7fe7, 'Effect\\Lava.jpg'), (0x8186, 'effect\\volcano_stone_bg.jpg'),
                            (0x82e3, 'Effect\\black_gold_crom02_mono.jpg'), (0x8531, 'Effect\\ef_line01.jpg')):
            self.assertEqual(self.registration(calls, index)[0], path)
        # computed runs: index base + i, sprintf'd paths
        self.assertEqual(self.registration(calls, 0x8300), ('Item\\texture\\fire_sq_00000.jpg', 0x2600, 0x2900))
        self.assertEqual(self.registration(calls, 0x830b)[0], 'Item\\texture\\fire_sq_00011.jpg')
        self.assertNotIn('fire_sq', self.registration(calls, 0x830c)[0])   # the loop ends at i = 11
        self.assertEqual(self.registration(calls, 0x8105)[0], 'Effect\\xsuper0006.jpg')
        self.assertEqual(self.registration(calls, 0x793a)[0], 'Player\\InvenArmorMale45.tga')
        # two calls: a later file replaces the first; the same file under _stricmp only counts a reference
        self.assertEqual(self.registration(calls, 0x854c)[0], 'Item\\texture\\Blur_Aura002.jpg')
        self.assertEqual(self.registration(calls, 0x7f6c)[0], 'Effect\\shiny05.jpg')
        self.assertNotIn('not reached', it.TABLE.read_text())

    def test_reregister_rule(self):
        def call(slot, path, filt=0x2601, wrap=0x2900):
            keep = []
            return it.run_register_c(self.lib, slot, 0x854c, path, filt, wrap, keep)
        events, ret, slot = call(None, 'Data\\Effect\\a.JPG')
        self.assertEqual((events, ret, slot['refs']), ([('load', 'jpg', 0x854c, 'Data\\Effect\\a.JPG', 0x2601, 0x2900)], 1, 1))
        events, ret, after = call(slot, 'data\\effect\\A.jpg', 0x2600, 0x2901)   # the same file: a reference
        self.assertEqual((events, ret, after['path'], after['filter'], after['refs']), ([], 1, 'Data\\Effect\\a.JPG', 0x2601, 2))
        events, ret, after = call(slot, 'Data\\Item\\a.tga')   # another file: unload, then the tga loader
        self.assertEqual([e[:2] for e in events], [('unload', 0x854c), ('load', 'tga')])
        events, ret, after = call(slot, 'Data\\Item\\a.bmp')   # no loader for the extension: the index is empty
        self.assertEqual((events, ret, after), ([('unload', 0x854c, 1)], 0, None))
        released = dict(slot, refs=0)   # no reference left: no unload, the load replaces it
        events, ret, after = call(released, 'Data\\Item\\b.jpg')
        self.assertEqual(([e[0] for e in events], after['path']), (['load'], 'Data\\Item\\b.jpg'))
        self.assertEqual(call(released, 'Data\\Item\\b.')[2], released)   # nothing loads, nothing changes
        names = it.names_entries()
        keys = [n[0].split('\\')[-1].lower() for n in names]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn(('Effect\\lightning2.jpg', 0x2601, 0x2900), names)

    def test_wearer_skin(self):
        # 0x0139d6a2: class & 0xf plus 16 per evolution tier above the first
        self.assertEqual([self.lib.mu_it_part_skin(c) for c in (0x00, 0x05, 0x11, 0x23, 0x47, 0x8f)],
                         [0, 5, 0x11, 0x23, 0x37, 0x4f])
        self.assertEqual(self.lib.mu_it_skin_bitmap(0x7725, 0x11), 0x7736)
        self.assertEqual(self.lib.mu_it_skin_bitmap(0x78ba, 4), 0x78be)
        self.assertEqual(self.lib.mu_it_skin_bitmap(0x7869, -1), 0x7868)   # movsx
        for index in (0x791a, 0x7724, 0x7530, 0x9000):
            self.assertEqual(self.lib.mu_it_skin_bitmap(index, 9), index)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='items-tex-test-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_item_textures.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(len(result['families']), 6)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), len(it.MUTANTS))
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))


if __name__ == '__main__':
    unittest.main()
