"""Network protocol module (NATIVE-NET-001) checks.

Portable (synthetic data only, run in CI on macOS and Linux):
  * framing: C1/C2/C3/C4 header-length and size-field rules via the mu-proto
    CLI and the ctypes-loaded library;
  * send obfuscation: XorData encode is reproduced by an independent Python
    statement of the client rule, and decode is its exact inverse;
  * packet builder: Begin/AddData/WriteSize produce the documented wire bytes,
    and encode ranges cover only the appended data;
  * receive dechunker: a byte stream splits into frames exactly like the client
    loop, including partial-frame buffering and bad-head reset.

No client bytes are used; every fixture is authored here. The bit-exact
agreement with the client's own instructions is checked separately by
scripts/validate_protocol.py (private restored capture, Unicorn).
"""
import ctypes
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
TOOL = NATIVE / 'build/mu-proto'
LIB = NATIVE / 'build' / ('libmuprotocol.' + SUFFIX)

# The client's 32-byte send key (XorData immediates at 0x00d5205e).
KEY = bytes([
    0xab, 0x11, 0xcd, 0xfe, 0x18, 0x23, 0xc5, 0xa3,
    0xca, 0x33, 0xc1, 0xcc, 0x66, 0x67, 0x21, 0xf3,
    0x32, 0x12, 0x15, 0x35, 0x29, 0xff, 0xfe, 0x1d,
    0x44, 0xef, 0xcd, 0x41, 0x26, 0x3c, 0x4e, 0x4d,
])


def py_xor_encode(obj, start, end):
    """Independent statement of XorData: obj[0..1] size word, body at obj+2."""
    b = bytearray(obj)
    for i in range(start, end):
        b[i + 2] ^= b[i + 1] ^ KEY[i & 31]
    return bytes(b)


def py_build(head, opcode, payload, encode):
    """Independent statement of Begin/AddData/WriteSize; returns the wire frame."""
    two = head in (0xC2, 0xC4)
    obj = bytearray(0x145c)
    size = 0

    def add(data, enc):
        nonlocal size, obj
        obj[2 + size:2 + size + len(data)] = data
        if enc:
            tmp = py_xor_encode(bytes(obj), size, size + len(data))
            obj = bytearray(tmp)
        size += len(data)
        obj[0] = size & 0xff
        obj[1] = (size >> 8) & 0xff

    add(bytes([head]), 0)
    add(bytes([0, 0]) if two else bytes([0]), 0)
    add(bytes([opcode]), 0)
    add(payload, encode)
    # WriteSize
    if two:
        obj[3] = (size >> 8) & 0xff
        obj[4] = size & 0xff
    else:
        obj[3] = size & 0xff
    return bytes(obj[2:2 + size])


def py_dechunk(stream):
    out, off, rl = [], 0, len(stream)
    while rl >= 3:
        h = stream[off]
        if h in (0xC1, 0xC3):
            size = stream[off + 1]
        elif h in (0xC2, 0xC4):
            size = (stream[off + 1] << 8) + stream[off + 2]
        else:
            break
        if size <= 0 or size > rl:
            break
        out.append(stream[off:off + size])
        off += size
        rl -= size
    return out


class NativePacket(ctypes.Structure):
    _fields_ = [('obj', ctypes.c_uint8 * 0x145c), ('overflow', ctypes.c_uint32)]


class NativeRecv(ctypes.Structure):
    _fields_ = [('buf', ctypes.c_uint8 * 0x2000), ('len', ctypes.c_size_t)]


@unittest.skipUnless(LIB.exists(), 'build native/ first (make -C native)')
class LibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lib = ctypes.CDLL(str(LIB))
        lib.mu_frame_header_len.argtypes = [ctypes.c_uint8]
        lib.mu_frame_header_len.restype = ctypes.c_uint32
        lib.mu_packet_begin.argtypes = [ctypes.c_void_p, ctypes.c_uint8, ctypes.c_uint8]
        lib.mu_packet_add.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int]
        lib.mu_packet_add.restype = ctypes.c_int
        lib.mu_packet_finish.argtypes = [ctypes.c_void_p]
        lib.mu_packet_finish.restype = ctypes.c_uint32
        lib.mu_send_xor_encode.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_size_t]
        lib.mu_send_xor_decode.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_size_t]
        lib.mu_recv_init.argtypes = [ctypes.c_void_p]
        lib.mu_recv_push.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        lib.mu_recv_push.restype = ctypes.c_int
        lib.mu_recv_drain.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        lib.mu_recv_drain.restype = ctypes.c_size_t
        cls.lib = lib

    def test_header_len_rules(self):
        self.assertEqual(self.lib.mu_frame_header_len(0xC1), 2)
        self.assertEqual(self.lib.mu_frame_header_len(0xC3), 2)
        self.assertEqual(self.lib.mu_frame_header_len(0xC2), 3)
        self.assertEqual(self.lib.mu_frame_header_len(0xC4), 3)
        self.assertEqual(self.lib.mu_frame_header_len(0x00), 0)
        self.assertEqual(self.lib.mu_frame_header_len(0xFF), 0)

    def _native_build(self, head, opcode, payload, encode):
        p = NativePacket()
        ctypes.memset(ctypes.byref(p), 0, ctypes.sizeof(p))
        self.lib.mu_packet_begin(ctypes.byref(p), head, opcode)
        self.lib.mu_packet_add(ctypes.byref(p), bytes(payload), len(payload), 1 if encode else 0)
        total = self.lib.mu_packet_finish(ctypes.byref(p))
        return bytes(bytearray(p.obj)[2:2 + total])

    def test_builder_matches_independent_model(self):
        import random
        rng = random.Random(1)
        for _ in range(2000):
            head = rng.choice([0xC1, 0xC2, 0xC3, 0xC4])
            op = rng.randrange(256)
            payload = bytes(rng.randrange(256) for _ in range(rng.randint(0, 60)))
            encode = rng.randint(0, 1)
            got = self._native_build(head, op, payload, encode)
            exp = py_build(head, op, payload, encode)
            self.assertEqual(got, exp)

    def test_known_build_vectors(self):
        # C1, opcode 0xF1, payload 01 02 03, no encode.
        self.assertEqual(self._native_build(0xC1, 0xF1, b'\x01\x02\x03', 0).hex(), 'c106f1010203')
        # Same, encoded: only the payload is xored.
        self.assertEqual(self._native_build(0xC1, 0xF1, b'\x01\x02\x03', 1).hex(), 'c106f10e1434')
        # C2 uses a 2-byte big-endian size.
        self.assertEqual(self._native_build(0xC2, 0xF3, b'\xaa\xbb\xcc\xdd\xee', 0).hex(),
                         'c20009f3aabbccddee')

    def test_xor_round_trip_and_rule(self):
        import random
        rng = random.Random(2)
        for _ in range(2000):
            size = rng.randint(1, 200)
            obj = bytearray(2 + size + 8)
            for i in range(len(obj)):
                obj[i] = rng.randrange(256)
            obj[0] = size & 0xff
            obj[1] = (size >> 8) & 0xff
            buf = (ctypes.c_char * len(obj)).from_buffer_copy(bytes(obj))
            self.lib.mu_send_xor_encode(buf, 0, size)
            self.assertEqual(bytes(buf), py_xor_encode(bytes(obj), 0, size))
            self.lib.mu_send_xor_decode(buf, 0, size)
            self.assertEqual(bytes(buf), bytes(obj))

    def test_dechunk_matches_model(self):
        import random
        rng = random.Random(3)
        for _ in range(1000):
            frames = []
            for _ in range(rng.randint(1, 5)):
                head = rng.choice([0xC1, 0xC2, 0xC3, 0xC4])
                if head in (0xC1, 0xC3):
                    size = rng.randint(3, 250)
                    frames.append(bytes([head, size]) + bytes(rng.randrange(256) for _ in range(size - 2)))
                else:
                    size = rng.randint(3, 900)
                    frames.append(bytes([head, (size >> 8) & 0xff, size & 0xff])
                                  + bytes(rng.randrange(256) for _ in range(size - 3)))
            stream = b''.join(frames)
            got = self._native_dechunk(stream)
            self.assertEqual(got, py_dechunk(stream))

    def _native_dechunk(self, stream):
        r = NativeRecv()
        self.lib.mu_recv_init(ctypes.byref(r))
        self.lib.mu_recv_push(ctypes.byref(r), stream, len(stream))
        out = []

        @ctypes.CFUNCTYPE(None, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_void_p)
        def cb(frame, size, ud):
            out.append(bytes(bytearray(frame[:size])))
        self.lib.mu_recv_drain(ctypes.byref(r), cb, None)
        return out

    def test_partial_frame_is_buffered(self):
        # One full C1 frame then a 2-byte prefix of another: one frame, 2 left.
        r = NativeRecv()
        self.lib.mu_recv_init(ctypes.byref(r))
        self.lib.mu_recv_push(ctypes.byref(r), bytes.fromhex('c104aabb') + b'\xc1\x05', 6)
        out = []

        @ctypes.CFUNCTYPE(None, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_void_p)
        def cb(frame, size, ud):
            out.append(bytes(bytearray(frame[:size])))
        n = self.lib.mu_recv_drain(ctypes.byref(r), cb, None)
        self.assertEqual(n, 1)
        self.assertEqual(out, [bytes.fromhex('c104aabb')])
        self.assertEqual(r.len, 2)

    def test_bad_head_clears_buffer(self):
        r = NativeRecv()
        self.lib.mu_recv_init(ctypes.byref(r))
        self.lib.mu_recv_push(ctypes.byref(r), b'\x00\x01\x02\x03', 4)
        n = self.lib.mu_recv_drain(ctypes.byref(r), None, None)
        self.assertEqual(n, 0)
        self.assertEqual(r.len, 0)


@unittest.skipUnless(TOOL.exists(), 'build native/ first (make -C native)')
class CliTests(unittest.TestCase):
    def run_tool(self, *args):
        res = subprocess.run([str(TOOL), *args], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        return res.stdout

    def test_build_parse_round_trip(self):
        out = self.run_tool('build', 'C1', 'F1', '010203')
        frame = out.split()[-1]
        self.assertEqual(frame, 'c106f1010203')
        parsed = self.run_tool('parse', frame)
        self.assertIn('head=c1', parsed)
        self.assertIn('size=6', parsed)
        self.assertIn('payload: f1010203', parsed)

    def test_xor_cli_round_trip(self):
        enc = self.run_tool('xor-encode', '0400c100f101').split()[-1]
        dec = self.run_tool('xor-decode', '0400' + enc).split()[-1]
        self.assertEqual(dec, 'c100f101')

    def test_dechunk_cli(self):
        out = self.run_tool('dechunk', 'c106f1010203c2000700aabbcc')
        self.assertIn('frames=2', out)


if __name__ == '__main__':
    unittest.main()
