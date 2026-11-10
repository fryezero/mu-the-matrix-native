"""Classless Kanturu and Blood Castle visuals through the production object runtime."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
NATIVE = Path(__file__).resolve().parents[1]


def synthetic_bmd():
    out = [b'BMD\x0a', b'inner-demo'.ljust(32, b'\0'), struct.pack('<HHH', 4, 7, 1)]
    for k in range(4):
        out.append(struct.pack('<5h', 3, 3, 1, 1, k))
        for p in ((0, 0, 0), (10, 0, 0), (0, 10, 0)):
            out.append(struct.pack('<hh3f', 0, 0, *p))
        for n in ((0, 0, 1), (0, 1, 0), (1, 0, 0)):
            out.append(struct.pack('<hh3fhh', 0, 0, *n, 0, 0))
        out.append(struct.pack('<2f', 0.5, 0.5))
        face = bytearray(64); face[0] = 3
        struct.pack_into('<3h', face, 2, 0, 1, 2)
        struct.pack_into('<3h', face, 10, 0, 1, 2)
        out.extend([bytes(face), b'tex.jpg'.ljust(32, b'\0')])
    out.append(struct.pack('<hB', 2, 0))
    for k in range(7):
        name = b'light' if k == 0 else ('light%02d' % k).encode()
        out.append(b'\0' + name.ljust(32, b'\0') + struct.pack('<h', -1 if k == 0 else 0))
        out.append(struct.pack('<6f', k * 2, 2, 3, k * 2 + 4, 2, 3) + bytes(24))
    return b''.join(out)


class WorldsInnerHost(unittest.TestCase):
    def test_emitters_meshes_and_refusals(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/worlds-inner-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            model = Path(td) / 'inner.bmd'; model.write_bytes(synthetic_bmd())
            run = subprocess.run([str(NATIVE / 'build/worlds-inner-host'), str(model)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == '__main__':
    unittest.main()
