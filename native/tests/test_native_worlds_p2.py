"""Kanturu Underground/Ignis Volcano creation, steps, visuals and refusals in the production host."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
NATIVE = Path(__file__).resolve().parents[1]


def bmd(bones=5, actions=4, keys=2):
    # A bone chain, `actions` actions of `keys` keys each, no meshes.
    chunks = [b'BMD\x0a', b'worlds-p2'.ljust(32, b'\0'), struct.pack('<HHH', 0, bones, actions)]
    chunks += [struct.pack('<hB', keys, 0) for _ in range(actions)]
    for b in range(bones):
        chunks.append(b'\0' + f'bone{b}'.encode().ljust(32, b'\0') + struct.pack('<h', b - 1))
        for _ in range(actions):
            chunks.append(struct.pack(f'<{3 * keys}f', *([0, 0, 10] * keys)) + bytes(12 * keys))
    return b''.join(chunks)


class WorldsP2Host(unittest.TestCase):
    def test_creation_steps_visuals_and_refusals(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/worlds-p2-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            model = Path(td) / 'p2.bmd'
            model.write_bytes(bmd())
            subprocess.run([str(NATIVE / 'build/worlds-p2-host'), str(model)], check=True)


if __name__ == '__main__':
    unittest.main()
