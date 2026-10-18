"""Native terrain (NATIVE-TERRAIN-001) checks.

Portable (synthetic data only):
  * reconstructed/terrain against the independent pure-Python statements of
    the client rules in scripts/validate_terrain.py (parsers, heights, light
    map, normals, primary light, per-tile GL streams for both passes);
  * a synthetic Data/World1 tree (v12-encrypted .map/.att/.obj, 8-bit height,
    light map, OZJ/OZT tile bitmaps) through `mu-terrain` info/render/export,
    the 24-bit height world, the "MAP\\x01" Modulus envelope through
    `mu-terrain decrypt`, render determinism and the headless GL/software
    agreement of `mu-viewer --terrain` (skipped without SDL2).
Private (MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT): every installed world
folder loads with map and attribute numbers equal to the folder, the height
format follows the literal world list or the file length, the installed
EncTerrain*.obj files are reported as not decodable by the client's v12
routine, and Lorencia / Twisted Karutan render with every tile supported.
The instruction-level comparison with the client is scripts/validate_terrain.py.
"""
import ctypes
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
ROOT = NATIVE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT/'scripts'))
import native_fixtures as nf  # noqa: E402
import validate_terrain as vt  # noqa: E402

TOOL = NATIVE/'build/mu-terrain'
VIEWER = NATIVE/'build/mu-viewer'
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
LIBRARY = ROOT/'reconstructed/terrain'/f'libterrain.{SUFFIX}'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
MAP_KEY = bytes.fromhex('d17352f6d29acb273eaf593137b3e7a2')


def v12_encrypt(plain):
    """Inverse of the client's rolling decoder 0x0098c5f2."""
    previous, out = 0x5e, bytearray()
    for i, value in enumerate(plain):
        c = ((value + previous) & 255) ^ MAP_KEY[i % 16]
        out.append(c)
        previous = (c + 0x3d) & 255
    return bytes(out)


def ozj_tga(width, height, seed):
    payload = nf.tga(width, height, seed, alpha=False)   # TGA under .OZJ: the 24-byte prefix repeats its start
    return payload[:24] + payload


def write_world(root, folder=1, *, seed=1, rgb=False, noground=0, obj_ok=True):
    g = random.Random(seed)
    data = Path(root)/'Data'/f'World{folder}'
    data.mkdir(parents=True, exist_ok=True)
    layer1 = bytes(g.choice((0, 1, 2, 5, 7)) for _ in range(65536))
    alpha = bytes(g.choice((0, 0, 0, 255, 128, 7)) for _ in range(65536))
    # layer 2 = 255 ("none") only where alpha is 0, as in the installed maps
    layer2 = bytes(g.choice((0, 3, 5, 255) if a == 0 else (0, 3, 5)) for a in alpha)
    (data/f'EncTerrain{folder}.map').write_bytes(v12_encrypt(bytes([0, folder & 255]) + layer1 + layer2 + alpha))
    cells = [g.choice((0, 0, 4, 0x40 if not noground else 8)) for _ in range(65536)]
    att = bytes([0, folder & 255, 255, 255]) + b''.join(struct.pack('<H', c) for c in cells)
    att = bytes(b ^ (0xfc, 0xcf, 0xab)[i % 3] for i, b in enumerate(att))
    (data/f'EncTerrain{folder}.att').write_bytes(v12_encrypt(att))
    if rgb:
        # three bytes per cell, value = b2 | b1 << 8 | b0 << 16: b0 = b1 = 0 keeps heights in -500..-245
        height = b'BM6\0' + bytes(54) + bytes(g.randrange(10, 256) if i % 3 == 2 else 0 for i in range(3*65536))
    else:
        height = b'BM8\x04' + bytes(0x438) + bytes(g.randrange(256) for _ in range(65536))
    (data/'TerrainHeight.OZB').write_bytes(height)
    header = bytearray(54)
    struct.pack_into('<2sI', header, 0, b'BM', 54 + 3*65536)
    struct.pack_into('<III', header, 14, 40, 256, 256)
    (data/'TerrainLight.OZB').write_bytes(b'BM6\0' + bytes(header) + bytes(g.randrange(64, 256) for _ in range(3*65536)))
    objects = 3
    body = bytes([0, folder & 255]) + struct.pack('<h', objects) + b''.join(
        struct.pack('<h7f', i, 100.0*i, 200.0, 0.0, 0.0, 0.0, 90.0, 1.0) for i in range(objects))
    (data/f'EncTerrain{folder}.obj').write_bytes(v12_encrypt(body) if obj_ok else bytes(len(body)))
    for i, name in enumerate(('TileGrass01', 'TileGrass02', 'TileGround01', 'TileGround02', 'TileGround03',
                              'TileWater01', 'TileWood01', 'TileRock01')):
        (data/f'{name}.OZJ').write_bytes(ozj_tga(32 if i % 2 else 64, 64, seed + i))
    (data/'TileGrass01.OZT').write_bytes(nf.ozt(nf.tga(64, 32, seed + 50)))
    return data


def run(*args, check=True):
    result = subprocess.run([str(TOOL), *[str(a) for a in args]], capture_output=True)
    if check and result.returncode:
        raise AssertionError(f'mu-terrain {args[0]} failed: {result.stderr.decode(errors="replace")}')
    return result


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(ROOT/'reconstructed/terrain')], check=True, capture_output=True)
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.authored = vt.Authored(LIBRARY)


class RuleModelTests(Build):
    """libterrain against the Python statements of the client rules."""

    def test_parsers_heights_light(self):
        g = random.Random(3)
        plain = bytes(g.randrange(256) for _ in range(2 + 3*65536 + 5))
        status, number, l1, l2, alpha = self.authored.parse_map(plain)
        py = vt.py_parse_map(plain)
        self.assertEqual((status, number, l1, l2), (0, py[0], py[1], py[2]))
        self.assertTrue(vt.compare_lists(alpha, py[3]))
        self.assertEqual(self.authored.parse_map(plain[:2 + 3*65536 - 1])[0], 1)
        good = bytes([0, 9, 255, 255]) + b''.join(struct.pack('<H', g.choice((0, 4, 0x7f, 0x500, 0xff7f)))
                                                  for _ in range(65536))
        for plain in (good, good[:0x10004], bytes([1]) + good[1:], good[:3] + b'\0' + good[4:], good[:-1]):
            encrypted = vt.py_xor3(plain)
            status, number, att = self.authored.parse_attributes(encrypted)
            py_status, py_number, py_att = vt.py_parse_attributes(encrypted)
            self.assertEqual(['ok', 'bad-size', 'corrupt'][status], py_status)
            if py_att is not None:
                self.assertEqual(att, py_att)
        bad = bytearray(good)
        bad[4 + 2*77] = 0x80
        self.assertEqual(self.authored.parse_attributes(vt.py_xor3(bytes(bad)))[0], 2)
        h8 = bytes(g.randrange(256) for _ in range(4 + 0x438 + 65536))
        for scale in (1.5, 3.0):
            status, height = self.authored.height_bytes(h8, scale)
            self.assertEqual(status, 0)
            self.assertTrue(vt.compare_lists(height, vt.py_height_bytes(h8, vt.f32(scale))))
        self.assertEqual(self.authored.height_bytes(h8[:-1], 1.5)[0], 1)
        h24 = bytes(g.randrange(256) for _ in range(58 + 3*65536))
        status, height = self.authored.height_rgb(h24)
        self.assertTrue(status == 0 and vt.compare_lists(height, vt.py_height_rgb(h24)))
        header = bytearray(58)
        struct.pack_into('<II', header, 22, 7, 3)
        light = bytes(header) + bytes(g.randrange(256) for _ in range(63))
        status, values = self.authored.light(light)
        self.assertEqual(status, 0)
        self.assertTrue(vt.compare_lists(values, vt.py_light(light)))

    def test_normals_and_primary_light(self):
        g = random.Random(4)
        height = [vt.f32(g.uniform(-500, 2000)) for _ in range(65536)]
        normal = self.authored.normals(height)
        self.assertTrue(vt.compare_lists(normal, vt.py_normals(height)))
        light_map = [vt.f32(g.random()) for _ in range(3*65536)]
        for world in (0, 30):
            self.assertTrue(vt.compare_lists(self.authored.primary_light(normal, light_map, world),
                                             vt.py_primary_light(normal, light_map, world)))

    def test_tile_streams(self):
        g = random.Random(5)
        compared = 0
        for seed, world in enumerate((0, 2, 142, 0x50, 0x3f, 0x8d)):
            scene = vt.synthetic_scene(300 + seed, world)
            built = self.authored.scene(scene)
            for _ in range(120):
                xi, yi = g.randrange(255), g.randrange(255)
                for pass_ in (0, 2):
                    status, stream = self.authored.draw_tile(built, pass_, float(xi), float(yi), xi, yi)
                    expected = []
                    py_status = vt.py_draw_tile(scene, pass_, float(xi), float(yi), xi, yi, expected)
                    self.assertEqual(status, py_status, (world, xi, yi, pass_))
                    if status != 4:
                        self.assertEqual(stream, expected, (world, xi, yi, pass_))
                        compared += 1
        self.assertGreater(compared, 900)

    def test_uv_negative_control(self):
        self.assertTrue(vt.negative_controls(self.authored)['uv_natural_index_differs'])

    # NATIVE-TERRAIN-002

    def test_height_choice_resolved(self):
        for world in range(256):
            rgb, unresolved = self.authored.height_is_rgb(world)
            self.assertEqual((rgb, unresolved), (vt.py_height_is_rgb(world), 0), world)
        self.assertEqual([w for w in range(0x80, 0x95) if self.authored.lib.mu_terrain_world_handler_flag(w) == 1],
                         list(range(0x86, 0x92)))
        self.assertEqual(self.authored.lib.mu_terrain_world_handler_flag(0x41), -1)

    def test_world_tile_streams(self):
        g = random.Random(9)
        compared = effects_seen = 0
        for seed, world in enumerate(vt.SPECIAL_WORLDS):
            scene = vt.synthetic_scene(600 + seed, world, extended=True)
            state = [seed]

            def rand():
                state[0] = (state[0] * 214013 + 2531011) & 0xffffffff
                return (state[0] >> 16) & 0x7fff
            scene['random'] = rand
            built = self.authored.scene(scene)
            for case in range(40):
                xi, yi = g.randrange(1, 254), g.randrange(1, 254)
                built[0].detail = scene['detail'] = 4 if case % 2 else 0
                for pass_ in (0, 2):
                    start = state[0]
                    scene['effects_out'].clear()
                    status, stream = self.authored.draw_tile(built, pass_, float(xi), float(yi), xi, yi)
                    c_effects = list(scene['effects_out'])
                    state[0] = start
                    model_scene = dict(scene, effects=[])
                    expected = []
                    py_status = vt.py_draw_tile(model_scene, pass_, float(xi), float(yi), xi, yi, expected)
                    self.assertEqual(status, py_status, (world, xi, yi, pass_))
                    if status != 4:
                        self.assertEqual(stream, expected, (world, xi, yi, pass_))
                        self.assertEqual(c_effects, model_scene['effects'], (world, xi, yi))
                        effects_seen += len(c_effects)
                        compared += 1
        self.assertGreater(compared, 2500)

    def test_add_light(self):
        g = random.Random(10)
        for case in range(12):
            base = [vt.f32(g.uniform(-0.5, 1.5)) for _ in range(3 * 65536)]
            x, y = vt.f32(g.uniform(-200, 25800)), vt.f32(g.uniform(-200, 25800))
            light = [vt.f32(g.uniform(-1, 2)) for _ in range(3)]
            light_range = g.choice([0, 1, 2, 4])
            mine = self.authored.add_light(x, y, light, light_range, base)
            self.assertTrue(vt.compare_lists(mine, vt.py_add_light(x, y, light, light_range, base)), case)
        # falloff: (range - distance) / range at the cell under the light, no upper clamp
        zero = [0.0] * (3 * 65536)
        lit = self.authored.add_light(12850.0, 12850.0, [2.0, 1.0, 0.5], 2, zero)
        i = 3 * (128 * 256 + 128)
        self.assertAlmostEqual(lit[i], 2.0 * (2 - 0.5 ** 0.5) / 2, places=5)
        self.assertGreater(lit[i], 1.0)

    def test_frustum_and_culling(self):
        rows = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        f = self.authored.frustum_create(2.0, 3000.0, 35.0, rows, [12800.0, 12800.0, 900.0])
        self.assertEqual(list(f.vertex)[:3], [12800.0, 12800.0, 900.0])
        self.assertTrue(all(0 <= v <= 251 for v in (f.x_min, f.y_min, f.x_max, f.y_max)))
        self.assertEqual([f.x_min % 4, f.y_min % 4], [0, 0])
        ok, params = self.authored.params_2d(0, 3, 1280, 1.0, 2400.0)
        self.assertEqual(ok, 1)
        self.assertEqual(params[0], 3300.0)
        status, xs, ys = self.authored.frustum_2d(0, [12800.0, 12800.0, 0.0], [-48.5, 0.0, -45.0], params, 0)
        self.assertEqual(status, 0)
        # the hero cell is inside its own polygon, a far cell is not; scene states 1..4 accept everything
        test = self.authored.lib.mu_terrain_test_frustum_2d
        self.assertEqual(test(vt.floats(xs), vt.floats(ys), 5, 128.0, 128.0, 0.0), 1)
        self.assertEqual(test(vt.floats(xs), vt.floats(ys), 5, 10.0, 10.0, 0.0), 0)
        self.assertEqual(test(vt.floats(xs), vt.floats(ys), 2, 10.0, 10.0, 0.0), 1)
        g = random.Random(11)
        for _ in range(500):
            x, y, r = vt.f32(g.uniform(90, 170)), vt.f32(g.uniform(90, 170)), g.choice([0.0, -80.0])
            self.assertEqual(test(vt.floats(xs), vt.floats(ys), 5, x, y, r), vt.py_test_frustum_2d(xs, ys, 5, x, y, r))
        scene = vt.synthetic_scene(12, 0)
        built = self.authored.scene(scene)
        frustum = vt.Frustum()
        frustum.x_min, frustum.y_min, frustum.x_max, frustum.y_max = 112, 112, 144, 144
        for i in range(4):
            frustum.x2d[i], frustum.y2d[i] = xs[i], ys[i]
        status, culled = self.authored.render(built, frustum, 5, 0, 1)
        status, everything = self.authored.render(built, frustum, 5, 1, 1)   # top view: whole box
        self.assertLess(len(culled), len(everything))
        status, box = self.authored.draw(built, (112, 112, 144, 144), 1)
        self.assertEqual(everything, box)

    def test_decal(self):
        scene = vt.synthetic_scene(13, 0)
        scene['att'] = [0] * 65536
        built = self.authored.scene(scene)
        fans, stream = self.authored.decal(built, 0x7ef7, 12850.0, 12850.0, 2.0, 2.0, [1.0, 0.5, 0.25], 0.0, 1.0,
                                           5.0, 1, 0)
        self.assertEqual(fans, 49)                       # n = (int)2 + 1 = 3: 7 x 7 tiles
        self.assertEqual(stream[0], ('c3', vt.fbits(1.0), vt.fbits(0.5), vt.fbits(0.25)))
        self.assertEqual(stream[1], ('bind', 0x7ef7))
        self.assertEqual(sum(1 for item in stream if item[0] == 'begin'), 49)
        texcoords = [(vt.frombits(t[1]), vt.frombits(t[2])) for t in stream if t[0] == 'tex']
        inside = [uv for uv in texcoords if 0.0 <= uv[0] <= 1.0 and 0.0 <= uv[1] <= 1.0]
        self.assertGreater(len(inside), 0)
        fans, stream = self.authored.decal(built, 0x7ef7, 12850.0, 12850.0, 2.0, 2.0, [1.0, 1.0, 1.0], 0.0, 0.5,
                                           5.0, 0, 1)
        self.assertEqual(stream[0][0], 'c4')
        vertices = [vt.frombits(v[3]) for v in stream if v[0] == 'v']
        self.assertTrue(all(z == 5.0 for z in vertices))   # flat at `height` when not following the terrain
        scene['att'] = [0x200] * 65536
        self.assertEqual(self.authored.decal(self.authored.scene(scene), 0x7ef7, 12850.0, 12850.0, 2.0, 2.0,
                                             [1.0, 1.0, 1.0], 0.0, 1.0, 5.0, 1, 0)[0], 0)


class ToolTests(Build):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def info(self, world):
        return json.loads(run('info', self.root, '--world', world).stdout)

    def test_synthetic_world_loads_and_renders(self):
        write_world(self.root, 1)
        report = self.info(0)
        self.assertEqual((report['map_status'], report['map_number'], report['att_status'], report['att_number']),
                         (0, 1, 0, 1))
        self.assertEqual((report['height_rgb'], report['height_status'], report['light_status']), (0, 0, 0))
        self.assertEqual((report['obj_status'], report['obj_version'], report['obj_count']), (0, 0, 3))
        self.assertGreaterEqual(report['bitmaps_loaded'], 9)
        out = self.root/'a.png'
        first = json.loads(run('render', self.root, '--world', 0, '--width', 160, '--height', 100,
                               '--out', out, '--time', 1234).stdout)
        second = json.loads(run('render', self.root, '--world', 0, '--width', 160, '--height', 100,
                                '--time', 1234).stdout)
        self.assertEqual(first['sha256'], second['sha256'])
        self.assertEqual((first['status'], first['unsupported'], first['missing_texture_binds']), (0, 0, 0))
        self.assertEqual(first['faces'], 252*252)
        self.assertGreater(first['alpha_faces'], 0)
        self.assertGreater(first['grass'], 0)
        self.assertTrue(out.read_bytes().startswith(b'\x89PNG'))
        later = json.loads(run('render', self.root, '--world', 0, '--width', 160, '--height', 100,
                               '--time', 9234).stdout)
        self.assertNotEqual(later['sha256'], first['sha256'])   # water and sway move with time

    def test_noground_rgb_height_and_bad_obj(self):
        write_world(self.root, 143, seed=2, rgb=True, noground=1, obj_ok=False)
        report = self.info(142)
        # world 142 has a handler with byte +4 = 1 (NATIVE-TERRAIN-002): 24-bit, nothing left unresolved
        self.assertEqual((report['height_rgb'], report['height_rgb_unresolved'], report['height_status']),
                         (1, 0, 0))
        self.assertTrue(-490.0 <= report['height_min'] <= -480.0 and report['height_max'] <= -245.0, report)
        self.assertEqual(report['obj_status'], 2)
        render = json.loads(run('render', self.root, '--world', 142, '--width', 64, '--height', 64).stdout)
        self.assertGreater(render['skipped'], 0)
        self.assertEqual(render['faces'] + render['skipped'] // 2, 252*252)

    def test_lights_decal_frustum_options(self):
        write_world(self.root, 1, seed=8)
        effect = self.root/'Data'/'Effect'
        effect.mkdir(parents=True)
        (effect/'flare01.OZJ').write_bytes(ozj_tga(32, 32, 9))
        base = ['--world', 0, '--width', 160, '--height', 100, '--target', '12850,12850', '--yaw', -45, '--pitch', 45,
                '--distance', 2500, '--time', 1234]
        plain = json.loads(run('render', self.root, *base).stdout)
        lit = json.loads(run('render', self.root, *base, '--light', '12850,12850,1,0.5,0.2,4').stdout)
        self.assertNotEqual(plain['sha256'], lit['sha256'])
        self.assertEqual(lit['lights'], 1)
        decal = json.loads(run('render', self.root, *base, '--decal', '12850,12850,2,30').stdout)
        self.assertEqual(decal['decal_fans'], 49)
        culled = json.loads(run('render', self.root, *base, '--frustum', '12850,12850').stdout)
        self.assertEqual(culled['frustum_status'], 0)
        self.assertLess(culled['faces'], plain['faces'])
        box = culled['frustum_box']
        self.assertTrue(box[0] <= 128 <= box[2] and box[1] <= 128 <= box[3], box)
        legacy = json.loads(run('render', self.root, *base, '--light', '12850,12850,1,0.5,0.2,4', '--legacy').stdout)
        self.assertEqual(legacy['sha256'], plain['sha256'])

    def test_animated_layer_world(self):
        # world index 7 (Atlans): layer-2 water (5) under partial alpha is the additive Object8\wt%02d layer
        data = write_world(self.root, 8, seed=10)
        objects = self.root/'Data'/'Object8'
        objects.mkdir(parents=True)
        for n in range(32):
            (objects/f'wt{n:02d}.OZJ').write_bytes(ozj_tga(32, 32, 100 + n))
        report = json.loads(run('render', self.root, '--world', 7, '--width', 120, '--height', 80, '--time', 0).stdout)
        later = json.loads(run('render', self.root, '--world', 7, '--width', 120, '--height', 80,
                               '--time', 40 * 5).stdout)
        self.assertEqual((report['status'], report['unsupported'], report['missing_texture_binds']), (0, 0, 0))
        self.assertEqual((report['frame_counter'], later['frame_counter']), (0, 5))
        self.assertNotEqual(report['sha256'], later['sha256'])
        self.assertTrue(data.exists())

    def test_missing_files_refused(self):
        data = write_world(self.root, 1)
        (data/'TerrainHeight.OZB').unlink()
        result = run('info', self.root, '--world', 0, check=False)
        self.assertNotEqual(result.returncode, 0)

    def test_modulus_envelope_decrypt(self):
        vectors = json.loads((ROOT/'model-recovery/fixtures/modulus-v14-vectors.json').read_text())
        vector = next(v for v in vectors['vectors'] if v['kind'] != 'model')
        expected = bytes((i*37 + 11) % 256 for i in range(vector['body_bytes']))
        path = self.root/'EncTerrain9.map'
        path.write_bytes(b'MAP\x01' + bytes.fromhex(vector['envelope_hex']))
        self.assertEqual(run('decrypt', path).stdout, expected)
        att = self.root/'EncTerrain9.att'
        att.write_bytes(b'ATT\x01' + bytes.fromhex(vector['envelope_hex']))
        self.assertEqual(run('decrypt', att).stdout, expected)
        plain = self.root/'EncTerrain8.map'
        plain.write_bytes(v12_encrypt(b'hello terrain'))
        self.assertEqual(run('decrypt', plain).stdout, b'hello terrain')

    def test_export_matches_library(self):
        write_world(self.root, 1, seed=6)
        out = run('export', self.root, '--world', 0).stdout
        height = struct.unpack_from('<65536f', out, 0)
        raw = (self.root/'Data/World1/TerrainHeight.OZB').read_bytes()
        self.assertTrue(vt.compare_lists(list(height), vt.py_height_bytes(raw, 1.5)))


@unittest.skipUnless(sys.platform == 'darwin', 'headless GL uses CGL (macOS)')
class ViewerTests(Build):
    def test_headless_gl_matches_software(self):
        built = subprocess.run(['make', '-C', str(NATIVE), 'viewer'], capture_output=True)
        if built.returncode:
            self.skipTest('viewer needs SDL2')
        with tempfile.TemporaryDirectory() as tmp:
            write_world(tmp, 1, seed=7)
            for extra in ([], ['--lights', '--frustum', '--decal', '--detail', '4', '--target', '12850,12850',
                               '--yaw', '-45']):
                result = subprocess.run([str(VIEWER), '--terrain', tmp, '--world', '0', '--headless', '--backend',
                                         'gl', '--compare', '--width', '200', '--height', '120', '--distance', '3000',
                                         *extra], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(result.stdout)
                self.assertLess(report['pixels_over_8'], report['pixels'] * 0.10)


@unittest.skipUnless(PRIVATE and os.environ.get('MU_GAME_ROOT'),
                     'Installed-world checks are opt-in (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT)')
class PrivateInstalledTests(Build):
    def test_every_world_folder(self):
        root = os.environ['MU_GAME_ROOT']
        rows = [json.loads(line) for line in run('scan', root).stdout.decode().splitlines()]
        loaded = [r for r in rows if 'error' not in r]
        self.assertGreaterEqual(len(loaded), 80)
        for r in loaded:
            self.assertEqual((r['map_status'], r['map_number'], r['att_status'], r['att_number']),
                             (0, r['folder'], 0, r['folder']), r['folder'])
            self.assertEqual(r['height_status'], 0, r['folder'])
            # 0x016c9868 with the world handler table: nothing unresolved, 24-bit exactly for the literal list
            # and the handlers of 0x86..0x91 (World67 ships a 24-bit file that the client reads as 8-bit).
            self.assertEqual(r['height_rgb_unresolved'], 0, r['folder'])
            self.assertEqual(r['height_rgb'], int(self.authored.height_is_rgb(r['world'])[0]), r['folder'])
            # Finding: the installed .obj files do not decode with 0x0098c5f2.
            self.assertEqual(r['obj_status'], 2, r['folder'])
        for r in rows:
            if 'error' in r:
                self.assertIn('EncTerrain116.map', r['error'])   # World116 ships no .map

    def test_lorencia_and_twisted_karutan(self):
        root = os.environ['MU_GAME_ROOT']
        with tempfile.TemporaryDirectory() as tmp:
            for world in (0, 142, 63, 7):   # + Vulcanus (lava scroll) and Atlans (animated layer), NATIVE-TERRAIN-002
                report = json.loads(run('render', root, '--world', world, '--width', 320, '--height', 200,
                                        '--out', Path(tmp)/f'{world}.png').stdout)
                self.assertEqual((report['status'], report['unsupported'], report['missing_texture_binds']),
                                 (0, 0, 0), world)
                self.assertEqual(report['faces'] + report['skipped'] // 2, 252*252)
                if world != 7:   # Atlans draws no grass
                    self.assertGreater(report['grass'], 0)
                view = json.loads(run('render', root, '--world', world, '--width', 320, '--height', 200, '--target',
                                      '12850,12850', '--frustum', '12850,12850', '--detail', 4, '--decal',
                                      '12850,12850,2,0', '--light', '12850,12850,1,1,1,1').stdout)
                self.assertEqual((view['status'], view['frustum_status'], view['missing_texture_binds']), (0, 0, 0))
                self.assertGreater(view['faces'], 100)


if __name__ == '__main__':
    unittest.main()
