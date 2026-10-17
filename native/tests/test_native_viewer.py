"""Native viewer (NATIVE-VIEW-001) checks.

Portable (synthetic data only, run in CI on macOS and Linux):
  * loader agreement with the Python readers (v10/v12/v14/v15, malformed input);
  * golden data: `mu-render dump` equals the reconstructed libraries and the
    validators' pure-Python models byte for byte, through independently built
    client memory (native/tests/reference.py);
  * mesh draw: the ported per-corner loop and colour pass equal an independent
    Python statement of the rules in every portable draw mode
    (native/tests/meshdraw_reference.py), plus direct ctypes checks;
  * textures: OZT/OZB/TGA/BMP decoding against Pillow;
  * renders: software-rasterizer SHA-256 regression hashes and PNG round trip;
  * the windowed viewer builds and its headless GL output agrees with the
    software renderer (macOS with SDL2; explicit skip otherwise).
Private (MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT): installed-model golden
sample per version, the full corpus scan, texture decoding against Pillow and
GL/software render agreement. Renders of installed assets stay in a temporary
directory.
"""
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
ROOT = NATIVE.parent
sys.path.insert(0, str(HERE))
import native_fixtures as nf  # noqa: E402
import meshdraw_reference as mr  # noqa: E402
import reference  # noqa: E402

TOOL = NATIVE/'build/mu-render'
VIEWER = NATIVE/'build/mu-viewer'
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'

# Software-rasterizer regression hashes (raw RGBA8 pixels) for the synthetic
# textured model; see RenderTests.
RENDER_HASHES = {
    'default': 'a3e3e713e4bcaeebbce4d8b2cf7cd8fddd96c1ff0993aa2071b9a369fcc16e13',
    'nearest-yaw': '0706ffb76e438f8a890cd02efb2a38c86867ef4b136c928debeaa54b6024f96f',
    'blend-alpha': 'a9118fa33b08f74ae2e4f1a7414aea5e981c12f6be55acf18f6a10e35bb1c735',
    'additive-env': '222cd899561ac73197e5d204e778bddca897cbcac38d84b80799c41e9810147b',
    'alpha-test-unlit': '6c2f397b6650e66023577ccde409fd2a2fed88bc0c5c1df44785a6ee0e5ffb3c',
}


def run(*args, check=True):
    result = subprocess.run([str(TOOL), *[str(a) for a in args]], capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'mu-render {args[0]} failed: {result.stderr}')
    return result


def png_pixels(path):
    data = Path(path).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    offset, idat, width, height = 8, b'', 0, 0
    while offset < len(data):
        length, = struct.unpack('>I', data[offset:offset+4])
        kind, body = data[offset+4:offset+8], data[offset+8:offset+8+length]
        if zlib.crc32(kind+body) != struct.unpack('>I', data[offset+8+length:offset+12+length])[0]:
            raise AssertionError('PNG CRC mismatch')
        if kind == b'IHDR':
            width, height = struct.unpack('>II', body[:8])
        elif kind == b'IDAT':
            idat += body
        offset += 12+length
    raw = zlib.decompress(idat)
    row = width*4+1
    assert all(raw[y*row] == 0 for y in range(height))
    return width, height, b''.join(raw[y*row+1:(y+1)*row] for y in range(height))


def pk(record):
    return struct.pack('<II4f', *record)


class NativeBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.directory = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls.directory.name)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()


class LoaderTests(NativeBuild):
    def info(self, raw):
        path = self.tmp/'model.bmd'
        path.write_bytes(raw)
        return run('info', path, check=False)

    def test_all_envelopes_match_the_python_readers(self):
        layout = nf.synthetic_layout(3, four_corner=True)
        envelopes = [(10, layout), (12, nf.envelope_v12(layout)), (15, nf.envelope_v15(layout))]
        envelopes += [(14, raw) for _, raw in nf.v14_models()]
        self.assertGreaterEqual(len(envelopes), 20)
        for version, raw in envelopes:
            with self.subTest(version=version):
                model, plain = reference.decode(raw)
                result = self.info(raw)
                self.assertEqual(result.returncode, 0, result.stderr)
                info = json.loads(result.stdout)
                self.assertEqual(info['version'], version)
                self.assertEqual(info['payload_bytes'], len(plain))
                self.assertEqual(info['parsed_bytes'], model['parsed_bytes']-4)
                self.assertEqual(info['keys'], [a['keys'] for a in model['actions']])
                self.assertEqual(info['locks'], [int(a['lock_positions']) for a in model['actions']])
                self.assertEqual([m['texture'] for m in info['mesh_list']],
                                 [m['texture']['text'] for m in model['meshes']])
                self.assertEqual([m['polygons'] for m in info['mesh_list']],
                                 [len(m['polygons']) for m in model['meshes']])

    def test_malformed_inputs_rejected_exactly_when_python_rejects(self):
        layout = bytearray(nf.synthetic_layout(4))
        variants = [bytes(layout[:n]) for n in range(0, len(layout), 37)]
        for offset in range(4, 400, 3):
            for value in (0xff, 0x7f, 0x02, 0x80):
                mutated = bytearray(layout)
                mutated[offset] = value
                variants.append(bytes(mutated))
        nan = bytearray(layout)
        struct.pack_into('<f', nan, 4+32+6+10+4, math.nan)
        variants += [bytes(nan), bytes(layout)+b'x', bytes(layout)+b'\0'*16]
        padded = nf.envelope_v15(bytes(layout))
        variants += [padded, padded[:-1], nf.envelope_v12(bytes(layout))[:-3], b'BMD\x0b'+bytes(layout[4:])]
        accepted = rejected = 0
        for raw in variants:
            try:
                reference.decode(raw)
                python_ok = True
            except Exception:
                python_ok = False
            native_ok = self.info(raw).returncode == 0
            self.assertEqual(native_ok, python_ok, raw[:8].hex())
            accepted += python_ok
            rejected += not python_ok
        self.assertGreater(accepted, 20)
        self.assertGreater(rejected, 100)


STATES = [
    {},
    {'action': 1, 'frame': 2.5, 'prior_action': 0, 'prior_frame': 3.0},
    {'action': 2, 'frame': 0.0, 'ticks': 3},
    {'action': 0, 'frame': 3.75, 'ticks': 7, 'speed': 0.4, 'special': 4, 'head': (10.0, -20.0),
     'angles': (5.0, 10.0, 30.0), 'scale': 1.5, 'origin': (1.0, 2.0, 3.0), 'pose_translate': 1},
    {'action': 1, 'frame': 1.25, 'ticks': 2, 'bone_scale': 0.75, 'vertex_scale': 2.0, 'world': 30, 'bounds_mode': 2},
    {'action': 0, 'frame': 1.0, 'lighting': 0, 'translate': 0, 'stop': 1, 'ticks': 12},
    {'action': 1, 'frame': 0.5, 'ticks': 5, 'speed': -0.3, 'scene': 5, 'override': 1, 'light_angles': (10.0, 20.0, 30.0)},
]


class GoldenDataTests(NativeBuild):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reference = reference.Reference()

    def compare(self, path, raw, state):
        expected = self.reference.outputs(raw, state)
        result = run('dump', path, '--out', self.tmp/'dump.bin', *reference.cli_arguments(state))
        observed = reference.read_dump(self.tmp/'dump.bin')
        report = json.loads(result.stdout)
        if expected is None:
            self.assertEqual(report['posed'], 0)
            return 0
        self.assertEqual(report['posed'], 1)
        self.assertEqual(struct.pack('<f', report['frame']), struct.pack('<f', expected['state']['frame']))
        self.assertEqual(struct.pack('<f', report['prior_frame']), struct.pack('<f', expected['state']['prior_frame']))
        self.assertEqual(report['prior_action'], expected['state']['prior_action'])
        self.assertEqual(report['loop'], expected['state']['loop'])
        self.assertEqual(observed['bones'], expected['bones'])
        vertices = 0
        for mine, theirs in zip(observed['meshes'], expected['meshes']):
            for key in ('vertices', 'normals', 'lights', 'secondary'):
                if theirs[key] is not None:
                    self.assertEqual(mine[key], theirs[key], key)
            vertices += len(mine['vertices'])//12
        return vertices

    def test_synthetic_models_equal_the_reconstructed_functions(self):
        cases = vertices = 0
        for seed in (5, 6):
            layout = nf.synthetic_layout(seed, four_corner=seed == 6)
            for version, raw in ((10, layout), (12, nf.envelope_v12(layout)), (15, nf.envelope_v15(layout))):
                path = self.tmp/f's{seed}v{version}.bmd'
                path.write_bytes(raw)
                for state in STATES:
                    with self.subTest(seed=seed, version=version, state=state):
                        vertices += self.compare(path, raw, state)
                        cases += 1
        for name, raw in nf.v14_models()[:8]:
            path = self.tmp/'v14.bmd'
            path.write_bytes(raw)
            with self.subTest(v14=name):
                self.compare(path, raw, {'frame': 0.0})
                cases += 1
        self.assertEqual(cases, 2*3*len(STATES)+8)
        self.assertGreater(vertices, 300)

    def test_comparison_detects_a_wrong_input(self):
        layout = nf.synthetic_layout(7)
        path = self.tmp/'neg.bmd'
        path.write_bytes(layout)
        expected = self.reference.outputs(layout, {'action': 0, 'frame': 1.5})
        run('dump', path, '--out', self.tmp/'neg.bin', *reference.cli_arguments({'action': 0, 'frame': 1.25}))
        self.assertNotEqual(reference.read_dump(self.tmp/'neg.bin')['meshes'][0]['vertices'],
                            expected['meshes'][0]['vertices'])


MODES = [
    ({}, []), ({'alpha': 0.5}, ['--alpha', '0.5']), ({'alpha': math.nan}, ['--alpha', 'nan']),
    ({'lighting': 0}, ['--lighting', '0']), ({'lighting': 0, 'alpha': 0.25}, ['--lighting', '0', '--alpha', '0.25']),
    ({'mode': 4}, ['--mode', '4']),
    ({'mode': 0x1000, 'uoff': 0.25, 'voff': -0.5}, ['--mode', '0x1000', '--uv-offset', '0.25', '-0.5']),
    ({'mode': 0x80000, 'alpha': 0.5}, ['--mode', '0x80000', '--alpha', '0.5']), ({'mode': 0x100000}, ['--mode', '0x100000']),
    ({'mode': 1}, ['--mode', '1']), ({'mode': 0x40, 'flags': 0x40}, ['--mode', '0x40', '--flags', '0x40']),
    ({'uv_mesh': 1, 'uoff': 0.5, 'voff': 0.125}, ['--uv-mesh', '1', '--uv-offset', '0.5', '0.125']),
    ({'flags': 0x20}, ['--flags', '0x20']), ({'flags': 0x420}, ['--flags', '0x420']),
    ({'flags': 0x200000}, ['--flags', '0x200000']),
    ({'flags': 0x200000, 'voff': 5.0}, ['--flags', '0x200000', '--uv-offset', '0', '5']),
    ({'secondary': 1}, ['--secondary', '1']), ({'skip': 1}, ['--light-skip-mesh', '1']),
    ({'colour': (0.5, 0.25, 2.0), 'mode': 4}, ['--color', '0.5', '0.25', '2', '--mode', '4']),
    ({'flags': 0x2080}, ['--flags', '0x2080']), ({'flags': 0x10}, ['--flags', '0x10']),
    ({'flags': 0x400000}, ['--flags', '0x400000']), ({'flags': 0x40001}, ['--flags', '0x40001']),
    ({'flags': 1, 'alpha': 0.5}, ['--flags', '1', '--alpha', '0.5']),
    ({'alpha_test': 1, 'cull': 0}, ['--alpha-test', '--cull', '0']),
]


class MeshDrawTests(NativeBuild):
    def test_call_stream_equals_the_independent_rule_model(self):
        records = 0
        for seed, version in ((8, 10), (9, 15)):
            layout = nf.synthetic_layout(seed, four_corner=True)
            raw = layout if version == 10 else nf.envelope_v15(layout)
            path = self.tmp/f'md{seed}.bmd'
            path.write_bytes(raw)
            model, _ = reference.decode(raw)
            base = ['--action', '1', '--frame', '1.5', '--origin', '3', '4', '5']
            for options, args in MODES:
                with self.subTest(seed=seed, args=args):
                    run('dump', path, '--out', self.tmp/'md.bin', *base, *args)
                    dump = reference.read_dump(self.tmp/'md.bin')
                    result = json.loads(run('corners', path, '--out', self.tmp/'md.ops', *base, *args).stdout)
                    expected = mr.model_stream(model, dump, dict(options, origin=(3.0, 4.0, 5.0)))
                    observed = mr.read_corners(self.tmp/'md.ops')
                    self.assertEqual([pk(r) for r in observed], [pk(r) for r in expected])
                    self.assertEqual(result['refused'], 0)
                    records += len(observed)
        self.assertGreater(records, 8000)

    def test_client_call_paths_are_refused_not_approximated(self):
        path = self.tmp/'refuse.bmd'
        path.write_bytes(nf.synthetic_layout(10))
        for args in (['--mode', '0x8000'], ['--flags', '0x400']):
            result = json.loads(run('corners', path, '--out', self.tmp/'r.ops', *args).stdout)
            self.assertEqual(result['refused'], result['meshes'])
            self.assertEqual(result['corners'], 0)
            ops = [r[1] for r in mr.read_corners(self.tmp/'r.ops')]
            self.assertNotIn(mr.OP_VERTEX, ops)

    def test_module_directly_bounds_indices_and_handles_nan_alpha(self):
        library = ctypes.CDLL(str(NATIVE/f'build/libmumeshdraw.{SUFFIX}'))
        TC = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_float, ctypes.c_float)
        C3 = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_float))
        C4 = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float)
        V = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_float))

        class Sink(ctypes.Structure):
            _fields_ = [('context', ctypes.c_void_p), ('texcoord', TC), ('color3', C3), ('color4', C4), ('vertex', V)]

        class Mesh(ctypes.Structure):
            _fields_ = [('triangles', ctypes.c_void_p), ('triangle_count', ctypes.c_int32),
                        ('texcoords', ctypes.c_void_p), ('texcoord_count', ctypes.c_int32),
                        ('vertices', ctypes.c_void_p), ('vertex_count', ctypes.c_int32),
                        ('light_colors', ctypes.c_void_p), ('normal_texcoords', ctypes.c_void_p),
                        ('normal_count', ctypes.c_int32), ('model_color', ctypes.c_void_p), ('origin', ctypes.c_void_p)]

        class Params(ctypes.Structure):
            _fields_ = [('mode', ctypes.c_int32), ('flags', ctypes.c_uint32), ('alpha', ctypes.c_float),
                        ('u_offset', ctypes.c_float), ('v_offset', ctypes.c_float), ('apply_uv_offset', ctypes.c_uint8),
                        ('light_colors', ctypes.c_uint8)]
        log = []
        sink = Sink(None, TC(lambda c, s, t: log.append(('t', s, t))), C3(lambda c, p: log.append(('c3', p[0], p[1], p[2]))),
                    C4(lambda c, r, g, b, a: log.append(('c4', r, g, b, a))), V(lambda c, p: log.append(('v', p[0], p[1], p[2]))))
        triangle = bytearray(0x24)
        triangle[0] = 3
        struct.pack_into('<4h', triangle, 2, 0, 1, 2, 0)
        struct.pack_into('<4h', triangle, 0xa, 0, 1, 1, 0)
        struct.pack_into('<4h', triangle, 0x12, 1, 0, 1, 0)
        tri = (ctypes.c_uint8*0x24).from_buffer_copy(triangle)
        floats = lambda values: (ctypes.c_float*len(values))(*values)
        tex, verts = floats([0, 0, 0.5, 0.25]), floats([1, 2, 3, 4, 5, 6, 7, 8, 9])
        lights, table, colour, origin = floats([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]), floats([0.0]*4), floats([1, 1, 1]), floats([0, 0, 0])
        mesh = Mesh(ctypes.addressof(tri), 1, ctypes.addressof(tex), 2, ctypes.addressof(verts), 3, ctypes.addressof(lights),
                    ctypes.addressof(table), 2, ctypes.addressof(colour), ctypes.addressof(origin))
        corners = ctypes.c_long()
        function = library.mu_meshdraw_corners
        function.restype = ctypes.c_int
        status = function(ctypes.byref(mesh), ctypes.byref(Params(2, 0, math.nan, 0, 0, 0, 1)), ctypes.byref(sink),
                          ctypes.byref(corners))
        self.assertEqual((status, corners.value), (0, 3))
        self.assertEqual([entry[0] for entry in log], ['t', 'c4', 'v']*3)   # NaN alpha takes glColor4f
        self.assertEqual(log[0][1:], (0.5, 0.25))
        log.clear()
        mesh.vertex_count = 2   # corner 2 uses vertex 2: refused before any call
        status = function(ctypes.byref(mesh), ctypes.byref(Params(2, 0, 1.0, 0, 0, 0, 1)), ctypes.byref(sink),
                          ctypes.byref(corners))
        self.assertEqual((status, log), (2, []))
        mesh.vertex_count, mesh.normal_count = 3, 1
        status = function(ctypes.byref(mesh), ctypes.byref(Params(2, 0, 1.0, 0, 0, 0, 0)), ctypes.byref(sink),
                          ctypes.byref(corners))
        self.assertEqual(status, 0)   # normals unused without light colours
        self.assertEqual(function(ctypes.byref(mesh), ctypes.byref(Params(2, 0, 1.0, 0, 0, 0, 1)), ctypes.byref(sink),
                                  ctypes.byref(corners)), 2)


class TextureTests(NativeBuild):
    def decode(self, name, data):
        path = self.tmp/name
        path.write_bytes(data)
        result = run('image', path, '--out', self.tmp/'image.raw', check=False)
        if result.returncode:
            return None
        raw = (self.tmp/'image.raw').read_bytes()
        width, height = struct.unpack('<II', raw[:8])
        return width, height, raw[8:]

    def test_wrappers_and_formats_match_pillow(self):
        from PIL import Image
        import io
        cases = []
        for seed, kwargs in enumerate([{}, {'rle': True}, {'top_left': True}, {'alpha': False},
                                       {'alpha': False, 'rle': True, 'top_left': True}]):
            payload = nf.tga(13, 7, seed, **kwargs)
            cases += [('a.ozt', nf.ozt(payload), payload), ('b.OZT', nf.ozt(payload, zero_field=True), payload),
                      ('c.tga', payload, payload)]
        bitmap = nf.bmp24(9, 5, 3)
        cases += [('d.ozb', nf.ozb(bitmap), bitmap), ('e.bmp', bitmap, bitmap)]
        for name, data, payload in cases:
            with self.subTest(name=name):
                decoded = self.decode(name, data)
                self.assertIsNotNone(decoded)
                with Image.open(io.BytesIO(payload)) as image:
                    expected = image.convert('RGBA')
                    self.assertEqual(decoded[:2], expected.size)
                    self.assertEqual(decoded[2], expected.tobytes())
        info = json.loads(run('image', self.tmp/'a.ozt').stdout)
        if info['jpeg']:
            buffer = io.BytesIO()
            Image.new('RGB', (16, 8), (200, 30, 90)).save(buffer, format='JPEG', quality=95)
            decoded = self.decode('f.ozj', b'\0'*24+buffer.getvalue())
            self.assertEqual(decoded[:2], (16, 8))
            self.assertLess(max(abs(decoded[2][k]-(200, 30, 90, 255)[k % 4]) for k in range(len(decoded[2]))), 8)

    def test_unrecognized_wrappers_rejected(self):
        payload = nf.tga(4, 4, 1)
        self.assertIsNone(self.decode('x.ozt', payload[:4]+b'\1\2\3\4'+payload[4:]))
        self.assertIsNone(self.decode('x.ozb', nf.bmp24(4, 4, 1)))
        self.assertIsNone(self.decode('x.ozj', b'\0'*64))
        self.assertIsNone(self.decode('x.ozt', nf.ozt(payload)[:30]))


class RenderTests(NativeBuild):
    SETTINGS = {
        'default': [],
        'nearest-yaw': ['--nearest', '--yaw', '35', '--pitch', '-10', '--action', '1', '--frame', '2.5'],
        'blend-alpha': ['--alpha', '0.6', '--flags', '0x40000', '--background', '0', '0', '0'],
        'additive-env': ['--mode', '0x1000', '--flags', '0x40', '--uv-offset', '0.1', '0.2'],
        'alpha-test-unlit': ['--alpha-test', '--lighting', '0', '--color', '0.8', '0.6', '1.0', '--cull', '0'],
    }

    def model(self):
        directory = self.tmp/'render'
        directory.mkdir(exist_ok=True)
        return nf.write_textured_model(directory, 11, four_corner=True)

    def render(self, path, name, args, size=(160, 120)):
        out = self.tmp/f'{name}.png'
        result = json.loads(run('render', path, '--out', out, '--width', size[0], '--height', size[1], *args).stdout)
        return result, out

    def test_software_render_hashes(self):
        path = self.model()
        observed = {}
        for name, args in self.SETTINGS.items():
            with self.subTest(name=name):
                result, out = self.render(path, name, args)
                width, height, pixels = png_pixels(out)
                self.assertEqual((width, height), (160, 120))
                self.assertEqual(hashlib.sha256(pixels).hexdigest(), result['sha256'])
                self.assertEqual(result['textures_missing'], 0)
                self.assertEqual(result['refused'], 0)
                self.assertGreater(result['fragments'], 500)
                self.assertEqual(self.render(path, name+'-again', args)[0]['sha256'], result['sha256'])
                observed[name] = result['sha256']
        self.assertEqual(len(set(observed.values())), len(observed))
        self.assertEqual(observed, RENDER_HASHES, json.dumps(observed, indent=4))

    def test_envelopes_render_identically(self):
        directory = self.tmp/'env'
        directory.mkdir(exist_ok=True)
        hashes = {json.loads(run('render', nf.write_textured_model(directory, 12, version=v), '--width', 64,
                                 '--height', 48).stdout)['sha256'] for v in (10, 12, 15)}
        self.assertEqual(len(hashes), 1)


@unittest.skipUnless(shutil.which('sdl2-config'), 'windowed viewer needs SDL2 (sdl2-config)')
class ViewerTests(NativeBuild):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        subprocess.run(['make', '-C', str(NATIVE), 'viewer'], check=True, capture_output=True)

    def test_headless_gl_agrees_with_the_software_renderer(self):
        directory = self.tmp/'gl'
        directory.mkdir(exist_ok=True)
        path = nf.write_textured_model(directory, 13)
        result = subprocess.run([str(VIEWER), '--headless', '--backend', 'gl', '--compare', '--width', '160',
                                 '--height', '120', '--out', str(self.tmp/'gl.png'), str(path)],
                                capture_output=True, text=True)
        if result.returncode and 'headless GL' in result.stderr:
            self.skipTest('no offscreen OpenGL context: '+result.stderr.strip())
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        soft = json.loads(run('render', path, '--width', 160, '--height', 120).stdout)
        self.assertEqual(report['other_sha256'], soft['sha256'])
        self.assertLess(report['pixels_over_8'], 160*120//100)   # under 1% of pixels differ by more than 8/255
        self.assertLess(report['mean_channel_diff'], 1.0)


@unittest.skipUnless(PRIVATE, 'Installed-model checks are opt-in (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT)')
class PrivateInstalledTests(NativeBuild):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        root = os.environ.get('MU_GAME_ROOT')
        if not root:
            raise AssertionError('Requested integration needs MU_GAME_ROOT')
        data = Path(root)/'Data'
        cls.data = data if data.is_dir() else Path(root)

    def models(self):
        by_version = {}
        for path in sorted(self.data.rglob('*')):
            if path.suffix.lower() != '.bmd' or not path.is_file():
                continue
            with path.open('rb') as handle:
                head = handle.read(4)
            if head[:3] == b'BMD':
                by_version.setdefault(head[3], []).append(path)
        return by_version

    def test_installed_golden_sample_per_version(self):
        ref = reference.Reference()
        per_version = int(os.environ.get('MU_NATIVE_GOLDEN_PER_VERSION', '12'))
        max_vertices = int(os.environ.get('MU_NATIVE_GOLDEN_MAX_VERTICES', '3000'))
        totals = {}
        for version, paths in sorted(self.models().items()):
            if version not in (10, 12, 14, 15):
                continue
            compared = vertices = 0
            for path in paths[::max(1, len(paths)//(per_version*3))] if per_version*3 < len(paths) else paths:
                raw = path.read_bytes()
                try:
                    model, _ = reference.decode(raw)
                except Exception:
                    continue
                if not model['meshes'] or not model['actions'] or sum(len(m['vertices']) for m in model['meshes']) > max_vertices:
                    continue
                keys = [a['keys'] for a in model['actions']]
                action = max(range(len(keys)), key=lambda a: keys[a])
                state = {'action': action, 'frame': keys[action]*0.5+0.25, 'prior_action': 0,
                         'prior_frame': 0.0, 'ticks': 3, 'speed': 0.37}
                with self.subTest(path=str(path.relative_to(self.data))):
                    expected = ref.outputs(raw, state, label=path.name)
                    if expected is None:
                        continue
                    run('dump', path, '--out', self.tmp/'p.bin', *reference.cli_arguments(state))
                    observed = reference.read_dump(self.tmp/'p.bin')
                    self.assertEqual(observed['bones'], expected['bones'])
                    for mine, theirs in zip(observed['meshes'], expected['meshes']):
                        for key in ('vertices', 'normals', 'lights', 'secondary'):
                            self.assertEqual(mine[key], theirs[key], key)
                        vertices += len(mine['vertices'])//12
                    compared += 1
                if compared >= per_version:
                    break
            totals[version] = (compared, vertices)
            self.assertGreaterEqual(compared, min(per_version, 5), version)
        print('installed golden sample (models, vertices) per version:', totals)
        self.assertEqual(set(totals), {10, 12, 14, 15})

    def test_corpus_scan(self):
        result = json.loads(run('scan', self.data).stdout)
        for version, files in (('10', 701), ('12', 180), ('14', 216)):
            self.assertEqual(result[version]['files'], files)
            self.assertEqual(result[version]['animated'], files)
        self.assertEqual(result['15']['files'], 11583)
        self.assertEqual(result['15']['rejected'], 17)
        self.assertEqual(result['15']['animated'], 11566)
        self.assertEqual(sum(result[v]['refused_meshes'] + result[v]['init_failed'] + result[v]['anim_failed']
                             for v in result), 0)
        self.assertEqual(sum(result[v]['vertices'] for v in ('12', '14', '15')), 3814006)

    def test_installed_textures_match_pillow(self):
        sys.path.insert(0, str(ROOT/'asset-recovery'))
        import recover_images
        checked = 0
        for path in sorted((self.data/'Monster').iterdir())[:400]:
            if path.suffix.lower() not in ('.ozj', '.ozt', '.ozb'):
                continue
            image, _ = recover_images.decode(path)
            run('image', path, '--out', self.tmp/'t.raw')
            raw = (self.tmp/'t.raw').read_bytes()
            self.assertEqual(struct.unpack('<II', raw[:8]), image.size)
            self.assertEqual(raw[8:], image.convert('RGBA').tobytes(), path.name)
            checked += 1
        self.assertGreater(checked, 50)

    @unittest.skipUnless(VIEWER.exists() or shutil.which('sdl2-config'), 'needs the windowed viewer build')
    def test_installed_gl_and_software_renders_agree(self):
        subprocess.run(['make', '-C', str(NATIVE), 'viewer'], check=True, capture_output=True)
        for relative in ('Monster/Monster01.bmd', 'Monster/Monster05.bmd', 'NPC/Smith01.bmd'):
            path = self.data/relative
            if not path.exists():
                continue
            with self.subTest(model=relative):
                result = subprocess.run([str(VIEWER), '--headless', '--backend', 'gl', '--compare', '--width', '320',
                                         '--height', '240', '--frame', '2.5', str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(result.stdout)
                self.assertLess(report['pixels_over_8'], 320*240//200)


if __name__ == '__main__':
    unittest.main()
