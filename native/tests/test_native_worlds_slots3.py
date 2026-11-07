"""RENDER-WORLDS-SLOTS3: RenderObjectVisual's outer draw in the worlds without a class and Tormenta 141, particles attached."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
NATIVE = Path(__file__).resolve().parents[1]


class WorldsSlots3Host(unittest.TestCase):
    def test_outer_draw_per_classless_world(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/worlds-slots3-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            # One root bone, two keys, no meshes (as test_native_worlds_slots): enough to pose the object.
            chunks = [b'BMD\x0a', b"slots3".ljust(32, b'\0'), struct.pack('<HHH', 0, 1, 1), struct.pack('<hB', 2, 0),
                      b'\0' + b'bone0'.ljust(32, b'\0') + struct.pack('<h', -1), struct.pack('<6f', 0, 2, 3, 4, 2, 3),
                      bytes(24)]
            model = Path(td) / 's.bmd'
            model.write_bytes(b''.join(chunks))
            run = subprocess.run([str(NATIVE / 'build/worlds-slots3-host'), str(model)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == '__main__':
    unittest.main()
