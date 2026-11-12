"""Portable synthetic checks and opt-in original call comparison for the classless inline visuals."""
import ctypes as C
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_worlds_inner as inner
import validate_object_render as v


class InlineVisuals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = inner.build(ROOT / 'reconstructed')

    def test_wrong_world_no_calls_or_writes(self):
        obj = C.create_string_buffer(bytes([0x55]) * v.OBJ_SIZE, v.OBJ_SIZE)
        model = C.create_string_buffer(0x100)
        before = obj.raw; log = v.new_log(1)
        calls = []
        rnd = v.RAND_FN(lambda c: calls.append('RNG') or 0)
        bone = inner.w2.BONE_FN(lambda *a: calls.append('bone'))
        named = inner.w3.NAMED_FN(lambda *a: calls.append('named bone'))
        for world in [-1, 0, 10, 18, 36, 38, 39, 41, 51, 53, 145]:
            self.assertEqual(self.lib.dll.mu_kanturu_inner(obj, model, 0, world, 0, 0, rnd, bone, None, C.byref(log)), 0)
            self.assertEqual(self.lib.dll.mu_blood_castle_inner(obj, 0, world, 0, rnd, named, None, C.byref(log)), 0)
        self.assertEqual(obj.raw, before); self.assertEqual(log.count, 0); self.assertEqual(calls, [])

    def test_clock_window_and_log_overflow(self):
        obj = C.create_string_buffer(v.OBJ_SIZE); model = C.create_string_buffer(0x100)
        C.c_int32.from_buffer(obj, 0x5c).value = 0x25
        calls = []
        rnd = v.RAND_FN(lambda c: calls.append('RNG') or 0)
        bone = inner.w2.BONE_FN()
        for clock, events in [(0, 1), (9, 1), (10, 0), (1023, 0), (1024, 1), (1033, 1), (1034, 0), (0xffffffff, 0)]:
            log = v.new_log(1)
            self.lib.dll.mu_kanturu_inner(obj, model, 0, 37, 0, clock, rnd, bone, None, C.byref(log))
            self.assertEqual(log.count, events); self.assertEqual(C.c_int32.from_buffer(obj, 0x68).value, -2)
        C.c_int32.from_buffer(obj, 0x5c).value = 0x6b
        C.c_int32.from_buffer(obj, 0x68).value = -1
        log = v.new_log(1)
        self.lib.dll.mu_kanturu_inner(obj, model, 0, 40, 0, 0, rnd, bone, None, C.byref(log))
        self.assertEqual((log.count, log.overflow), (1, 1)); self.assertEqual(calls, [])


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private original text/data required')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_inner.py'), '--cases', '200',
                            '--output', str(Path(td) / 'report.json')], check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
