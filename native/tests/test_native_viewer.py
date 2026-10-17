"""Native viewer (NATIVE-VIEW-001) checks.

Portable (synthetic data only, run in CI on macOS and Linux):
  * loader agreement with the Python readers (v10/v12/v14/v15, malformed input);
  * golden data: `mu-render dump` equals the reconstructed libraries and the
    validators' pure-Python models byte for byte, through independently built
    client memory (native/tests/reference.py);
  * mesh draw: the GL call streams of the port on the synthetic cases equal
    pinned digests of the client's own mesh draw 0x012b8d1d / body 0x012bb35a
    executed under Unicorn (scripts/validate_meshdraw.py, which recomputes the
    same digests from the client; docs/research/client-meshdraw-exec.md), the
    texture-name sub-object records, refusal and fault conventions;
  * textures: OZT/OZB/TGA/BMP decoding against Pillow;
  * renders: software-rasterizer SHA-256 regression hashes and PNG round trip;
  * the windowed viewer builds and its headless GL output agrees with the
    software renderer (macOS with SDL2; explicit skip otherwise).
Private (MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT): installed-model golden
sample per version, the full corpus scan, texture decoding against Pillow,
GL/software render agreement, and the mesh-draw execution harness against the
pinned restored client text (synthetic, mutated and installed cases). Renders of installed assets stay in a temporary
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
import reference  # noqa: E402
sys.path.insert(0, str(ROOT/'scripts'))
import validate_meshdraw as vm  # noqa: E402  (case format and pinned cases; Unicorn only when executed)

TOOL = NATIVE/'build/mu-render'
VIEWER = NATIVE/'build/mu-viewer'
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'

# Software-rasterizer regression hashes (raw RGBA8 pixels) for the synthetic
# textured model; see RenderTests.
RENDER_HASHES = {
    'default': '2a2a4d0abad6e80f8c4b339a073e1f2637c7d4cc4ecc25dd5995f38d994f3e3f',
    'linear-yaw': 'a65ccc386b0427b91d193102a6797148eab54f4a94cd3cca0e1c30f07948878c',
    'blend-alpha': '0c9389141ba0cffed2516ba25363b51e9bcf23e2d0a73dc4ed28ec3e618f0211',
    'additive-env': 'a789b0d3a6ad9effd7ad80b3ad6853b217269211dea44497020400e25f5e8444',
    'alpha-test-unlit': '64db42038ad6bce745f191cda8b705303bd808d1ea01ee5b43a77fa32f2bc67b',
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
        self.assertEqual(len(observed['meshes']), len(expected['meshes']))   # zip() alone would hide a short dump
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


# Digests of the client's GL call streams for the pinned synthetic cases
# (validate_meshdraw.pinned_cases): one SHA-256 over "label digest" lines.
# validate_meshdraw.py recomputes both from the client's instructions under
# Unicorn (report "pinned"); the private test below ties them together.
CLIENT_CORNERS_GROUP = '9d9cf95c32ad48c51ad25b749e5f33841c87db9c58dc1deded05d5997d8ccc00'   # 207 viewer cases, `mu-render corners`
CLIENT_REPLAY_GROUP = '86f3593ad959e835e18255b0518c69efccd395c2140ae11a4953a80ffa4d901c'     # 40 mutated cases, `mu-render replay` (with fault/cache/colour records)
CLIENT_STREAMS = {   # a few individual corners digests, for diagnosis
    's8f2': 'dc5d71bb1c6eb7b7328c9a2fb20a5bc84e0003f821caea7e61ccaffbf7461881',      # body flags 2 (dominant)
    's9f1000': 'da78fcad44feb7ed541c82f158a76123b2d711b7b3fbbac82c35fd943d92e67d',   # v15, environment 0x1000
    's10f2': 'aff2100d1f921f453f77978d9ccdfa4ca816540a61f3a17d0336b5d0703f8de3',     # sub-object texture names
    's8f400': '026e33aca7b766d42679c415c9c74990b26e2c0b7dca14b7eb2a9f7cf8aa797e',    # 0x400 wave (client sin)
    's10f8000': '2664e8346386a097ed6c66ffa3b30d0b952b7bd41b0c9523e1d2b5d33339ea74',  # 0x8000: fault at texel read
}


def stream(path):
    return vm.read_stream(Path(path).read_bytes())


class MeshDrawTests(NativeBuild):
    def test_streams_equal_the_client_digests(self):
        corners, replays = [], []
        for label, case_bytes, recorded in vm.pinned_cases(self.tmp):
            if recorded is not None:
                corners.append((label, vm.stream_digest(recorded)))
            else:
                native, _ = vm.replay(case_bytes, self.tmp)
                replays.append((label, vm.stream_digest(native)))
        self.assertEqual((len(corners), len(replays)), (207, vm.PINNED_MUTATIONS))
        observed = dict(corners)
        for label, digest in CLIENT_STREAMS.items():
            self.assertEqual(observed[label], digest, label)
        self.assertEqual(vm.group_digest(corners), CLIENT_CORNERS_GROUP)
        self.assertEqual(vm.group_digest(replays), CLIENT_REPLAY_GROUP)

    def test_digest_detects_a_changed_input(self):
        path = vm.synthetic_models(self.tmp)[0][1]
        a = vm.corners_case(path, vm.SYNTHETIC_BASE+['--flags', '0x1000', '--client-time', '100'], self.tmp, 'a')[1]
        b = vm.corners_case(path, vm.SYNTHETIC_BASE+['--flags', '0x1000', '--client-time', '101'], self.tmp, 'b')[1]
        self.assertNotEqual(vm.stream_digest(a), vm.stream_digest(b))

    def test_texture_name_records(self):
        library = ctypes.CDLL(str(NATIVE/f'build/libmumeshdraw.{SUFFIX}'))
        function = library.mu_meshdraw_sub_from_name
        function.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        function.restype = ctypes.c_int
        # (name, record or None); every row equals the client's parser 0x01185111
        # executed under Unicorn (validate_meshdraw.py synthetic_names).
        table = [
            (b'skin.jpg', None), (b'x_R.jpg', b'\1\0\0\0\0'), (b'x_RHSN.jpg', b'\1\1\1\1\0'),
            (b'x_RHSNR.jpg', b'\1\1\1\1\0'), (b'x_HX.jpg', None), (b'x_XR.jpg', None), (b'x_.jpg', None),
            (b'x_R_S.jpg', None), (b'a_b_N.tga', None), (b'wizard_gloves_02.jpg', None),
            (b'master10_center.jpg', b'\0\1\0\0\0'), (b'lightning_4sq.jpg', b'\0\1\0\0\0'),
            (b'fire_sq.jpg', b'\0\1\0\0\0'), (b's195.tga', b'\0\1\0\0\0'), (b's195.TGA', None),
            (b'mu_rgb_lights.jpg', b'\1\0\0\0\0'), (b'x_DC.jpg', None), (b'q'*32, None),
            (b'q'*31+b'_', b'\1\1\1\1\0'),   # unterminated: the scan runs into "RHSN" on the client's stack
        ]
        for name, expected in table:
            with self.subTest(name=name):
                record = ctypes.create_string_buffer(5)
                has = function(name.ljust(32, b'\0')[:32], record)
                self.assertEqual(has, int(expected is not None))
                if expected is not None:
                    self.assertEqual(record.raw, expected)

    def test_sub_object_names_hide_and_select_meshes(self):
        begins = {}
        for label, names in (('plain', None), ('named', ['a_R.tga', 'b.tga', 'c_H.tga'])):
            directory = self.tmp/label
            directory.mkdir(exist_ok=True)
            path = nf.write_textured_model(directory, 14, four_corner=True, names=names)
            run('corners', path, '--out', self.tmp/f'{label}.ops', '--uv-offset', '0.5', '0.25')
            begins[label] = [r for r in stream(self.tmp/f'{label}.ops') if r[0] in (1, 3)]
        self.assertEqual(sum(r[0] == 1 for r in begins['plain']), 3)
        self.assertEqual(sum(r[0] == 1 for r in begins['named']), 2)   # 'H': the body skips mesh 2
        # 'R': the body passes the mesh as select, so mesh 0 gets the uv offset.
        self.assertNotEqual(begins['plain'][1], begins['named'][1])

    def test_mode_8000_faults_where_the_client_reads_freed_pixels(self):
        path = nf.write_textured_model(self.tmp, 15, four_corner=True)
        report = json.loads(run('corners', path, '--out', self.tmp/'f.ops', '--flags', '0x8000').stdout)
        self.assertEqual((report['faulted'], report['refused']), (1, 0))
        ops = [r[0] for r in stream(self.tmp/'f.ops')]
        self.assertEqual(ops[-1], 1)                     # stopped after glBegin, at the first texel read
        self.assertNotIn(14, ops)                        # no glPopMatrix: the client would have crashed

    def test_out_of_range_index_refused_before_any_call(self):
        path = nf.write_textured_model(self.tmp, 16, four_corner=True)
        case_bytes = vm.corners_case(path, [], self.tmp, 'bad')[0]
        case = vm.read_case(case_bytes)
        mesh = case['model']['meshes'][1]
        tri = bytearray(mesh['tri'])
        struct.pack_into('<h', tri, 2, mesh['vertices'])     # corner 0 of triangle 0 past the vertex count
        mesh['tri'] = bytes(tri)
        native, _ = vm.replay(vm.write_case(case), self.tmp)
        good, _ = vm.replay(case_bytes, self.tmp)
        self.assertEqual(sum(r[0] == 1 for r in native), sum(r[0] == 1 for r in good)-1)


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
        # An image ID longer than the file must be rejected, not read past the buffer
        # (uncompressed and RLE, plain and wrapped).
        for rle in (False, True):
            header = bytearray(nf.tga(1, 1, 1, rle=rle)[:18])
            header[0] = 255
            with self.subTest(rle=rle):
                self.assertIsNone(self.decode('id.tga', bytes(header)))
                self.assertIsNone(self.decode('id.ozt', nf.ozt(bytes(header)+b'\0'*4)))


class RenderTests(NativeBuild):
    SETTINGS = {
        'default': [],
        'linear-yaw': ['--linear', '--yaw', '35', '--pitch', '-10', '--action', '1', '--frame', '2.5'],
        'blend-alpha': ['--alpha', '0.6', '--flags', '0x40002', '--background', '0', '0', '0'],
        'additive-env': ['--flags', '0x1040', '--client-time', '2500', '--uv-offset', '0.1', '0.2'],
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
                    self.assertEqual(len(observed['meshes']), len(expected['meshes']))
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

    def test_private_client_mesh_draw_execution(self):
        """The client's mesh draw, body, texture-name parser and math wrappers
        executed under Unicorn against the port (scripts/validate_meshdraw.py)."""
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        flag = Path(os.environ.get('MU_TRIG_FLAG', ROOT/'evidence/trig-state-15/captures/late/math-dispatch-flag.bin'))
        feature = Path(os.environ.get('MU_MATH_DATA', ROOT/'evidence/x86-math-capture-09'))/'cpu-features.bin'
        report = self.tmp/'meshdraw.json'
        subprocess.run([sys.executable, str(ROOT/'scripts/validate_meshdraw.py'), '--text', str(text), '--data', str(data),
                        '--flag', str(flag), '--feature', str(feature), '--game-root', os.environ['MU_GAME_ROOT'],
                        '--per-folder', os.environ.get('MU_MESHDRAW_PER_FOLDER', '3'), '--mutations', '300',
                        '--math-sweep', '20000', '--output', str(report)], check=True, capture_output=True)
        result = json.loads(report.read_text())
        synthetic, installed = result['synthetic'], result['installed']
        self.assertEqual(synthetic['viewer_matches'], synthetic['viewer_cases'])
        self.assertEqual(synthetic['mutated_matches'], synthetic['mutated_cases'])
        self.assertGreaterEqual(synthetic['viewer_cases'], 207)
        self.assertEqual(installed['matches'], installed['cases'])
        self.assertGreater(installed['cases'], 250)
        self.assertEqual(result['uncovered'], [])
        self.assertTrue(all(result['negative_controls'].values()))
        for key in ('names_synthetic', 'names_installed'):
            self.assertEqual(result[key]['matches'], result[key]['names'], key)
        self.assertGreater(result['names_installed']['names'], 1000)
        for name, entry in result['math_sweep'].items():
            self.assertEqual(entry['binary32_differences'], 0, name)
        self.assertEqual(result['x87_transcendentals_in_draw_cases'], {})
        # The CI pins above are the client's own streams.
        pinned = result['pinned']
        self.assertEqual(pinned['matches'], pinned['cases'])
        self.assertEqual(pinned['corners_group'], CLIENT_CORNERS_GROUP)
        self.assertEqual(pinned['replay_group'], CLIENT_REPLAY_GROUP)
        self.assertEqual({k: v for k, v in pinned['corners'] if k in CLIENT_STREAMS}, CLIENT_STREAMS)


if __name__ == '__main__':
    unittest.main()
