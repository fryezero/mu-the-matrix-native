"""Checks for the authored plaintext model reader (client 0x012b3b50..0x012b4477) and the
bone box pass 0x012b47fd (MODEL-EDGE).

Portable: the authored C runs on synthetic payloads, including every kind of value the
strict reader rejects, and its records are checked field by field against an
independent walk of the stream. Private (MU_RECOVERY_INTEGRATION=1 with the pinned
captures and MU_GAME_ROOT): scripts/validate_model_edge.py executes the client's own
instructions on the 17 rejected v15 files, synthetic payloads and an installed sample.
"""
import ctypes
import importlib.util
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
ROOT = HERE.parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
ARENA, ARENA_BYTES = 0x40000000, 0x100000
STATE, STATE_BYTES = 0x07500000, 0x00500000   # box counts 0x075a9d58, min 0x078965e0, max 0x07896f40


def load_validator():
    spec = importlib.util.spec_from_file_location('validate_model_edge', ROOT/'scripts/validate_model_edge.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules['validate_model_edge'] = module
    spec.loader.exec_module(module)
    return module


class ModelReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        cls.v = load_validator()
        cls.library = ctypes.CDLL(str(HERE/f'libmodelreader.{SUFFIX}'))
        read = cls.library.mu_model_read_layout
        read.argtypes = [ctypes.POINTER(cls.v.Memory), ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_int32),
                         ctypes.POINTER(cls.v.Hooks), ctypes.c_void_p]
        read.restype = ctypes.c_int

    def read(self, payload, names=None):
        v = self.v
        arena = (ctypes.c_ubyte*ARENA_BYTES)()
        state = (ctypes.c_ubyte*STATE_BYTES)()
        images = (v.Image*2)(v.Image(ctypes.addressof(arena), ARENA, ARENA_BYTES),
                             v.Image(ctypes.addressof(state), STATE, STATE_BYTES))
        memory = v.Memory(images, 2)
        model, stream = ARENA+0x100, ARENA+0x1000
        ctypes.memmove(ctypes.addressof(arena)+stream-ARENA, payload, len(payload))
        cursor = [align(stream+len(payload)+0x100)]
        requests, released, parsed = [], [], []

        def allocate(context, request):
            requests.append(request)
            address = align(cursor[0]+16)
            cursor[0] = address+max(request, 1)
            ctypes.memset(ctypes.addressof(arena)+address-ARENA, 0xa5, max(request, 1))
            return address

        def name_flags(context, name, out):
            text = bytes(arena[name-ARENA:name-ARENA+32])
            parsed.append(text)
            flags = (names or {}).get(text.split(b'\0')[0], (0, b'\0'*5))
            for k in range(5):
                out[k] = flags[1][k]
            return flags[0]
        hooks = v.Hooks(v.ALLOCATE(allocate), v.RELEASE(lambda c, b: released.append(b)), v.NAME_FLAGS(name_flags),
                        None)
        offset = ctypes.c_int32(0)
        tables = (ctypes.c_uint32*3)(v.BOX_COUNTS, v.BOX_MIN, v.BOX_MAX)
        status = self.library.mu_model_read_layout(ctypes.byref(memory), model, stream, ctypes.byref(offset),
                                                   ctypes.byref(hooks), ctypes.addressof(tables))
        mem = {'arena': bytes(arena), 'state': bytes(state)}

        def at(address, size):
            if ARENA <= address < ARENA+ARENA_BYTES:
                return mem['arena'][address-ARENA:address-ARENA+size]
            return mem['state'][address-STATE:address-STATE+size]
        return {'status': status, 'offset': offset.value, 'at': at, 'model': model, 'stream': stream,
                'requests': requests, 'released': released, 'parsed': parsed}

    def check_records(self, payload, result):
        """Records against the independent stream walk (validate_model_edge.client_layout)."""
        v, at = self.v, result['at']
        layout = v.client_layout(payload)
        nm, nb, na = layout['counts']
        model = result['model']
        self.assertEqual(result['status'], 0)
        self.assertEqual(result['offset'], layout['end'])
        self.assertEqual(result['released'], [result['stream']])
        self.assertEqual(struct.unpack('<hhh', at(model+0x22, 6)), (nb, nm, na))
        self.assertEqual(at(model, 32), payload[:32])
        self.assertEqual(struct.unpack('<i', at(model+0x60, 4))[0], -1)
        self.assertEqual(at(model+0x94, 1), b'\xff')
        self.assertEqual(at(model+0xb6, 0x14), b'\xff'*0x14)
        meshes = struct.unpack('<I', at(model+0x28, 4))[0]
        for i, mesh in enumerate(layout['meshes']):
            record = at(meshes+0x20*i, 0x20)
            self.assertEqual(record[0], 0)
            self.assertEqual(struct.unpack_from('<5h', record, 2),
                             (mesh['texture'], mesh['nv'], mesh['nn'], mesh['nt'], mesh['nf']))
            vertices, normals, uvs, triangles = struct.unpack_from('<4I', record, 0xc)
            self.assertEqual(at(vertices, 16*mesh['nv']), payload[mesh['vertices']:mesh['vertices']+16*mesh['nv']])
            self.assertEqual(at(normals, 20*mesh['nn']), payload[mesh['normals']:mesh['normals']+20*mesh['nn']])
            self.assertEqual(at(uvs, 8*mesh['nt']), payload[mesh['uvs']:mesh['uvs']+8*mesh['nt']])
            for j in range(mesh['nf']):   # first 0x24 bytes of each 64-byte polygon, unchecked
                self.assertEqual(at(triangles+0x24*j, 0x24), payload[mesh['polygons']+64*j:mesh['polygons']+64*j+0x24])
        actions = struct.unpack('<I', at(model+0x30, 4))[0]
        for i, action in enumerate(layout['actions']):
            record = at(actions+16*i, 16)
            self.assertEqual((record[0], struct.unpack_from('<h', record, 8)[0], record[0xa]),
                             (0, action['keys'], action['lock']))
            if not action['lock']:
                self.assertEqual(struct.unpack_from('<I', record, 0xc)[0], 0)
        bones = struct.unpack('<I', at(model+0x2c, 4))[0]
        counts = {}
        for mesh in layout['meshes']:
            for j in range(mesh['nv']):
                node = struct.unpack_from('<h', payload, mesh['vertices']+16*j)[0]
                counts[node] = counts.get(node, 0)+1
        for i, bone in enumerate(layout['bones']):
            record = at(bones+0x8c*i, 0x8c)
            self.assertEqual(record[0x22], bone['dummy'])
            if not bone['dummy']:
                self.assertEqual(struct.unpack_from('<h', record, 0x20)[0], bone['parent'])   # raw parent
            self.assertEqual(record[0x28], int(counts.get(i, 0) != 0))
        # Out-of-range vertex bones count into the tables at base + node*2, unchecked.
        for node, count in counts.items():
            if not 0 <= node < nb:
                address = (v.BOX_COUNTS+2*node) & 0xffffffff
                if STATE <= address < STATE+STATE_BYTES:
                    self.assertEqual(struct.unpack('<H', at(address, 2))[0], count & 0xffff)
        return layout

    def test_synthetic_payloads_with_unsupported_values(self):
        generator = random.Random(0x12b47fd)
        foreign = 0
        for index in range(120):
            payload = self.v.synthetic_payload(generator, 'negative-model-counts' if index % 40 == 3 else 'mutated')
            with self.subTest(index=index):
                result = self.read(payload)
                layout = self.check_records(payload, result)
                foreign += any(not 0 <= struct.unpack_from('<h', payload, m['vertices']+16*j)[0] < len(layout['bones'])
                               for m in layout['meshes'] for j in range(m['nv']))
        self.assertGreater(foreign, 10)

    def test_negative_vertex_bone_writes_below_the_count_table(self):
        payload = bytearray(b'm'.ljust(32, b'\0')+struct.pack('<hhh', 1, 1, 0))
        payload += struct.pack('<5h', 2, 0, 0, 0, 0)
        payload += struct.pack('<hh3f', -8888, 0, 0.0, 0.0, 0.0)+struct.pack('<hh3f', 0, 0, 1.0, 2.0, 3.0)
        payload += b'tex.jpg'.ljust(32, b'\0')
        payload += b'\0'+b'root'.ljust(32, b'\0')+struct.pack('<h', -1)
        result = self.read(bytes(payload))
        self.check_records(bytes(payload), result)
        at = result['at']
        self.assertEqual(struct.unpack('<H', at(0x075a57e8, 2))[0], 1)       # 0x075a9d58 - 8888*2
        self.assertEqual(struct.unpack('<3f', at(0x0787c540, 12)), (0.0, 0.0, 0.0))   # zero min slot: no write
        self.assertEqual(struct.unpack('<3f', at(self.v.BOX_MIN, 12)), (1.0, 2.0, 3.0))   # 9999 > p: written
        self.assertEqual(struct.unpack('<3f', at(self.v.BOX_MAX, 12)), (1.0, 2.0, 3.0))   # p > -9999: written
        bones = struct.unpack('<I', at(result['model']+0x2c, 4))[0]
        corners = [struct.unpack_from('<3f', at(bones+0x2c, 96), 12*c) for c in range(8)]
        self.assertEqual(corners[0], (1.0, 2.0, 3.0))   # all from max
        self.assertEqual(corners[7], (1.0, 2.0, 3.0))   # all from min (one vertex)

    def test_sub_object_only_when_parser_returns_nonzero(self):
        payload = bytearray(b'm'.ljust(32, b'\0')+struct.pack('<hhh', 2, 0, 0))
        for name in (b'body_R.jpg', b'plain.jpg'):
            payload += struct.pack('<5h', 0, 0, 0, 0, 0)+name.ljust(32, b'\0')
        result = self.read(bytes(payload), {b'body_R.jpg': (1, b'\1\0\0\0\0')})
        self.check_records(bytes(payload), result)
        meshes = struct.unpack('<I', result['at'](result['model']+0x28, 4))[0]
        first = struct.unpack('<I', result['at'](meshes+0x1c, 4))[0]
        second = struct.unpack('<I', result['at'](meshes+0x20+0x1c, 4))[0]
        self.assertEqual(result['at'](first, 5), b'\1\0\0\0\0')
        self.assertEqual(second, 0)
        self.assertIn(5, result['requests'])
        self.assertEqual(len(result['parsed']), 2)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private client-instruction comparison is opt-in')
    def test_private_client_reader_pose_transform_and_draw(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        flag = Path(os.environ.get('MU_TRIG_FLAG', ROOT/'evidence/trig-state-15/captures/late/math-dispatch-flag.bin'))
        feature = Path(os.environ.get('MU_MATH_DATA', ROOT/'evidence/x86-math-capture-09'))/'cpu-features.bin'
        game_root = os.environ.get('MU_GAME_ROOT')
        self.assertTrue(game_root, 'Requested integration needs MU_GAME_ROOT for the 17 installed files')
        native = ROOT/'native/build/mu-render'
        subprocess.run(['make', '-C', str(ROOT/'native')], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)/'report.json'
            run = subprocess.run([sys.executable, str(ROOT/'scripts/validate_model_edge.py'), '--text', str(text),
                                  '--data', str(data), '--flag', str(flag), '--feature', str(feature),
                                  '--game-root', game_root, '--native', str(native), '--output', str(report)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout[-2000:]+run.stderr[-2000:])
            result = json.loads(report.read_text())
        summary = result['summary']
        self.assertEqual(result['failures'], [])
        self.assertEqual((summary['files'], summary['reader_matches'], summary['authored_reader_matches']), (17, 17, 17))
        for key in ('pose', 'transform', 'draw'):
            self.assertEqual(summary[f'{key}_matches'], summary[f'{key}_calls'], key)
        self.assertEqual(summary['geometry_state_dependent_files'], [])
        self.assertEqual(summary['synthetic_readers']['matches'], summary['synthetic_readers']['cases'])
        native_summary = summary['native_corner_streams']
        self.assertEqual(native_summary['matches'], native_summary['files'])
        self.assertGreaterEqual(native_summary['files'], 15)


def align(value, boundary=16):
    return (value+boundary-1) & -boundary


if __name__ == '__main__':
    unittest.main()
