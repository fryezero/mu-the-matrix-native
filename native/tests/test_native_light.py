"""Model lighting inputs of the native scenes (NATIVE-LIGHT-001) checks.

Portable (synthetic data only):
  * static objects (`mu-terrain render --objects ... --object-steps N --light-report 1`): RenderObject's pose
    puts the body scale into the bones (Animation translate 1, Transform translate 0), the light vector is
    (1.3, 0, 2) (the client's light-override byte 0x01cf1048 = 1) and the Transform light arguments are 0.4 and
    the record's +0x30/+0x34: a one-bone model with axis normals gives exactly
    max(0.2, 0.4 + 0.8 * scale * dot(n, (1.3, 0, 2))) per normal;
  * demo-placed monsters and NPCs (`mu-walk --placement`): the colour is the frame light at the actor plus the
    character object light 0.2, with the client's light vector.
The live evidence (reads of our own running client) and the comparisons with window screenshots are in
docs/research/client-model-light.md; they need private data and stay local.
"""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
import native_fixtures as nf  # noqa: E402
from test_native_terrain import v12_encrypt  # noqa: E402
from test_native_world import write_open_world  # noqa: E402
from test_native_objects import obj_plain  # noqa: E402
from test_native_world2 import write_life  # noqa: E402

TERRAIN = NATIVE/'build/mu-terrain'
WALK = NATIVE/'build/mu-walk'
NORMALS = [(0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0)]


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def axis_model(texture='light.tga'):
    """One mesh on one bone (identity key): three vertices, the four axis normals of NORMALS, one triangle."""
    chunks = [b'BMD\x0a', nf.name32('axis.smd'), struct.pack('<HHH', 1, 1, 1)]
    chunks.append(struct.pack('<hhhhh', 3, len(NORMALS), 3, 1, 0))
    for v in ((0.0, 0.0, 0.0), (50.0, 0.0, 0.0), (0.0, 50.0, 0.0)):
        chunks.append(struct.pack('<hhfff', 0, 0, *v))
    for i, n in enumerate(NORMALS):
        chunks.append(struct.pack('<hhfffhh', 0, 0, *n, i % 3, 0))
    for uv in ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)):
        chunks.append(struct.pack('<ff', *uv))
    face = bytearray(64)
    face[0] = 3
    struct.pack_into('<4h', face, 2, 0, 1, 2, -1)
    struct.pack_into('<4h', face, 10, 0, 1, 2, -1)
    struct.pack_into('<4h', face, 18, 0, 1, 2, -1)
    chunks.append(bytes(face))
    chunks.append(nf.name32(texture))
    chunks.append(struct.pack('<hB', 1, 0))                               # one action, one key, not locked
    chunks.append(b'\x00' + nf.name32('root') + struct.pack('<h', -1))    # bone 0: position and rotation key
    chunks.append(struct.pack('<3f', 0.0, 0.0, 0.0))
    chunks.append(struct.pack('<3f', 0.0, 0.0, 0.0))
    return b''.join(chunks)


def expected_lights(scale, scale_argument=0.8, minimum=0.2, light=(1.3, 0.0, 2.0)):
    out = []
    for n in NORMALS:
        dot = f32(f32(f32(scale * n[0]) * light[0]) + f32(f32(scale * n[1]) * light[1]))
        dot = f32(dot + f32(f32(scale * n[2]) * light[2]))
        value = f32(f32(dot * scale_argument) + 0.4)
        out.append(max(minimum, value))
    return out


class ObjectLightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)

    def test_static_objects_take_the_client_pose_and_light_vector(self):
        with tempfile.TemporaryDirectory() as root:
            write_open_world(root)
            models = Path(root)/'Data'/'Object1'
            models.mkdir(parents=True, exist_ok=True)
            (models/'House01.bmd').write_bytes(axis_model())
            (models/'light.OZT').write_bytes(nf.ozt(nf.tga(8, 8, 3)))
            scales = (1.0, 0.5, 3.0)
            records = [(115, 12850.0 + 100.0 * i, 12850.0, 60.0, 0.0, s) for i, s in enumerate(scales)]
            (Path(root)/'Data'/'World1'/'EncTerrain1.obj').write_bytes(v12_encrypt(obj_plain(1, records)))
            result = subprocess.run([str(TERRAIN), 'render', root, '--world', '0', '--objects', 'installed',
                                     '--object-steps', '2', '--light-report', '1', '--target', '12950,12850',
                                     '--distance', '2000', '--width', '96', '--height', '64'],
                                    capture_output=True, text=True, check=True)
            rows = [json.loads(l) for l in result.stdout.splitlines() if l.startswith('{"object_light"')]
            self.assertEqual(sorted(r['object_light'] for r in rows), [0, 1, 2])
            for row in rows:
                scale = scales[row['object_light']]
                self.assertEqual((row['type'], row['pose_translate'], row['transform_translate'],
                                  row['light_override'], row['lighting']), (115, 1, 0, 1, 1))
                self.assertEqual((f32(row['ambient']), f32(row['light_scale']), f32(row['light_minimum'])),
                                 (f32(0.4), f32(0.8), f32(0.2)))
                self.assertAlmostEqual(row['scale'], scale, places=6)
                for got, want in zip(row['lights'][0], expected_lights(scale)):
                    self.assertAlmostEqual(got, want, delta=2e-6, msg=f'scale {scale}')
            # the old inputs (normals at unit length, light vector (0, -1.5, 0)) would give 1.6 for the -y normal
            self.assertAlmostEqual(next(r for r in rows if r['object_light'] == 2)['lights'][0][2], 0.4, places=6)


class ActorLightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)

    def test_monsters_and_npcs_take_the_frame_light_plus_the_object_light(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = write_open_world(Path(tmp)/'game')
            write_life(root)
            placement = Path(tmp)/'placement.txt'
            placement.write_text('actor 3 130 128 2 label spider\nactor 251 126 128 4 label smith\n')
            result = subprocess.run([str(WALK), '--game-root', str(root), '--headless', '--backend', 'soft',
                                     '--tile', '128,128', '--frames', '3', '--every', '0', '--placement',
                                     str(placement), '--quiet', '--no-audio'],
                                    capture_output=True, text=True, check=True)
            rows = [json.loads(l) for l in result.stdout.splitlines() if l.startswith('{"actor"')]
            self.assertEqual(len(rows), 2)
            expected = f32(f32(200 / 255) + f32(0.2))   # TerrainLight.OZB is a uniform 200
            for row in rows:
                self.assertEqual(row['light_override'], 1)
                for value in row['light']:
                    self.assertAlmostEqual(value, expected, delta=1e-5)


if __name__ == '__main__':
    unittest.main()
