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
from test_native_world import write_open_world  # noqa: E402
from test_native_charsel import write_world94 as write_charsel_world  # noqa: E402

TOOL = NATIVE/'build/mu-terrain'
WALK = NATIVE/'build/mu-walk'
CHARSEL = NATIVE/'build/mu-charsel'
CONVERT = ROOT/'scripts/live_objects_to_plain.py'
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


def snapshot(path, world, objects):
    """A synthetic object-list snapshot in the layout objread.c writes (no game data)."""
    body = bytearray(b'MUOBJLV1') + struct.pack('<iiiI', world, world, len(objects), len(objects))
    for i, (type_, position, angle, scale, state) in enumerate(objects):
        obj = bytearray(0x3d8)
        obj[5:8] = b'\x01\x01\x01'
        struct.pack_into('<i', obj, 0x5c, type_)
        struct.pack_into('<i', obj, 0x68, state)
        struct.pack_into('<f', obj, 0xa0, scale)
        struct.pack_into('<3f', obj, 0x110, *position)
        struct.pack_into('<3f', obj, 0x158, *position)
        struct.pack_into('<3f', obj, 0x164, *angle)
        struct.pack_into('<ff', obj, 0xe4, 0.8, 0.2)
        body += struct.pack('<II', 0x20000000 + 0x400 * i, 0) + obj
    Path(path).write_bytes(bytes(body))


def convert(snap, out, *args):
    result = subprocess.run([sys.executable, str(CONVERT), '--raw-output', str(snap), '--out', str(out), *map(str, args)],
                            capture_output=True, text=True, check=True)
    return [json.loads(line) for line in result.stdout.splitlines()]


class LiveSnapshotTests(unittest.TestCase):
    """The live-read path on synthetic snapshots: converter, plaintext + hidden sidecar, the front ends."""

    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)

    def test_converter_and_terrain_tools(self):
        with tempfile.TemporaryDirectory() as root:
            write_world(root, 94)
            write_models(root, 94, ['Object01.bmd', 'Object02.bmd', 'Object14.bmd'])
            snap = Path(root)/'snap.bin'
            snapshot(snap, 93, [(0, (12800.0, 12800.0, 0.0), (0.0, 0.0, 90.0), 30.0, -1),
                                (1, (12900.0, 12800.0, 0.0), (0.0, 0.0, 0.0), 30.0, -2),
                                (13, (13629.30078125, 12338.5654296875, 164.5), (0.0, 3.0, 0.0), 1.0, -2),
                                (500, (100.0, 100.0, 0.0), (0.0, 0.0, 0.0), 1.0, -1)])
            obj = Path(root)/'installed.obj'
            obj.write_bytes(bytes(4 + 4 * 45))   # the installed length implies version 3 for 4 objects
            summary, written = convert(snap, Path(root)/'EncTerrain94.plain', '--installed', obj)
            self.assertEqual((summary['world'], summary['objects_in_sectors'], summary['kept']), (93, 4, 3))
            self.assertEqual((written['version'], written['records']), (3, 3))
            self.assertEqual((Path(root)/'EncTerrain94.hidden').read_text().split(), ['1', '13'])
            plain = (Path(root)/'EncTerrain94.plain').read_bytes()
            self.assertEqual(plain[:4], bytes([3, 94]) + struct.pack('<h', 3))
            self.assertEqual(len(plain), 4 + 3 * 45)
            report = json.loads(run('objects', root, '--world', 93, '--objects', Path(root)/'EncTerrain94.plain').stdout)
            self.assertEqual([r[0] for r in report['records']], [0, 1, 13])
            self.assertAlmostEqual(report["records"][2][1], 13629.30078125, places=2)
            out = json.loads(run('render', root, '--world', 93, '--objects', Path(root)/'EncTerrain94.plain',
                                 '--target', '12850,12800', '--distance', 2000, '--width', 96, '--height', 64).stdout)
            self.assertEqual(out['objects']['drawn'], 1)   # types 1 and 13 hidden by the sidecar

    def test_walk_session_draws_objects_from_a_directory(self):
        with tempfile.TemporaryDirectory() as root:
            write_open_world(root)
            write_models(root, 1, ['Tree01.bmd', 'House01.bmd'])
            snap = Path(root)/'snap.bin'
            snapshot(snap, 0, [(0, (12850.0, 12850.0, 60.0), (0.0, 0.0, 0.0), 20.0, -1),
                               (115, (12950.0, 12850.0, 60.0), (0.0, 0.0, 45.0), 20.0, -1),
                               (0, (100.0, 25000.0, 60.0), (0.0, 0.0, 0.0), 20.0, -1)])
            plain_dir = Path(root)/'plain'
            plain_dir.mkdir()
            convert(snap, plain_dir/'EncTerrain1.plain', '--version', 0)
            result = subprocess.run([str(WALK), '--game-root', root, '--headless', '--frames', '2', '--every', '2',
                                     '--out-dir', str(Path(root)/'out'), '--backend', 'soft', '--tile', '128,128',
                                     '--no-audio', '--quiet',   # a 640-wide window: CreateFrustrum2D scales with it
                                     '--width', '640', '--height', '400', '--objects-dir', str(plain_dir)],
                                    capture_output=True, text=True, check=True)
            row = next(json.loads(l) for l in result.stdout.splitlines() if l.startswith('{"objects"'))
            self.assertEqual((row['objects'], row['object_models'], row['objects_drawn']), (3, 2, 2))

    def test_object_lifecycle_in_the_walk_session(self):
        """NATIVE-OBJECTS-002: CreateObject, MoveObjects (street light and candle add terrain light every
        step, the tick runs), RenderObjects culls the far object."""
        with tempfile.TemporaryDirectory() as root:
            write_open_world(root)
            write_models(root, 1, ['StreetLight01.bmd', 'Candle01.bmd'])
            snap = Path(root)/'snap.bin'
            snapshot(snap, 0, [(90, (12850.0, 12850.0, 60.0), (0.0, 0.0, 0.0), 1.0, -1),
                               (150, (12950.0, 12850.0, 60.0), (0.0, 0.0, 45.0), 1.0, -1),
                               (90, (100.0, 25000.0, 60.0), (0.0, 0.0, 0.0), 1.0, -1)])
            plain_dir = Path(root)/'plain'
            plain_dir.mkdir()
            convert(snap, plain_dir/'EncTerrain1.plain', '--version', 0)
            result = subprocess.run([str(WALK), '--game-root', root, '--headless', '--frames', '6', '--every', '6',
                                     '--out-dir', str(Path(root)/'out'), '--backend', 'soft', '--tile', '128,128',
                                     '--no-audio', '--quiet', '--width', '640', '--height', '400',
                                     '--objects-dir', str(plain_dir)], capture_output=True, text=True, check=True)
            row = next(json.loads(l) for l in result.stdout.splitlines() if l.startswith('{"objects"'))
            self.assertEqual((row['objects_created'], row['objects_create_unsupported']), (3, 0))
            self.assertEqual(row['object_draw_list'], 2)                    # the far street light is culled
            self.assertEqual(row['object_lights_last_step'], 2)             # AddTerrainLight per step, range 3
            self.assertEqual(row['object_lights'], row['objects_moved'])   # one light per moved object (none before the first render pass)
            self.assertGreater(row['objects_moved'], 0)
            self.assertEqual(row['object_ticks'], row['objects_moved'])
            out = json.loads(run('render', root, '--world', 0, '--objects', plain_dir/'EncTerrain1.plain',
                                 '--object-steps', 3, '--target', '12850,12850', '--distance', 2000,
                                 '--width', 96, '--height', 64).stdout)
            self.assertEqual(out['objects']['drawn'], 3)

    def test_charsel_takes_markers_and_objects_from_a_directory(self):
        with tempfile.TemporaryDirectory() as root:
            write_charsel_world(root)
            write_models(root, 94, ['Object15.bmd', 'Object01.bmd'])
            snap = Path(root)/'snap.bin'
            snapshot(snap, 93, [(14, (13000.25, 12500.5, 164.5), (0.0, 3.0, 0.0), 1.0, -2),
                                (0, (13100.0, 12500.0, 169.5), (0.0, 0.0, 0.0), 1.0, -1)])
            plain_dir = Path(root)/'plain'
            plain_dir.mkdir()
            convert(snap, plain_dir/'EncTerrain94.plain', '--version', 0)
            result = subprocess.run([str(CHARSEL), '--game-root', root, '--headless', '--frames', '1',
                                     '--out-dir', str(Path(root)/'out'), '--backend', 'soft', '--no-ui', '--quiet',
                                     '--width', '96',
                                     '--height', '64', '--objects-dir', str(plain_dir)],
                                    capture_output=True, text=True, check=True)
            summary = next(json.loads(l) for l in result.stdout.splitlines() if '"summary"' in l)
            self.assertEqual(summary['marker1'], [13000.25, 12500.5, 164.5])
            self.assertEqual((summary['objects'], summary['objects_drawn']), (2, 1))   # the marker type is hidden


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


PLAIN_DIR = os.environ.get('MU_OBJECTS_PLAIN_DIR')


@unittest.skipUnless(PRIVATE and PLAIN_DIR, 'MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT and MU_OBJECTS_PLAIN_DIR '
                                           '(local live-read plaintexts) required')
class LiveReadPrivateTests(unittest.TestCase):
    """The local live-read plaintexts agree with the installed files: same object count, and the count fits
    the installed length for the version written; every model they name exists."""

    def test_counts_match_installed_files(self):
        data = Path(os.environ['MU_GAME_ROOT'])/'Data'
        checked = 0
        for plain in sorted(Path(PLAIN_DIR).glob('EncTerrain*.plain')):
            folder = int(plain.stem[len('EncTerrain'):])
            raw = plain.read_bytes()
            version, count = raw[0], struct.unpack_from('<h', raw, 2)[0]
            sizes = {0: 30, 1: 32, 2: 33, 3: 45, 4: 46, 5: 54}
            installed = data/f'World{folder}'/f'EncTerrain{folder}.obj'
            self.assertEqual(4 + count * sizes[version], installed.stat().st_size, plain.name)
            self.assertEqual(len(raw), 4 + count * sizes[version])
            report = json.loads(run('objects', os.environ['MU_GAME_ROOT'], '--world', folder - 1, '--objects',
                                    plain).stdout)
            types = {r[0] for r in report['records']}
            missing = [t for t in types if t < 300 and not report['models'].get(str(t), [None, 0])[1]]
            # a few types have no installed model (World95: 0, 15, 63; World142: one)
            self.assertLessEqual(len(missing), max(3, len(types) // 10), (plain.name, missing))
            checked += 1
        self.assertGreaterEqual(checked, 1)
