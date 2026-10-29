"""RENDER-WORLDS-R production host: worlds 131..134 create/move dispatch, visual bones/callbacks, refusals."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
NATIVE = Path(__file__).resolve().parents[1]
BONES, ACTIONS, KEYS = 20, 4, 3


class WorldsRHost(unittest.TestCase):
    def test_worlds_131_to_134_host(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/worlds-r-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            # Twenty root bones translated by 10 per bone, four actions of three keys, no meshes.
            chunks = [b'BMD\x0a', b'worlds-r'.ljust(32, b'\0'), struct.pack('<HHH', 0, BONES, ACTIONS)]
            chunks += [struct.pack('<hB', KEYS, 0)] * ACTIONS
            for bone in range(BONES):
                chunks.append(b'\0' + f'bone{bone}'.encode().ljust(32, b'\0') + struct.pack('<h', -1))
                for _ in range(ACTIONS):
                    chunks += [struct.pack('<3f', bone * 10, 0, 0) * KEYS, bytes(12 * KEYS)]
            model = Path(td) / 'worlds-r.bmd'
            model.write_bytes(b''.join(chunks))
            subprocess.run([str(NATIVE / 'build/worlds-r-host'), str(model)], check=True)


if __name__ == '__main__':
    unittest.main()
