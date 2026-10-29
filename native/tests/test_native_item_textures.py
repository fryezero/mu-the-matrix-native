"""RENDER-ITEMS-TEX-001: item textures by the client's item-model rule, drawn by the real item renderer.

Synthetic root: an Item.bmd record whose model sits in Data/Item and whose mesh bitmaps sit only in
Data/Item/Texture (the item loader 0x00cd558e's folder) or only in Data/Effect (a startup LoadBitmap file in the
name map). The survey host (native/tests/item_textures_host.c) draws every state through mu_renderchar_draw_item
and counts passes drawn with texturing on and no bitmap.

Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT = an installed client): the full 1,691-type survey before (the
model folder only) and after.

RENDER-ITEMS-TEX-002: the item loader's GL_CLAMP, TextureType and the wearer's skin bitmaps (0x7725 + model +0xa4).
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from native_fixtures import write_textured_model
from test_native_data import item_record, xor3
from test_native_hud import counted

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
HOST = NATIVE / 'build/item-textures-host'
TSV = NATIVE.parent / 'docs/research/item-body-types.tsv'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')


def survey(root, tsv, *flags):
    out = subprocess.run([str(HOST), str(root), str(tsv), *flags], check=True, capture_output=True, text=True)
    lines = out.stdout.strip().split('\n')
    return json.loads(lines[-1]), lines[:-1]


def mesh_uploads(root, tsv, *flags):
    """{mesh name: (filter, wrap)} of every surveyed mesh slot (the host's MU_ITEM_TEXTURES_MESHES aid)."""
    env = dict(os.environ, MU_ITEM_TEXTURES_MESHES='1')
    out = subprocess.run([str(HOST), str(root), str(tsv), *flags], check=True, capture_output=True, text=True,
                         env=env)
    rows = [l.split('\t') for l in out.stderr.split('\n') if l.startswith('M\t')]
    return {r[3]: (int(r[5], 16), int(r[6], 16)) for r in rows}


def ozj_jpeg(width, height):
    from PIL import Image
    import io
    buf = io.BytesIO()
    Image.new('RGB', (width, height), (200, 150, 120)).save(buf, 'JPEG')
    return buf.getvalue()[:24] + buf.getvalue()


class ItemTextureSurvey(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/item-textures-host'], check=True, capture_output=True)

    def root(self, folder, texture_dir):
        root = Path(folder)
        for d in ('Data/Local', 'Data/Item/Texture', 'Data/Effect'):
            (root / d).mkdir(parents=True)
        model = write_textured_model(root / 'Data/Item', seed=4, names=['blade.tga', 'lightning2.tga', 'guard.tga'])
        for f in ('blade.OZT', 'LIGHTNING2.OZT', 'guard.OZT'):
            shutil.move(root / 'Data/Item' / f, root / texture_dir(f) / f)
        records = [item_record(0, b'Data\\Item\\', model.name.encode(), b'Test Blade')]
        (root / 'Data/Local/item.bmd').write_bytes(counted(records, xor3))
        tsv = root / 'types.tsv'
        tsv.write_text('type\tvisibility\tshape\tbody_implemented\tstopped_states\n0x0ae6\tweapon\t-\t1\t0\n')
        return root, tsv

    def test_texture_folder_rule(self):
        with tempfile.TemporaryDirectory() as folder:
            root, tsv = self.root(folder, lambda f: 'Data/Item/Texture')
            before, _ = survey(root, tsv, '--legacy')
            after, _ = survey(root, tsv)
            self.assertEqual((before['missing_meshes'], before['white_types']), (3, 1))
            self.assertGreater(before['white_passes'], 0)
            self.assertEqual(after['missing_meshes'], 0)
            # what is left are the glow passes naming the environment bitmaps (Chrome01, ...), absent from this root
            self.assertLess(after['white_passes'], before['white_passes'])
            self.assertEqual(after['passes'], before['passes'])

    def test_model_folder_is_not_asked(self):
        # the client never looks next to the model for a record item: a bitmap only there stays missing
        with tempfile.TemporaryDirectory() as folder:
            root, tsv = self.root(folder, lambda f: 'Data/Item')
            before, _ = survey(root, tsv, '--legacy')
            after, _ = survey(root, tsv)
            self.assertEqual(before['missing_meshes'], 0)
            self.assertEqual(after['missing_meshes'], 3)

    def test_name_map_key_is_the_file_name(self):
        # lightning2 is a startup LoadBitmap file (Effect\lightning2.jpg): a .tga mesh name with that key misses,
        # the same name in Data/Effect as the startup path loads it is found through the map
        with tempfile.TemporaryDirectory() as folder:
            root, tsv = self.root(folder, lambda f: 'Data/Effect' if f == 'LIGHTNING2.OZT' else 'Data/Item/Texture')
            after, _ = survey(root, tsv)
            self.assertEqual(after['missing_meshes'], 1)   # lightning2.tga is not the startup key lightning2.jpg
            self.assertEqual(after['name_map_meshes'], 0)

    def test_clamp_types_and_wearer_skin(self):
        # RENDER-ITEMS-TEX-002: item-rule slots take the loader's GL_NEAREST, GL_CLAMP; a nude_ mesh has TextureType 1
        # (the mesh draw hides it when the body writes +0x40); a skin_ mesh binds 0x7725 + the wearer's skin index
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest('PIL writes the JPEG skin bitmap')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for d in ('Data/Local', 'Data/Item/Texture', 'Data/Effect', 'Data/Player'):
                (root / d).mkdir(parents=True)
            model = write_textured_model(root / 'Data/Item', seed=6, names=['blade.tga', 'nude_arm.tga', 'skin_x.tga'])
            for f in ('blade.OZT', 'NUDE_ARM.OZT'):
                shutil.move(root / 'Data/Item' / f, root / 'Data/Item/Texture' / f)
            (root / 'Data/Player/skin_barbarian_01.OZJ').write_bytes(ozj_jpeg(8, 8))   # 0x7725, LoadBitmap 0x0182a919
            records = [item_record(0, b'Data\\Item\\', model.name.encode(), b'Test Blade')]
            (root / 'Data/Local/item.bmd').write_bytes(counted(records, xor3))
            tsv = root / 'types.tsv'
            tsv.write_text('type\tvisibility\tshape\tbody_implemented\tstopped_states\n0x0ae6\tweapon\t-\t1\t0\n')
            legacy = mesh_uploads(root, tsv, '--legacy')
            after = mesh_uploads(root, tsv)
            self.assertEqual(legacy['blade.tga'], (0x2600, 0x2901))
            self.assertEqual(after['blade.tga'], (0x2600, 0x2900))
            self.assertEqual(after['nude_arm.tga'], (0x2600, 0x2900))
            before, _ = survey(root, tsv, '--legacy')
            plain, _ = survey(root, tsv)
            self.assertEqual(plain['typed_meshes'], 1)
            self.assertEqual(plain['special_meshes'], 1)
            # no wearer: +0xa4 = 0 binds 0x7725 (installed); class 0x11 (skin index 0x11) binds 0x7736, not installed
            self.assertEqual(plain['missing_meshes'], 0)
            worn, lines = survey(root, tsv, '--class', '0x11')
            self.assertEqual(worn['worn'], 1)
            self.assertGreater(worn['white_passes'], plain['white_passes'])
            self.assertIn('[skin_x.tga special]', lines[0])
            self.assertIn('wearer 0x11', lines[0])
            # the nude_ mesh is not drawn where the body writes +0x40 > 0
            self.assertLess(plain['passes'], before['passes'])

    @unittest.skipUnless(PRIVATE, 'installed client data required')
    def test_private_installed_survey(self):
        root = os.environ['MU_GAME_ROOT']
        before, _ = survey(root, TSV, '--legacy')
        after, lines = survey(root, TSV)
        self.assertEqual(before['types'], 1691)
        self.assertGreater(before['missing_meshes'], 4000)
        self.assertGreater(before['white_types'], 1400)
        self.assertEqual(after['missing_meshes'], 0)
        self.assertLess(after['white_types'], 30)   # RENDER-ITEMS-TEX-002: 28 with +0xa4 = 0 (hair 0x7776/0x78ba)
        worn, worn_lines = survey(root, TSV, '--wearer')
        self.assertEqual(worn['white_types'], 15)   # only the unregistered index 0 is left
        self.assertTrue(all(l.endswith('0x0000') for l in worn_lines), worn_lines)
        self.assertGreater(after['name_map_meshes'], 0)
        # what stays white: special mesh names (the wearer's skin bitmaps) or the unregistered index 0
        for line in lines:
            reasons = line.split('\t')
            self.assertTrue(' special]' in line or reasons[-1].endswith('0x0000'), line)


if __name__ == '__main__':
    unittest.main()
