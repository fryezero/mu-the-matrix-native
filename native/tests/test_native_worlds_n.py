"""Nixies Lake/Deep Dungeon creation, lights, scrolls and refused keyed effects in the production host."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
NATIVE = Path(__file__).resolve().parents[1]


class WorldsNHost(unittest.TestCase):
    def test_creation_steps_lights_and_refusals(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/worlds-n-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            # One root bone, two keys, no meshes: enough for the generic animation tick.
            chunks = [b'BMD\x0a', b'worlds-n'.ljust(32, b'\0'), struct.pack('<HHH', 0, 1, 1), struct.pack('<hB', 2, 0),
                      b'\0' + b'bone0'.ljust(32, b'\0') + struct.pack('<h', -1), struct.pack('<6f', 0, 2, 3, 4, 2, 3),
                      bytes(24)]
            model = Path(td) / 'n.bmd'
            model.write_bytes(b''.join(chunks))
            subprocess.run([str(NATIVE / 'build/worlds-n-host'), str(model)], check=True)


if __name__ == '__main__':
    unittest.main()
