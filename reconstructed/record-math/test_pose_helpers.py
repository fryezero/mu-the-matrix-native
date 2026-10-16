"""Analytic checks for the pose-builder helpers 0x00cfec33, 0x00d00ca4,
0x00d008bf and 0x00cff32a (instruction comparison: scripts/validate_pose_builder.py)."""
import ctypes
import math
from pathlib import Path
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'


def buffer(fmt, *values):
    return ctypes.create_string_buffer(struct.pack(fmt, *values), struct.calcsize(fmt))


class PoseHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        library = ctypes.CDLL(str(HERE/f'librecord_math.{SUFFIX}'))
        cls.compare = library.mu_quaternion_compare
        cls.compare.argtypes, cls.compare.restype = [ctypes.c_void_p]*2, ctypes.c_int
        cls.slerp = library.mu_quaternion_slerp
        cls.slerp.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_float, ctypes.c_void_p]
        cls.slerp.restype = None
        cls.qmatrix = library.mu_quaternion_matrix
        cls.qmatrix.argtypes, cls.qmatrix.restype = [ctypes.c_void_p]*2, None
        cls.amatrix = library.mu_angle_matrix
        cls.amatrix.argtypes, cls.amatrix.restype = [ctypes.c_void_p]*2, None

    def test_compare_uses_binary64_threshold_and_treats_nan_as_equal(self):
        zero = buffer('<4f', 0, 0, 0, 0)
        # binary32 0.001 is slightly above binary64 0.001, so it differs.
        self.assertEqual(self.compare(zero, buffer('<4f', 0, 0, 0, 0.001)), 0)
        self.assertEqual(self.compare(zero, buffer('<4f', 0.000999, -0.000999, 0, 0)), 1)
        self.assertEqual(self.compare(zero, buffer('<4f', math.nan, 0, 0, 0)), 1)

    def test_slerp_flips_q_in_place_and_branches(self):
        p = buffer('<4f', 0, 0, 0, 1)
        q = buffer('<4f', 0, 0, 0, -1)
        out = ctypes.create_string_buffer(16)
        self.slerp(p, q, 0.5, out)
        self.assertEqual(struct.unpack('<4f', q.raw), (-0.0, -0.0, -0.0, 1.0))
        # cosom = 1 after the flip: linear scales 1-t and t.
        self.assertEqual(struct.unpack('<4f', out.raw), (0.0, 0.0, 0.0, 1.0))
        # |p|^2 = 2^28 hides a-b, so no flip; cosom = -1 takes the opposite branch.
        p = buffer('<4f', 16384, 0, 0, 0)
        q = buffer('<4f', -2.0**-14, 0, 0, 1)
        self.slerp(p, q, 0.0, out)
        # out = (-p1, p0, -p3, p2), then the first three blend with sin(pi/2) = 1 and sin(0) = 0.
        self.assertEqual(struct.unpack('<4f', out.raw), (16384.0, 0.0, 0.0, 0.0))
        self.assertEqual(struct.unpack('<4f', q.raw), (-2.0**-14, 0.0, 0.0, 1.0))
        self.slerp(p, q, 1.0, out)
        self.assertEqual(struct.unpack('<4f', out.raw)[1:], (16384.0, -0.0, 0.0))
        self.assertLess(abs(struct.unpack('<4f', out.raw)[0]), 1e-3*16384)
        # Spherical: 90 degrees about z at t = 0.5 gives 45 degrees, unit length.
        p = buffer('<4f', 0, 0, 0, 1)
        q = buffer('<4f', 0, 0, math.sin(math.pi/4), math.cos(math.pi/4))
        self.slerp(p, q, 0.5, out)
        r = struct.unpack('<4f', out.raw)
        self.assertAlmostEqual(r[2], math.sin(math.pi/8), places=6)
        self.assertAlmostEqual(math.sqrt(sum(v*v for v in r)), 1.0, places=6)

    def test_quaternion_matrix_leaves_translation(self):
        matrix = buffer('<12f', *range(12))
        self.qmatrix(buffer('<4f', 0, 0, 0, 1), matrix)
        self.assertEqual(struct.unpack('<12f', matrix.raw), (1, 0, 0, 3, 0, 1, 0, 7, 0, 0, 1, 11))
        # (1,0,0,0) is a half turn about x.
        self.qmatrix(buffer('<4f', 1, 0, 0, 0), matrix)
        self.assertEqual(struct.unpack('<12f', matrix.raw), (1, 0, 0, 3, 0, -1, 0, 7, 0, 0, -1, 11))

    def test_angle_matrix_degrees_zyx_and_zero_translation(self):
        matrix = buffer('<12f', *([7.0]*12))
        self.amatrix(buffer('<3f', 0, 0, 90), matrix)
        m = struct.unpack('<12f', matrix.raw)
        for actual, expected in zip(m, (0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0)):
            self.assertAlmostEqual(actual, expected, places=6)
        self.assertEqual(matrix.raw[12:16]+matrix.raw[28:32]+matrix.raw[44:48], bytes(12))
        self.amatrix(buffer('<3f', 90, 0, 0), matrix)
        m = struct.unpack('<12f', matrix.raw)
        for actual, expected in zip(m, (1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0)):
            self.assertAlmostEqual(actual, expected, places=6)


if __name__ == '__main__':
    unittest.main()
