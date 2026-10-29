"""Twisted Karutan/Kardamahal/Swamp of Destruction creation, steps, visuals and refusals in the production host."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
NATIVE = Path(__file__).resolve().parents[1]
NAMES = {5: 'E002', 9: 'E005'}   # Kardamahal type 115 lights the named bones E002..E009 it finds


def bmd(bones=13, actions=2, keys=2):
    # A bone chain, `actions` actions of `keys` keys each, no meshes.
    chunks = [b'BMD\x0a', b'worlds-r2'.ljust(32, b'\0'), struct.pack('<HHH', 0, bones, actions)]
    chunks += [struct.pack('<hB', keys, 0) for _ in range(actions)]
    for b in range(bones):
        chunks.append(b'\0' + NAMES.get(b, f'bone{b}').encode().ljust(32, b'\0') + struct.pack('<h', b - 1))
        for _ in range(actions):
            chunks.append(struct.pack(f'<{3 * keys}f', *([0, 0, 10] * keys)) + bytes(12 * keys))
    return b''.join(chunks)


class WorldsR2Host(unittest.TestCase):
    def test_creation_steps_visuals_and_refusals(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/worlds-r2-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            model = Path(td) / 'r2.bmd'
            model.write_bytes(bmd())
            subprocess.run([str(NATIVE / 'build/worlds-r2-host'), str(model)], check=True)


if __name__ == '__main__':
    unittest.main()
