"""RenderObject for environment objects (RENDER-WORLDS-G3): mu_env_render_body.

Portable: the helper on synthetic objects (alpha test, HiddenMesh -2, the Chaos Castle step, the Atlans fish
blend mesh 0 with its light). Private (MU_RECOVERY_INTEGRATION=1 and the restored text/data): the Unicorn
comparison scripts/validate_worlds_g3.py (also clouds 0x7f89 subtype 0xb).
"""
import ctypes as C
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
OBJ = 0x3d8


def setUpModule():
    subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)


def bits(v):
    return struct.unpack('<I', struct.pack('<f', v))[0]


class EnvBodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dll = C.CDLL(str(HERE / f'libclient_env.{SUFFIX}'))
        cls.dll.mu_env_render_body.argtypes = [C.c_void_p, C.c_int32, C.c_int, C.POINTER(C.c_uint32)]
        cls.dll.mu_env_object_load.argtypes = [C.c_void_p, C.c_char_p]
        cls.dll.mu_env_object_store.argtypes = [C.c_void_p, C.c_void_p]

    def body(self, world=7, flag=0, alpha=1.0, hidden=-1, blend=-1, light=0.0):
        image = bytearray(OBJ)
        struct.pack_into('<f', image, 0xdc, alpha)
        struct.pack_into('<i', image, 0x68, hidden)
        struct.pack_into('<i', image, 0x74, blend)
        struct.pack_into('<f', image, 0xa8, light)
        env = C.create_string_buffer(4096)
        self.dll.mu_env_object_load(env, bytes(image))
        args = (C.c_uint32 * 8)()
        drawn = self.dll.mu_env_render_body(env, world, flag, args)
        out = C.create_string_buffer(OBJ)
        self.dll.mu_env_object_store(env, out)
        return drawn, list(args), struct.unpack_from('<f', out.raw, 0xdc)[0]

    def test_atlans_fish_blend_mesh(self):
        drawn, args, _ = self.body(world=0x81, blend=0, light=0.7)
        self.assertEqual(drawn, 1)
        self.assertEqual(args, [2, bits(1.0), 0, bits(0.7), 0, 0, 0xffffffff, 0xffffffff])

    def test_skips(self):
        self.assertEqual(self.body(alpha=0.0099)[0], 0)
        self.assertEqual(self.body(alpha=0.01)[0], 1)
        self.assertEqual(self.body(hidden=-2)[0], 0)
        self.assertEqual(self.body(hidden=3)[1][6], 3)

    def test_chaos_castle_step(self):
        drawn, args, alpha = self.body(world=0x35, flag=1, alpha=0.5)
        self.assertEqual(drawn, 1)
        self.assertEqual(alpha, struct.unpack('<f', struct.pack('<f', 0.5 - 0.15))[0])
        self.assertEqual(args[1], bits(alpha))
        self.assertEqual(self.body(world=0x35, flag=1, alpha=0.155)[0], 0)
        self.assertEqual(self.body(world=0x35, flag=2, alpha=0.155)[0], 1)
        self.assertEqual(self.body(world=0x81, flag=1, alpha=0.155)[0], 1)

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-g3-orig-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_g3.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(sum(r['cases'] for r in result['families'].values()), 4000)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), 22)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))
            self.assertEqual(result['static']['fish_type_compares'], [])


if __name__ == '__main__':
    unittest.main()
