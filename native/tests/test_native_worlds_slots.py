"""RENDER-WORLDS-SLOTS: the class custom/after slots in the production first and after passes (host)."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
NATIVE = Path(__file__).resolve().parents[1]


class WorldsSlotsHost(unittest.TestCase):
    def test_slots_in_the_passes(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/worlds-slots-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            # One root bone, two keys, no meshes (as test_native_render_light): enough to pose the object.
            chunks = [b'BMD\x0a', b'slots'.ljust(32, b'\0'), struct.pack('<HHH', 0, 1, 1), struct.pack('<hB', 2, 0),
                      b'\0' + b'bone0'.ljust(32, b'\0') + struct.pack('<h', -1), struct.pack('<6f', 0, 2, 3, 4, 2, 3),
                      bytes(24)]
            model = Path(td) / 's.bmd'
            model.write_bytes(b''.join(chunks))
            subprocess.run([str(NATIVE / 'build/worlds-slots-host'), str(model)], check=True)


if __name__ == '__main__':
    unittest.main()
