"""RENDER-WORLDS-AFTER4: the after pass's render-time AddTerrainLight lands in the frame light (production host)."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
NATIVE = Path(__file__).resolve().parents[1]


class RenderLightHost(unittest.TestCase):
    def test_kardamahal_after_light(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/render-light-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            # One root bone, two keys, no meshes (as test_native_worlds_n): enough to pose the object.
            chunks = [b'BMD\x0a', b'light'.ljust(32, b'\0'), struct.pack('<HHH', 0, 1, 1), struct.pack('<hB', 2, 0),
                      b'\0' + b'bone0'.ljust(32, b'\0') + struct.pack('<h', -1), struct.pack('<6f', 0, 2, 3, 4, 2, 3),
                      bytes(24)]
            model = Path(td) / 'l.bmd'
            model.write_bytes(b''.join(chunks))
            subprocess.run([str(NATIVE / 'build/render-light-host'), str(model)], check=True)


if __name__ == '__main__':
    unittest.main()
