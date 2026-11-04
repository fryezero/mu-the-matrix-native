"""RENDER-WORLDS-AFTER5: the object action registry in the production runtime (anim_host.c), with a synthetic
mapanim.tsv. The live table is decoded game data and stays local."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
NATIVE = Path(__file__).resolve().parents[1]

TABLE = '\n'.join([
    '# synthetic MapObjectAnimationInfo rows (world, type, action, speed, handler, param, extra)',
    '144\t13\t0\t0.25\t1\t300\t1',
    '144\t13\t1\t0.5\t1\t300\t0',
    '144\t32\t0\t0.07\t0\t300\t-',
    '51\t32\t0\t0.48\t0\t0\t-',
    ''])


class AnimHost(unittest.TestCase):
    def test_registry_runtime(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/anim-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            # One root bone, two actions of two keys, no meshes.
            chunks = [b'BMD\x0a', b'anim'.ljust(32, b'\0'), struct.pack('<HHH', 0, 1, 2),
                      struct.pack('<hB', 2, 0) * 2, b'\0' + b'bone0'.ljust(32, b'\0') + struct.pack('<h', -1)]
            chunks += [struct.pack('<6f', 0, 2, 3, 4, 2, 3), bytes(24)] * 2
            model = Path(td) / 'a.bmd'
            model.write_bytes(b''.join(chunks))
            lang = Path(td) / 'lang'
            lang.mkdir()
            (lang / 'mapanim.tsv').write_text(TABLE)
            subprocess.run([str(NATIVE / 'build/anim-host'), str(model), str(lang)], check=True)


if __name__ == '__main__':
    unittest.main()
