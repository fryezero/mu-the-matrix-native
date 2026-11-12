"""Synthetic refusal/world guards and opt-in original checks for the later inline producers."""
import ctypes as C
import os
from pathlib import Path
import subprocess
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_worlds_inner2 as inner
import validate_object_render as v

class LaterInline(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.lib = inner.build(ROOT / 'reconstructed')

    def test_wrong_world(self):
        obj = C.create_string_buffer(bytes([0x55]) * v.OBJ_SIZE, v.OBJ_SIZE)
        before = obj.raw; log = v.new_log(); calls = []
        rnd = v.RAND_FN(lambda c: calls.append('rng') or 0)
        bone = inner.w2.BONE_FN(lambda *a: calls.append('bone'))
        for world in range(-1, 146):
            if world in (51, 56): continue
            self.assertEqual(self.lib.dll.mu_later_world_inner(obj, 0, world, 0, rnd, bone, None, None, C.byref(log)), 0)
        self.assertEqual(obj.raw, before); self.assertEqual(log.count, 0); self.assertEqual(calls, [])

    def test_unwritten_light_refusal(self):
        obj = C.create_string_buffer(v.OBJ_SIZE); C.c_int32.from_buffer(obj, 0x5c).value = 0x3a
        log = v.new_log(); rnd = v.RAND_FN(lambda c: self.fail('unexpected rng'))
        self.lib.dll.mu_later_world_inner(obj, 0, 51, 0, rnd, inner.w2.BONE_FN(), None, None, C.byref(log))
        self.assertEqual(v.log_events(log)[0][0], 0xe31358)
        self.assertEqual(log.count, 1)

    def test_smoke_overflow_still_hides(self):
        obj = C.create_string_buffer(v.OBJ_SIZE); C.c_int32.from_buffer(obj, 0x5c).value = 0x3c
        C.c_int32.from_buffer(obj, 0x68).value = -1
        log = v.new_log(1); rnd = v.RAND_FN(lambda c: self.fail('unexpected rng'))
        self.lib.dll.mu_later_world_inner(obj, 0, 51, 0, rnd, inner.w2.BONE_FN(), None, None, C.byref(log))
        self.assertEqual((log.count, log.overflow), (1, 1))
        self.assertEqual(C.c_int32.from_buffer(obj, 0x68).value, -2)

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private original text/data required')
class ClientComparison(unittest.TestCase):
    def test_original(self):
        subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_inner2.py'), '--cases', '200'],
                       check=True, capture_output=True)

if __name__ == '__main__': unittest.main()
