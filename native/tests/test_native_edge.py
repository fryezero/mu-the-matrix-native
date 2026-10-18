"""Native viewer behaviour on values the strict reader rejects (MODEL-EDGE, issue #17).

Portable (synthetic data): the loader keeps every such value and lists it exactly as
model-recovery/bmd10.py's client_layout mode does; poses, transforms and corner streams
follow the client's unchecked indexing, with the client memory those indices reach
modelled as in a freshly loaded client (docs/research/model-edge.md):
  * a child of a dummy record composes the dummy's never-written (zero) bone slot;
  * a vertex/normal bone outside the skeleton reads a zero-filled span at
    0x06fce398 + bone*0x30;
  * a corner index past its array reads a zero entry (colour, normal table, vertex) or,
    for the heap texcoord, a labelled zero substitute.
Private (MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT): the 17 installed files load,
animate and draw without a refused mesh. The bit-for-bit comparison of their corner
streams with the client's executed mesh draw is in scripts/validate_model_edge.py.
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
import reference  # noqa: E402

TOOL = NATIVE/'build/mu-render'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
EDGE_FILES = ('Data/Item/dark_05.bmd', 'Data/Item/medusa.bmd', 'Data/Item/medusaUp.bmd',
              'Data/Item/rockinghorsepet_evol.bmd', 'Data/Item/scorpio.bmd', 'Data/Item/scorpioUp.bmd',
              'Data/Item/selupan.bmd', 'Data/Item/selupanUp.bmd', 'Data/Monster/Monster151.bmd',
              'Data/Monster/Monster211.bmd', 'Data/Monster/Monster214.bmd', 'Data/Monster/Monster215.bmd',
              'Data/Monster/Monster415.bmd', 'Data/Monster/Monster444.bmd', 'Data/Monster/monster223.bmd',
              'Data/Object134/Object13.bmd', 'Data/Skill/CW_Bow_Skill.bmd')


def run(*args, check=True):
    result = subprocess.run([str(TOOL), *[str(a) for a in args]], capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(result.stderr)
    return result


# mu-render corners writes the literal GL stream: (op, four words) per call.
GL_BEGIN, GL_END = 1, 2
CORNER_KINDS = {3: 1, 5: 2, 6: 3, 7: 4}   # glTexCoord2f, glColor3fv, glColor4f, glVertex3fv


def corner_records(path):
    """(glBegin block, kind, four floats) for every corner call inside glBegin/glEnd:
    kind 1 texcoord, 2 colour3, 3 colour4, 4 vertex. Block n is the n-th mesh drawn."""
    data = Path(path).read_bytes()
    out, block, inside = [], -1, False
    for offset in range(0, len(data), 20):
        op = struct.unpack_from('<I', data, offset)[0]
        if op == GL_BEGIN:
            block, inside = block + 1, True
        elif op == GL_END:
            inside = False
        elif inside and op in CORNER_KINDS:
            out.append((block, CORNER_KINDS[op]) + struct.unpack_from('<4f', data, offset + 4))
    return out


def edge_layout():
    """Synthetic layout with each kind of value the installed edge files contain."""
    layout = bytearray(nf.synthetic_layout(11, meshes=2, bones=7, actions=2, keys=(4, 3)))
    model = reference.decode(bytes(layout))[0]
    mesh = model['meshes'][0]
    vertices = mesh['source_offset']+10
    normals = vertices+16*len(mesh['vertices'])
    polygons = normals+20*len(mesh['normals'])+8*len(mesh['uvs'])
    struct.pack_into('<h', layout, vertices+16*2, -8888)    # vertex bone outside the skeleton
    struct.pack_into('<h', layout, normals+20*1, -1)        # normal bone -1
    struct.pack_into('<h', layout, polygons+64*2+10+2*1, 5223)    # active normal index past the array
    struct.pack_into('<h', layout, polygons+64*2+10+2*2, -29063)  # negative normal index
    struct.pack_into('<h', layout, polygons+64*2+18, 6949)        # texcoord index past the array
    bone4 = model['bones'][4]['source_offset']
    struct.pack_into('<h', layout, bone4+33, 3)             # parent: the dummy record 3
    return bytes(layout), model


class EdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        subprocess.run(['make', '-C', str(ROOT/'model-recovery')], check=True, capture_output=True)
        cls.directory = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls.directory.name)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def write(self, raw, name='edge.bmd'):
        path = self.tmp/name
        path.write_bytes(raw)
        return path

    def test_anomalies_match_the_python_client_layout(self):
        layout, _ = edge_layout()
        for label, raw in (('v10', layout), ('v15', nf.envelope_v15(layout)), ('v12', nf.envelope_v12(layout))):
            with self.subTest(envelope=label):
                with self.assertRaises(Exception):
                    reference.decode(raw)                   # the strict reader rejects it
                model = reference.decode(raw, client_layout=True)[0]
                info = json.loads(run('info', self.write(raw)).stdout)
                expected = sorted((x['kind'], None if x['offset'] is None else x['offset']-4, x['strict'])
                                  for x in model['client_semantics'])
                observed = sorted((x['kind'], x['offset'], x['strict']) for x in info['anomalies'])
                self.assertEqual(observed, expected)
                self.assertEqual(info['strict_anomalies'], sum(x['strict'] for x in model['client_semantics']))
                self.assertEqual(info['unresolved_bones'],
                                 [i for i, b in enumerate(model['bones']) if b.get('client_unresolved')])
                kinds = {x['kind'] for x in info['anomalies']}
                self.assertTrue({'vertex-bone', 'normal-bone', 'normal-index', 'uv-index', 'dummy-parent'} <= kinds)

    def test_pose_and_transform_follow_the_client_indexing(self):
        layout, model = edge_layout()
        path = self.write(layout)
        run('dump', path, '--out', self.tmp/'edge.dump')
        dump = reference.read_dump(self.tmp/'edge.dump')
        # Dummy slot 3 is never written; bone 4 composes it (zero), and so does its child 6.
        self.assertEqual(dump['bones'][3*0x30:4*0x30], bytes(0x30))
        for slot in (4, 6):   # concat(zero, local): every entry is +0 or -0
            self.assertEqual(struct.unpack_from('<12f', dump['bones'], slot*0x30), (0.0,)*12, slot)
        clean = self.write(nf.synthetic_layout(11, meshes=2, bones=7, actions=2, keys=(4, 3)), 'clean.bmd')
        run('dump', clean, '--out', self.tmp/'clean.dump')
        other = reference.read_dump(self.tmp/'clean.dump')
        for slot in (0, 1, 2, 5):
            self.assertEqual(dump['bones'][slot*0x30:(slot+1)*0x30], other['bones'][slot*0x30:(slot+1)*0x30], slot)
        mesh = dump['meshes'][0]
        # Vertex 2 (bone -8888): zero foreign matrix, so its position is the translation (0) plus origin (0).
        self.assertEqual(struct.unpack_from('<3f', mesh['vertices'], 24), (0.0, 0.0, 0.0))
        # Normal 1 (bone -1): rotated to zero, so its light is max(minimum, ambient).
        self.assertEqual([abs(x) for x in struct.unpack_from('<3f', mesh['normals'], 12)], [0.0, 0.0, 0.0])
        self.assertAlmostEqual(struct.unpack_from('<f', mesh['lights'], 4)[0], 0.4, places=6)

    def test_corner_stream_draws_out_of_range_corners(self):
        layout, model = edge_layout()
        path = self.write(layout)
        result = json.loads(run('corners', path, '--out', self.tmp/'edge.ops').stdout)
        self.assertEqual(result['refused'], 0)
        self.assertEqual(result['corners'], sum(3*len(m['polygons']) for m in model['meshes']))
        records = [r for r in corner_records(self.tmp/'edge.ops') if r[0] == 0 and r[1] in (1, 2, 3, 4)]
        # Mesh 0, triangle 2: texcoord, colour, vertex per corner.
        corner0, corner1, corner2 = records[2*3*3:2*3*3+3], records[2*3*3+3:2*3*3+6], records[2*3*3+6:2*3*3+9]
        self.assertEqual(corner0[0][1:4], (1, 0.0, 0.0))        # redirected texcoord: labelled zero substitute
        self.assertEqual(corner1[1][1:5], (2, 0.0, 0.0, 0.0))   # colour of normal 5223: never-written entry
        self.assertEqual(corner2[1][1:5], (2, 0.0, 0.0, 0.0))   # colour of normal -29063: zero normal buffer
        clean = self.write(nf.synthetic_layout(11, meshes=2, bones=7, actions=2, keys=(4, 3)), 'clean.bmd')
        run('corners', clean, '--out', self.tmp/'clean.ops')
        reference_records = [r for r in corner_records(self.tmp/'clean.ops') if r[1] in (1, 2, 3, 4)]
        self.assertEqual(len(reference_records), len([r for r in corner_records(self.tmp/'edge.ops')
                                                      if r[1] in (1, 2, 3, 4)]))

    def test_structural_failures_still_reject(self):
        layout, _ = edge_layout()
        for size in (40, 100, len(layout)-30):
            with self.subTest(size=size):
                self.assertNotEqual(run('info', self.write(layout[:size]), check=False).returncode, 0)

    @unittest.skipUnless(PRIVATE and os.environ.get('MU_GAME_ROOT'), 'needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
    def test_installed_edge_files_load_animate_and_draw(self):
        root = Path(os.environ['MU_GAME_ROOT'])
        for relative in EDGE_FILES:
            with self.subTest(path=relative):
                info = json.loads(run('info', root/relative).stdout)
                self.assertGreater(info['strict_anomalies'], 0)
                result = json.loads(run('corners', root/relative, '--out', self.tmp/'installed.ops').stdout)
                self.assertEqual(result['refused'], 0)
                self.assertEqual(result['meshes'], info['meshes'])


if __name__ == '__main__':
    unittest.main()
