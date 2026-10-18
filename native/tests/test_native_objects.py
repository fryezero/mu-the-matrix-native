"""Native static map objects (NATIVE-OBJECTS-001) checks.

Portable (synthetic data only): a synthetic world tree with a v12-encoded
EncTerrain<n>.obj and synthetic Object models through `mu-terrain objects`
and `mu-terrain render --objects` (records, model table, the client's
map-number check, plaintext input, the gallery layout), and the headless
viewer with objects (skipped without SDL2).
Private (MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT): every installed
EncTerrain*.obj is refused by OpenWorld's map-number check after the client's
decode (the finding), and the Lorencia / World94 galleries load every model
the client's model pass names. The instruction-level comparison is
scripts/validate_objects.py (tests/test_objects_private.py).
"""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
ROOT = NATIVE.parent
sys.path.insert(0, str(HERE))
import native_fixtures as nf  # noqa: E402
from test_native_terrain import v12_encrypt, write_world  # noqa: E402

TOOL = NATIVE/'build/mu-terrain'
VIEWER = NATIVE/'build/mu-viewer'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')


def obj_plain(folder, records, version=0):
    body = bytes([version, folder & 255]) + struct.pack('<h', len(records))
    for type_, x, y, z, angle, scale in records:
        body += struct.pack('<h7f', type_, x, y, z, 0.0, 0.0, angle, scale)
        if version >= 1:
            body += b'\x01\x01'
    return body


def write_models(root, folder, names):
    directory = Path(root)/'Data'/f'Object{folder}'
    directory.mkdir(parents=True, exist_ok=True)
    for seed, name in enumerate(names, 1):
        path = nf.write_textured_model(directory, seed)
        path.rename(directory/name)
    return directory


def run(*args, check=True):
    result = subprocess.run([str(TOOL), *[str(a) for a in args]], capture_output=True)
    if check and result.returncode:
        raise AssertionError(f'mu-terrain {args[0]} failed: {result.stderr.decode(errors="replace")}')
    return result


class ObjectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)

    def world94(self, root, records, version=0, map_number=94):
        write_world(root, 94)
        data = Path(root)/'Data/World94'
        (data/'EncTerrain94.obj').write_bytes(v12_encrypt(obj_plain(map_number, records, version)))
        write_models(root, 94, ['Object01.bmd', 'Object02.bmd', 'Object14.bmd'])

    def test_records_and_model_table(self):
        with tempfile.TemporaryDirectory() as root:
            records = [(0, 12800.0, 12800.0, 10.0, 90.0, 1.0), (1, 13000.0, 12900.0, 0.0, 45.0, 1.5),
                       (13, 13617.0, 12339.0, 169.5, 0.0, 1.0), (7, 100.0, 100.0, 0.0, 0.0, 1.0)]
            self.world94(root, records, version=1)
            report = json.loads(run('objects', root, '--world', 93).stdout)
            o = report['objects']
            self.assertEqual((o['status'], o['source'], o['version'], o['map'], o['count']), (0, 'installed', 1, 94, 4))
            self.assertEqual(report['model_folder'], 94)
            self.assertEqual([r[0] for r in report['records']], [0, 1, 13, 7])
            self.assertAlmostEqual(report['records'][2][1], 13617.0, places=3)
            self.assertAlmostEqual(report['records'][1][7], 1.5, places=4)
            self.assertEqual(report['models']['0'], ['Data/Object94/Object01.bmd', 1])
            self.assertEqual(report['models']['13'], ['Data/Object94/Object14.bmd', 1])
            self.assertEqual(report['models']['7'][1], 0)
            self.assertEqual(len(report['models']), 300)

    def test_render_draws_objects(self):
        with tempfile.TemporaryDirectory() as root:
            records = [(0, 12800.0, 12800.0, 0.0, 0.0, 30.0), (13, 12900.0, 12850.0, 0.0, 30.0, 30.0),
                       (7, 12800.0, 12900.0, 0.0, 0.0, 1.0)]
            self.world94(root, records)
            common = ['render', root, '--world', 93, '--target', '12850,12850', '--distance', 2500,
                      '--width', 160, '--height', 100]
            plain = json.loads(run(*common).stdout)
            drawn = json.loads(run(*common, '--objects', 'installed').stdout)
            again = json.loads(run(*common, '--objects', 'installed').stdout)
            o = drawn['objects']
            self.assertEqual((o['status'], o['count'], o['types'], o['models_loaded'], o['models_missing'], o['drawn']),
                             (0, 3, 3, 2, 1, 2))
            self.assertNotEqual(plain['sha256'], drawn['sha256'])
            self.assertEqual(drawn['sha256'], again['sha256'])
            self.assertGreater(drawn['triangles'], plain['triangles'])

    def test_map_number_check_and_plaintext_input(self):
        with tempfile.TemporaryDirectory() as root:
            records = [(0, 12800.0, 12800.0, 0.0, 0.0, 1.0)]
            self.world94(root, records, map_number=95)
            o = json.loads(run('objects', root, '--world', 93).stdout)['objects']
            self.assertEqual(o['status'], 2)                    # OpenWorld: "file corrupted"
            self.assertIn('map number 95', o['error'])
            plain = Path(root)/'objects.plain'
            plain.write_bytes(obj_plain(94, records * 2))
            o = json.loads(run('objects', root, '--world', 93, '--objects', plain).stdout)['objects']
            self.assertEqual((o['status'], o['source'], o['count']), (0, 'plain', 2))
            plain.write_bytes(obj_plain(94, records * 2)[:-1])
            o = json.loads(run('objects', root, '--world', 93, '--objects', plain).stdout)['objects']
            self.assertEqual(o['status'], 3)
            (Path(root)/'Data/World94/EncTerrain94.obj').unlink()
            o = json.loads(run('objects', root, '--world', 93).stdout)['objects']
            self.assertEqual(o['status'], 1)

    def test_lorencia_gallery_uses_named_models(self):
        with tempfile.TemporaryDirectory() as root:
            write_world(root, 1)
            write_models(root, 1, ['Tree01.bmd', 'tree13.bmd', 'House01.bmd', 'Object01.bmd'])
            report = json.loads(run('objects', root, '--world', 0, '--objects', 'gallery', '--object-tile',
                                    '100,100').stdout)
            self.assertEqual(report['objects']['source'], 'gallery')
            self.assertEqual([r[0] for r in report['records']], [0, 12, 115])   # Object01.bmd is not in world 0's table
            self.assertAlmostEqual(report['records'][0][1], 10050.0, places=3)
            self.assertEqual(report['models']['12'], ['Data/Object1/Tree13.bmd', 1])
            out = json.loads(run('render', root, '--world', 0, '--objects', 'gallery', '--object-tile', '100,100',
                                 '--width', 64, '--height', 48).stdout)
            self.assertEqual(out['objects']['drawn'], 3)

    @unittest.skipUnless(VIEWER.exists(), 'mu-viewer not built (SDL2)')
    def test_viewer_headless_objects(self):
        with tempfile.TemporaryDirectory() as root:
            self.world94(root, [(0, 12800.0, 12800.0, 0.0, 0.0, 30.0), (1, 12900.0, 12800.0, 0.0, 0.0, 30.0)])
            result = subprocess.run([str(VIEWER), '--terrain', root, '--world', '93', '--headless', '--backend', 'soft',
                                     '--width', '96', '--height', '64', '--target', '12850,12800', '--distance',
                                     '2000', '--objects', 'installed'], capture_output=True, check=True)
            out = json.loads(result.stdout.splitlines()[-1])
            self.assertEqual((out['objects'], out['objects_drawn'], out['object_models']), (2, 2, 2))


@unittest.skipUnless(PRIVATE, 'MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT required')
class InstalledObjectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.root = os.environ['MU_GAME_ROOT']

    def test_installed_obj_files_are_refused(self):
        data = Path(self.root)/'Data'
        worlds = sorted(int(p.name[5:]) - 1 for p in data.glob('World*') if p.name[5:].isdigit() and
                        (p/f'EncTerrain{p.name[5:]}.obj').exists() and int(p.name[5:]) < 200)
        self.assertGreaterEqual(len(worlds), 80)
        refused = 0
        for world in worlds:
            report = json.loads(run('objects', self.root, '--world', world).stdout)
            if report['objects']['folder'] != world + 1:
                continue   # event-map folder groups share another folder's file
            refused += report['objects']['status'] == 2
        self.assertGreaterEqual(refused, 75)

    def test_galleries_load_every_named_model(self):
        for world, models in ((0, 112), (93, 43)):
            out = json.loads(run('render', self.root, '--world', world, '--objects', 'gallery', '--no-textures',
                                 '--width', 64, '--height', 40).stdout)['objects']
            self.assertEqual((out['count'], out['models_loaded'], out['models_missing'], out['drawn']),
                             (models, models, 0, models))


if __name__ == '__main__':
    unittest.main()
