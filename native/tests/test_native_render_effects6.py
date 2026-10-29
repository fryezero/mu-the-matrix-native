"""RENDER-EFFECTS-006: the refused world requests consumed in the production host (owned effects and .ein)."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

NATIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_native_effect import billboard, particle_system  # noqa: E402

EIN = ['fire09-red01', 'Sparkle21-red01', 'smoke17-red01', 'twinkle10-red02']


def bmd(bones=21, actions=3, keys=4):
    # A bone chain, `actions` actions of `keys` keys each, no meshes.
    chunks = [b'BMD\x0a', b'effects6'.ljust(32, b'\0'), struct.pack('<HHH', 0, bones, actions)]
    chunks += [struct.pack('<hB', keys, 0) for _ in range(actions)]
    for b in range(bones):
        chunks.append(b'\0' + f'bone{b}'.encode().ljust(32, b'\0') + struct.pack('<h', b - 1))
        for _ in range(actions):
            chunks.append(struct.pack(f'<{3 * keys}f', *([0, 0, 10] * keys)) + bytes(12 * keys))
    return b''.join(chunks)


class RenderEffects6Host(unittest.TestCase):
    def test_refused_requests_are_consumed(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/render-effects6-host'], check=True,
                       capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            model = Path(td) / 'effects6.bmd'
            model.write_bytes(bmd())
            root, empty = Path(td) / 'root', Path(td) / 'empty'
            (root / 'Data/Effect').mkdir(parents=True)
            (empty / 'Data/Effect').mkdir(parents=True)
            for k, name in enumerate(EIN):   # synthetic stand-ins under the client's names
                (root / 'Data/Effect' / (name + '.ein')).write_text(
                    json.dumps(particle_system(Scale=float(k + 1)) if k % 2 == 0 else billboard()))
            out = subprocess.run([str(NATIVE / 'build/render-effects6-host'), str(model), str(root), str(empty)],
                                 check=True, capture_output=True, text=True).stdout
        rows = [json.loads(line) for line in out.splitlines()]
        worlds = [r for r in rows if 'world' in r]
        self.assertEqual(len(worlds), 8)
        for r in worlds:
            self.assertEqual(r['refused_after'], 0, r)
            self.assertEqual(r['effects_unsupported'], 0, r)
            self.assertEqual(r['particles_unsupported'], 0, r)
            self.assertGreater(r['effects_created'], 0, r)
        ein = [r for r in rows if 'ein' in r]
        self.assertEqual([(r['ein'], r['refused_after'], r['attached']) for r in ein], [(1, 0, 4), (0, 400, 0)])


if __name__ == '__main__':
    unittest.main()
