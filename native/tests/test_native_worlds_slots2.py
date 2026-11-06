"""RENDER-WORLDS-SLOTS2: RenderObjectVisual's outer flicker draw in the production first pass of every class world."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
NATIVE = Path(__file__).resolve().parents[1]


class WorldsSlots2Host(unittest.TestCase):
    def test_outer_draw_per_class_world(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/worlds-slots2-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            # One root bone, two keys, no meshes (as test_native_worlds_slots): enough to pose the object.
            chunks = [b'BMD\x0a', b'slots2'.ljust(32, b'\0'), struct.pack('<HHH', 0, 1, 1), struct.pack('<hB', 2, 0),
                      b'\0' + b'bone0'.ljust(32, b'\0') + struct.pack('<h', -1), struct.pack('<6f', 0, 2, 3, 4, 2, 3),
                      bytes(24)]
            model = Path(td) / 's.bmd'
            model.write_bytes(b''.join(chunks))
            run = subprocess.run([str(NATIVE / 'build/worlds-slots2-host'), str(model)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == '__main__':
    unittest.main()
