"""RENDER-WORLDS-121: Test Area 121's custom slot (per-vertex light, bone particles) and Devias 0x67's action choice
in the production first pass, on a synthetic model."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
NATIVE = Path(__file__).resolve().parents[1]


def synthetic_bmd():
    """One mesh (three vertices and normals on bone 0, one texcoord, one triangle), two bones, one 2-key action."""
    out = [b'BMD\x0a', b'worlds121'.ljust(32, b'\0'), struct.pack('<HHH', 1, 2, 1)]
    out.append(struct.pack('<5h', 3, 3, 1, 1, 0))
    for p in ((0, 0, 0), (10, 0, 0), (0, 10, 0)):
        out.append(struct.pack('<hh3f', 0, 0, *p))
    for n in ((0, 0, 1), (0, 1, 0), (1, 0, 0)):
        out.append(struct.pack('<hh3fhh', 0, 0, *n, 0, 0))
    out.append(struct.pack('<2f', 0.5, 0.5))
    face = bytearray(64)
    face[0] = 3
    struct.pack_into('<3h', face, 2, 0, 1, 2)
    struct.pack_into('<3h', face, 10, 0, 1, 2)
    struct.pack_into('<3h', face, 18, 0, 0, 0)
    out.append(bytes(face))
    out.append(b'tex.jpg'.ljust(32, b'\0'))
    out.append(struct.pack('<hB', 2, 0))
    for name, parent in ((b'bone0', -1), (b'bone1', 0)):
        out.append(b'\0' + name.ljust(32, b'\0') + struct.pack('<h', parent))
        out.append(struct.pack('<6f', 0, 2, 3, 4, 2, 3) + bytes(24))
    return b''.join(out)


class Worlds121Host(unittest.TestCase):
    def test_light_particles_and_devias(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/worlds-121-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            model = Path(td) / 'w121.bmd'
            model.write_bytes(synthetic_bmd())
            run = subprocess.run([str(NATIVE / 'build/worlds-121-host'), str(model)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn('worlds-121-host ok', run.stdout)


if __name__ == '__main__':
    unittest.main()
