"""World fidelity tour (NATIVE-FIDELITY-002) checks.

Portable (synthetic data only):
  - reconstructed/terrain mu_terrain_scene_passes on worked examples of the render scene's terrain/object order;
  - mu-walk --fidelity-dump writes the native OBJECT images and light grids in objread/lightread layouts;
  - scripts/fidelity_tour.py: manifest building, object matching (missing / extra / field differences), light grid
    and camera comparison, image statistics and the scoreboard, on synthetic snapshots and images.
Private: the instruction comparison is scripts/validate_world_fidelity.py (tests/test_world_fidelity_private.py).
"""
import ctypes
import json
import math
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
sys.path.insert(0, str(ROOT / 'scripts'))
from test_native_objects import snapshot, convert, write_models  # noqa: E402
from test_native_world import write_open_world  # noqa: E402

WALK = NATIVE / 'build/mu-walk'
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'

try:
    from PIL import Image
    import fidelity_tour as tour
except ImportError:   # pragma: no cover - the repository's Python has Pillow
    Image = tour = None


def calls(packed):
    out = []
    while packed:
        out.append({1: 'terrain', 2: 'objects'}[packed & 3])
        packed >>= 2
    return out


class ScenePassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/terrain')], check=True)
        cls.lib = ctypes.CDLL(str(ROOT / f'reconstructed/terrain/libterrain.{SUFFIX}'))
        cls.lib.mu_terrain_scene_passes.argtypes = [ctypes.c_int32, ctypes.c_int, ctypes.c_int]
        cls.lib.mu_terrain_scene_passes.restype = ctypes.c_uint32

    def passes(self, world, top=0, kanturu=0):
        return calls(self.lib.mu_terrain_scene_passes(world, top, kanturu))

    def test_worked_examples(self):
        self.assertEqual(self.passes(0), ['terrain', 'objects'])
        self.assertEqual(self.passes(8), ['terrain', 'objects'])
        self.assertEqual(self.passes(10), ['objects'])          # Icarus: no terrain
        self.assertEqual(self.passes(0x84), ['objects'])
        self.assertEqual(self.passes(-1), ['objects'])
        self.assertEqual(self.passes(0x3f), ['objects', 'terrain'])
        self.assertEqual(self.passes(0x55), ['objects', 'terrain'])
        self.assertEqual(self.passes(0x27), ['terrain', 'objects'])
        self.assertEqual(self.passes(0x27, kanturu=1), ['objects'])
        self.assertEqual(self.passes(0, top=1), ['objects'])
        self.assertEqual(self.passes(0x52, top=1), [])


def light_file(path, primary, frame, characters=()):
    """A lightread-layout snapshot: GLOB (hero pointer), CHAR entries, two LITE sections."""
    glob = struct.pack('<II', 0x0a39d754, 4) + struct.pack('<I', 0x1000)
    body = bytearray(b'MULITLV1') + b'GLOB' + struct.pack('<I', len(glob)) + glob
    chars = bytearray()
    for index, (x, y, z) in enumerate(characters):
        entry = bytearray(0x3670)
        struct.pack_into('<3f', entry, 0x33ac, x, y, z)
        chars += struct.pack('<I', index) + entry
    body += b'CHAR' + struct.pack('<I', len(chars)) + chars
    for grid in (primary, frame):
        raw = struct.pack('<%df' % len(grid), *grid)
        body += b'LITE' + struct.pack('<I', len(raw)) + raw
    Path(path).write_bytes(bytes(body))


def globals_file(path, eye, angle=(-48.5, 0.0, -45.0), fov=39.0, far=3257.8):
    body = bytearray(b'MUGLBLV1')
    for address, payload in ((0x0bdc58f0, struct.pack('<3f', *angle)), (0x0bdc5ab4, struct.pack('<3f', *eye)),
                             (0x01cf1634, struct.pack('<f', fov)), (0x01cf1630, struct.pack('<f', far))):
        body += struct.pack('<II', address, len(payload)) + payload
    Path(path).write_bytes(bytes(body))


class WorldObjectCaseTests(unittest.TestCase):
    """Worked examples of the per-world CreateObject / MoveObject cases (reconstructed/objects)."""

    @classmethod
    def setUpClass(cls):
        import validate_object_render as vor
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.vor = vor
        cls.lib = vor.Library(ROOT / f'reconstructed/objects/libobjects.{SUFFIX}')

    def create(self, world, type_):
        v = self.vor
        r = v.Record()
        r.type, r.scale = type_, 1.0
        r.position[0], r.position[1], r.position[2] = 12850.0, 12850.0, 100.0
        o = ctypes.create_string_buffer(0x3d8)
        log = v.new_log(16)
        status = self.lib.dll.mu_obj_create(ctypes.byref(r), world, o, ctypes.byref(ctypes.c_int32()), 0,
                                            ctypes.byref(log))
        return status, o.raw, v.log_events(log)

    def move(self, world, type_, rand_values=(5, 1, 3, 7, 2, 4, 6, 8)):
        v = self.vor
        o = bytearray(0x3d8)
        struct.pack_into('<i', o, 0x5c, type_)
        struct.pack_into('<4f', o, 0xd8, 1.0, 1.0, 0.1, 0.8)
        struct.pack_into('<f', o, 0xa8, 1.0)
        struct.pack_into('<f', o, 0xbc, 0.16)
        struct.pack_into('<3f', o, 0x158, 12850.0, 12850.0, 100.0)
        values = list(rand_values)
        rand_fn = v.RAND_FN(lambda c: values.pop(0) if values else 0)
        speed_fn = v.SPEED_FN(lambda c, t, a: 0.25)
        inputs = v.MoveInputs(world, 6, 0, 1234.0, (ctypes.c_float * 3)(0, 0, 0), 1, 1, speed_fn, rand_fn, None)
        cobj = ctypes.create_string_buffer(bytes(o), 0x3d8)
        log = v.new_log()
        status = self.lib.dll.mu_obj_move(cobj, 0, ctypes.byref(inputs), ctypes.byref(log))
        return status, cobj.raw, v.log_events(log)

    def test_creation_cases(self):
        status, o, _ = self.create(3, 1)                       # Noria: BlendMesh 1
        self.assertEqual((status, struct.unpack_from('<i', o, 0x74)[0]), (0, 1))
        status, o, _ = self.create(0x25, 0x55)                 # Kanturu hook: range -400
        self.assertEqual(struct.unpack_from('<f', o, 0xc0)[0], -400.0)
        status, o, _ = self.create(0x33, 0x2d)                 # Elbeland hook: range -300
        self.assertEqual(struct.unpack_from('<f', o, 0xc0)[0], -300.0)
        status, o, _ = self.create(8, 0x59)                    # Tarkan: drawn after the characters, speed 0.05
        self.assertEqual((o[0xa], round(struct.unpack_from('<f', o, 0xbc)[0], 6)), (1, 0.05))
        status, o, events = self.create(2, 0x1a8)              # Devias: three CreateEffect calls
        self.assertEqual([e[2] for e in events if e[0] == 0x013c0eaa], [0x1a8, 0x1a9, 0x1aa])
        self.assertEqual(self.create(4, 1)[0], 2)               # Lost Tower: no creation case (unsupported)

    def test_move_cases(self):
        status, o, events = self.move(1, 0x29)                 # Dungeon torch: fire light, range 4
        self.assertEqual(status, 0)
        lights = [e for e in events if e[0] == 0x016cacfc]
        self.assertEqual((len(lights), lights[0][-1]), (1, 4))
        status, o, events = self.move(0x50, 0x71)              # Karutan brazier: light range 3, hidden
        self.assertEqual(([e[-1] for e in events if e[0] == 0x016cacfc], struct.unpack_from('<i', o, 0x68)[0]),
                         ([3], -2))
        status, o, events = self.move(7, 0x20)                 # Atlans crystal: BlendMesh 1, pulsing light
        self.assertEqual(struct.unpack_from('<i', o, 0x74)[0], 1)
        self.assertAlmostEqual(struct.unpack_from('<f', o, 0xa8)[0], math.sin(1234.0 * 0.004) * 0.5 + 0.5, places=5)
        status, o, events = self.move(0x25, 0x10)              # Kanturu: every object plays the ambient sound
        self.assertEqual([e[2] for e in events if e[0] == 0x00a6ac96], [0x26c])


@unittest.skipIf(tour is None, 'Pillow is not installed')
class TourTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)

    def test_dump_and_scoreboard(self):
        with tempfile.TemporaryDirectory() as root:
            write_open_world(root)
            write_models(root, 1, ['Tree01.bmd', 'House01.bmd'])
            objects = [(0, (12850.0, 12850.0, 60.0), (0.0, 0.0, 0.0), 20.0, -1),
                       (115, (12950.0, 12850.0, 60.0), (0.0, 0.0, 45.0), 20.0, -1)]
            snap = Path(root) / 'live-obj.bin'
            snapshot(snap, 0, objects)
            plain = Path(root) / 'plain'
            plain.mkdir()
            convert(snap, plain / 'EncTerrain1.plain', '--version', 0)
            out = Path(root) / 'tour' / 'map'
            frames = out / 'frames'
            frames.mkdir(parents=True)
            result = subprocess.run([str(WALK), '--game-root', root, '--headless', '--frames', '2', '--every', '1',
                                     '--out-dir', str(frames), '--backend', 'soft', '--tile', '128,128', '--no-audio',
                                     '--width', '160', '--height', '100', '--objects-dir', str(plain),
                                     '--fidelity-dump', str(out / 'native')], capture_output=True, text=True,
                                    check=True)
            (out / 'native.jsonl').write_text(result.stdout)   # what `fidelity_tour.py render` keeps
            dump = next(json.loads(l) for l in result.stdout.splitlines() if l.startswith('{"fidelity_dump"'))
            self.assertEqual(dump['objects'], 2)
            world, count, native = tour.read_objects(out / 'native-obj.bin')
            self.assertEqual((world, count, len(native)), (0, 2, 2))
            light = tour.read_light(out / 'native-light.bin')
            self.assertEqual((len(light['primary']), len(light['frame'])), (3 * 65536, 3 * 65536))

            # The "live" side: the same two objects plus one the native lacks, one field changed
            live_objects = objects + [(30, (13000.0, 13000.0, 60.0), (0.0, 0.0, 0.0), 1.0, -1)]
            snapshot(Path(root) / 'live-obj.bin', 0, live_objects)
            raw = bytearray((Path(root) / 'live-obj.bin').read_bytes())
            struct.pack_into('<i', raw, 24 + 8 + 0x74, 3)   # first object's BlendMesh
            (Path(root) / 'live-obj.bin').write_bytes(bytes(raw))
            primary = list(light['primary'])
            frame = list(light['frame'])
            frame[3 * (128 * 256 + 129)] += 0.5            # a light source next to the hero
            light_file(Path(root) / 'live-light.bin', primary, frame, [(12850.0, 12850.0, 60.0)])
            globals_file(Path(root) / 'live-glob.bin', (12850.0 + 707.1068, 12850.0 - 707.1068, 910.0))
            native_png = sorted(frames.glob('frame-*.png'))[-1]
            live = Image.open(native_png).convert('RGB')
            shot = Image.new('RGB', (160, 100 + 10), (0, 0, 0))
            shot.paste(live.point(lambda v: min(255, v + 30)), (0, 10))   # brighter, under a 10-row title bar
            shot.save(Path(root) / 'live.png')
            manifest = {'version': 1, 'out_dir': 'tour', 'width': 160, 'height': 100, 'title_bar': 10,
                        'masks': [[0, 0, 20, 20]],
                        'maps': [{'name': 'map', 'world': 0, 'live_png': 'live.png', 'live_obj': 'live-obj.bin',
                                  'live_globals': 'live-glob.bin', 'live_light': 'live-light.bin'}]}
            (Path(root) / 'tour.json').write_text(json.dumps(manifest))
            subprocess.run([sys.executable, str(ROOT / 'scripts/fidelity_tour.py'), 'compare',
                            str(Path(root) / 'tour.json')], check=True, capture_output=True)
            board = json.loads((Path(root) / 'tour' / 'scoreboard.json').read_text())
            r = board[0]
            self.assertEqual(r['tile'], [128, 128])
            self.assertEqual((r['objects']['live'], r['objects']['native'], r['objects']['missing'],
                              r['objects']['extra']), (3, 2, 1, 0))
            self.assertEqual(r['objects']['missing_types'], {'30': 1})
            blend = r['objects']['fields']['blend_mesh']   # the synthetic snapshot leaves BlendMesh 0, CreateObject -1
            self.assertEqual(blend['objects'], 2)
            self.assertIn({'type': 0, 'live': 3, 'native': -1}, blend['examples'])
            self.assertEqual(r['light']['primary']['map']['mean_abs'], 0.0)
            self.assertEqual(r['light']['frame']['near_hero']['worst'][0]['tile'], [129, 128])
            self.assertGreater(r['image']['mean_abs_diff'], 20)
            self.assertTrue(all(c < 0 for c in r['image']['colour_cast_native_minus_live']))
            self.assertGreaterEqual(r['camera']['eye_distance'], 0.0)   # live globals against the frame report
            self.assertAlmostEqual(r['camera']['fov_difference'], 37.0 - 39.0, places=3)   # the world's camera record
            self.assertTrue((Path(root) / 'tour' / 'map' / 'side.png').exists())
            self.assertIn('| map | 0 | 128,128 |', (Path(root) / 'tour' / 'scoreboard.md').read_text())

    def test_object_matching_rules(self):
        def obj(type_, x, **fields):
            o = bytearray(0x3d8)
            struct.pack_into('<i', o, 0x5c, type_)
            struct.pack_into('<3f', o, 0x110, x, 0.0, 0.0)
            struct.pack_into('<3f', o, 0x158, x, 0.0, 0.0)
            struct.pack_into('<f', o, 0xa0, fields.get('scale', 1.0))
            struct.pack_into('<i', o, 0x68, fields.get('hidden', -1))
            return bytes(o)
        live = [obj(1, 100.0), obj(1, 100.0), obj(2, 5000.0, hidden=-2), obj(3, 50.0, scale=2.0)]
        native = [obj(1, 100.0), obj(2, 5000.0), obj(3, 50.0, scale=2.00000001), obj(4, 9.0)]
        r = tour.compare_objects(live, native, hero=(0.0, 0.0), radius=1000.0)
        self.assertEqual((r['matched'], r['missing'], r['extra']), (3, 1, 1))
        self.assertEqual(r['fields']['hidden_mesh']['objects'], 1)
        self.assertNotIn('hidden_mesh', r['fields_near'])   # the object at x 5000 is outside the radius
        self.assertNotIn('scale', r['fields'])               # within the relative tolerance

    def test_manifest_from_capture_directory(self):
        with tempfile.TemporaryDirectory() as root:
            snapshot(Path(root) / '07-atlans-obj.bin', 7, [])
            Path(root, '07-atlans-glob.bin').write_bytes(b'MUGLBLV1')
            m = tour.build_manifest(root, objects_dir='plain', out_dir='out')
            self.assertEqual([(e['name'], e['world']) for e in m['maps']], [('07-atlans', 7)])
            self.assertIn('live_globals', m['maps'][0])
            self.assertNotIn('live_png', m['maps'][0])


if __name__ == '__main__':
    unittest.main()
