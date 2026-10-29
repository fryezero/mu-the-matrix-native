"""The item model loader's texture step 0x00cd558e and the item bitmap tables (RENDER-ITEMS-TEX-001)."""
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
        names = it.names_entries()
        keys = [n.split('\\')[-1].lower() for n in names]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn('Effect\\lightning2.jpg', names)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='items-tex-test-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_item_textures.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(len(result['families']), 3)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), len(it.MUTANTS))
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))


if __name__ == '__main__':
    unittest.main()
