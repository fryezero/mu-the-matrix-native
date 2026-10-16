"""Checks for the client-linked Euler-angle rotation conversion at 0x00d00724."""
import ctypes
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TRIG = ctypes.CFUNCTYPE(ctypes.c_double, ctypes.c_double)


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def stepwise(angles):
    """Independent binary32 restatement of the observed product sequence."""
    half = [f32(f32(a)*0.5) for a in angles]
    s = [f32(math.sin(h)) for h in half]
    c = [f32(math.cos(h)) for h in half]

    def product(a, b, d):
        return f32(f32(a*b)*d)
    return (f32(product(s[0], c[1], c[2]) - product(c[0], s[1], s[2])),
            f32(product(c[0], s[1], c[2]) + product(s[0], c[1], s[2])),
            f32(product(c[0], c[1], s[2]) - product(s[0], s[1], c[2])),
            f32(product(c[0], c[1], c[2]) + product(s[0], s[1], s[2])))


def hamilton(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw*bx + ax*bw + ay*bz - az*by, aw*by - ax*bz + ay*bw + az*bx,
            aw*bz + ax*by - ay*bx + az*bw, aw*bw - ax*bx - ay*by - az*bz)


class RotationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        library = ctypes.CDLL(str(HERE/('librecord_math.dylib' if sys.platform == 'darwin' else 'librecord_math.so')))
        cls.rotation = library.mu_rotation_quaternion
        cls.rotation.argtypes = [ctypes.c_void_p]*2
        cls.rotation.restype = None
        cls.using = library.mu_rotation_quaternion_using
        cls.using.argtypes = [ctypes.c_void_p, ctypes.c_void_p, TRIG, TRIG]
        cls.using.restype = None
        cls.environment = library.mu_record_math_environment_supported
        cls.environment.restype = ctypes.c_int

    def invoke(self, angles):
        source = ctypes.create_string_buffer(struct.pack('<3f', *angles))
        output = ctypes.create_string_buffer(16)
        self.rotation(source, output)
        return output.raw

    def test_zero_and_single_axis_rotations(self):
        self.assertEqual(self.environment(), 1)
        self.assertEqual(struct.unpack('<4f', self.invoke((0, 0, 0))), (0, 0, 0, 1))
        self.assertEqual(self.invoke((-0.0, -0.0, -0.0)), struct.pack('<4f', -0.0, 0.0, -0.0, 1.0))
        for angle in (0.5, -1.25, math.pi, 100.0):
            half = f32(f32(angle)*0.5)
            s, c = f32(math.sin(half)), f32(math.cos(half))
            for axis in range(3):
                angles = [0.0, 0.0, 0.0]
                angles[axis] = angle
                expected = [0.0, 0.0, 0.0, c]
                expected[axis] = s
                self.assertEqual(struct.unpack('<4f', self.invoke(angles)), tuple(expected))

    def test_binary32_sequence_and_zyx_convention(self):
        for angles in ((0.1, 0.2, 0.3), (1.0, -1.0, 2.0), (-3.0, 0.75, 6.0), (12.5, -0.001, 3.25)):
            actual = struct.unpack('<4f', self.invoke(angles))
            self.assertEqual(actual, stepwise(angles))
            axis = [(math.sin(a/2), 0, 0, math.cos(a/2)) for a in angles]
            axis[1] = (0, axis[1][0], 0, axis[1][3])
            axis[2] = (0, 0, axis[2][0], axis[2][3])
            reference = hamilton(hamilton(axis[2], axis[1]), axis[0])
            for value, expected in zip(actual, reference):
                self.assertAlmostEqual(value, expected, delta=2e-6)
            self.assertNotEqual(self.invoke(angles), self.invoke(tuple(reversed(angles))))

    def test_in_place_and_unaligned_spans(self):
        angles = (0.4, -2.5, 1.75)
        expected = self.invoke(angles)
        buffer = ctypes.create_string_buffer(b'\x00' + struct.pack('<3f', *angles) + b'\x00'*8)
        pointer = ctypes.addressof(buffer)+1
        self.rotation(pointer, pointer)
        self.assertEqual(buffer.raw[1:17], expected)

    def test_trig_callbacks_follow_original_call_order(self):
        calls = []

        def record(name):
            def trig(argument):
                calls.append((name, argument))
                return getattr(math, name)(argument)
            return TRIG(trig)
        sine, cosine = record('sin'), record('cos')
        angles = (0.3, -0.7, 2.9)
        output = ctypes.create_string_buffer(16)
        self.using(ctypes.create_string_buffer(struct.pack('<3f', *angles)), output, sine, cosine)
        halves = [f32(f32(a)*0.5) for a in angles]
        self.assertEqual(calls, [(name, halves[index]) for index in (2, 1, 0) for name in ('sin', 'cos')])
        self.assertEqual(output.raw, self.invoke(angles))

    def test_validator_refuses_unpinned_text_without_optional_emulator(self):
        with tempfile.TemporaryDirectory() as directory:
            text = Path(directory)/'authored.bin'
            text.write_bytes(b'not captured code')
            result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_rotation.py'),
                                     '--text', str(text), '--data', str(text), '--flag', str(text),
                                     '--library', '/nonexistent/library'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pinned restored text', result.stderr)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private rotation instruction comparison is opt-in')
    def test_private_original_rotation_instructions(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        flag = Path(os.environ.get('MU_TRIG_FLAG', ROOT/'evidence/trig-state-15/captures/late/math-dispatch-flag.bin'))
        with tempfile.TemporaryDirectory() as directory:
            scanner = Path(directory)/'scan'
            subprocess.run(['clang', '-O2', '-std=c11', '-ffp-contract=off', str(ROOT/'scripts/scan_trig_midpoints.c'),
                            '-lm', '-o', str(scanner)], check=True, capture_output=True)
            midpoints = Path(directory)/'midpoints.txt'
            with midpoints.open('w') as output:
                subprocess.run([str(scanner), '64'], check=True, stdout=output)
            report = Path(directory)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_rotation.py'), '--text', str(text),
                            '--data', str(data), '--flag', str(flag), '--midpoints', str(midpoints),
                            '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
        self.assertEqual(result['mismatches'], 0)
        self.assertEqual(result['composition_with_client_trig_mismatches'], 0)
        self.assertEqual(result['stopped_cases'], 0)
        self.assertGreater(result['instruction_cases'], 7000)
        self.assertEqual(result['trig_host_float_equal'], result['trig_calls'])
        self.assertEqual(result['alias_alignment_mismatches'], 0)
        self.assertEqual(result['state_variant_mismatches'], 0)
        self.assertGreater(result['axis_order_negative_control_differences'], 1000)
        self.assertGreater(result['double_intermediate_negative_control_differences'], 0)
        self.assertTrue(all(not item['returned'] or item['x86'] == item['native']
                            for item in result['outside_domain_cases']))


if __name__ == '__main__':
    unittest.main()
