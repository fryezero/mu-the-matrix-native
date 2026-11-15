"""RENDER-WORLDS-PICK-001: the map object's box +0x31c written by the render pass and the registry's mouse-over
tick handlers 4 and 6 in the production runtime (pick_host.c), with a synthetic mapanim.tsv and model. The live
table is decoded game data and stays local; no live row uses these handlers."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
NATIVE = Path(__file__).resolve().parents[1]

TABLE = '\n'.join([
    '# synthetic MapObjectAnimationInfo rows (world, type, action, speed, handler, param, extra)',
    '144\t13\t0\t0.16\t4\t300\t0,1',    # handler 4, step 0: the mouse is over the box -> action 1
    '144\t13\t1\t0.16\t4\t300\t2,0',    # handler 4, step 2: the mouse is not over it -> action 0
    '144\t32\t0\t0.16\t6\t300\t0,1',    # handler 6, step 0: over and not latched -> latch, action 1
    '144\t32\t1\t0.16\t0\t300\t-',
    '144\t99\t0\t0.16\t4\t300\t0,1',    # never drawn in the host: the all-zero box
    '144\t99\t1\t0.16\t0\t300\t-',
    ''])


class PickHost(unittest.TestCase):
    def test_box_and_mouse_handlers(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/pick-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            # One root bone, two actions of two keys, no meshes.
            chunks = [b'BMD\x0a', b'pick'.ljust(32, b'\0'), struct.pack('<HHH', 0, 1, 2),
                      struct.pack('<hB', 2, 0) * 2, b'\0' + b'bone0'.ljust(32, b'\0') + struct.pack('<h', -1)]
            chunks += [struct.pack('<6f', 0, 2, 3, 4, 2, 3), bytes(24)] * 2
            model = Path(td) / 'p.bmd'
            model.write_bytes(b''.join(chunks))
            lang = Path(td) / 'lang'
            lang.mkdir()
            (lang / 'mapanim.tsv').write_text(TABLE)
            subprocess.run([str(NATIVE / 'build/pick-host'), str(model), str(lang)], check=True)


if __name__ == '__main__':
    unittest.main()
