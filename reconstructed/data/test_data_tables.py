"""Synthetic checks for the client data-table codecs and decode schedules.

All fixtures are authored here and encoded by an independent Python model of
the observed client routines (three-byte XOR with per-call key phase, the
0x00976895 checksum, the 0x00f1600f package decoder). No game data is used.
The private actual-instruction comparison is scripts/validate_data_tables.py
(run by tests/test_data_tables_private.py with MU_RECOVERY_INTEGRATION=1).
"""
import ctypes
from pathlib import Path
import random
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
KEY3 = bytes((0xfc, 0xcf, 0xab))


def xor3(data, key=KEY3):
    return bytes(b ^ key[i % 3] for i, b in enumerate(data))


def checksum(data, key):
    key &= 0xffff
    result = (key << 9) & 0xffffffff
    for offset in range(0, len(data)-3, 4):
        word = struct.unpack_from('<I', data, offset)[0]
        result = result ^ word if ((offset >> 2)+key) % 2 == 0 else (result+word) & 0xffffffff
        if offset % 16 == 0:
            result = (((key+result) & 0xffffffff) >> (((offset >> 2) % 8)+1)) ^ result
    return result


def xor3_key(data, key, key3=KEY3):
    return bytes(b ^ key3[i % 3] ^ (key & 0xff) for i, b in enumerate(data))


class Spec(ctypes.Structure):
    _fields_ = [('file', ctypes.c_char_p), ('path', ctypes.c_char_p), ('loader', ctypes.c_uint32),
                ('kind', ctypes.c_int), ('record_size', ctypes.c_uint32), ('record_count', ctypes.c_uint32),
                ('checksum_key', ctypes.c_uint32), ('codec', ctypes.c_uint32), ('codec_key', ctypes.c_uint32),
                ('flags', ctypes.c_uint32)]


class Result(ctypes.Structure):
    _fields_ = [('status', ctypes.c_int), ('checksum_stored', ctypes.c_uint32),
                ('checksum_computed', ctypes.c_uint32), ('checksum_offset', ctypes.c_uint32),
                ('checksum_length', ctypes.c_uint32), ('units', ctypes.c_uint32), ('records', ctypes.c_uint32),
                ('records_offset', ctypes.c_size_t), ('consumed', ctypes.c_size_t)]


COUNTED, FIXED, UNTIL_EOF, FIXED_PLAIN, COUNT_BYTES, FORMULA, MAP_LISTS, WORDS, SERVER_LIST, PET, MIX, \
    TWO_COUNTS, PACKAGE = range(1, 14)
OK, TRUNCATED, BAD_CHECKSUM, ZERO_COUNT, BAD_HEADER, BAD_ARGUMENT = range(6)
HAS_CHECKSUM, STOP_BYTE4, COUNT_NONZERO = 1, 2, 4


class DataTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        lib = ctypes.CDLL(str(HERE/('libdatatables.dylib' if sys.platform == 'darwin' else 'libdatatables.so')))
        lib.mu_data_xor3.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_char_p]
        lib.mu_data_xor3_local.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        lib.mu_data_checksum.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint32]
        lib.mu_data_checksum.restype = ctypes.c_uint32
        lib.mu_data_xor3_key.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32]
        cls.unit = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32)
        lib.mu_data_decode.argtypes = [ctypes.POINTER(Spec), ctypes.c_void_p, ctypes.c_size_t, cls.unit,
                                       ctypes.c_void_p, ctypes.POINTER(Result)]
        lib.mu_data_decode.restype = ctypes.c_int
        lib.mu_data_find.argtypes = [ctypes.c_char_p]
        lib.mu_data_find.restype = ctypes.POINTER(Spec)
        lib.mu_data_specs.argtypes = [ctypes.POINTER(ctypes.c_size_t)]
        lib.mu_data_specs.restype = ctypes.POINTER(Spec)
        cls.lib = lib

    def decode(self, spec, image):
        buffer = ctypes.create_string_buffer(bytes(image), max(len(image), 1))
        units = []
        callback = self.unit(lambda user, offset, length, codec: units.append((offset, length, codec)))
        result = Result()
        status = self.lib.mu_data_decode(ctypes.byref(spec), buffer, len(image), callback, None, ctypes.byref(result))
        return status, result, units, buffer.raw[:len(image)]

    # ---- codecs ----
    def test_xor3_phase_and_bounds(self):
        rng = random.Random(1)
        for size in list(range(0, 40))+[257]:
            data = bytes(rng.randrange(256) for _ in range(size))
            for alignment in range(4):
                buffer = ctypes.create_string_buffer(b'\xa5'*alignment+data+b'guard')
                self.lib.mu_data_xor3(ctypes.addressof(buffer)+alignment, size, b'\x01\x02\x03')
                self.assertEqual(buffer.raw[alignment:alignment+size], xor3(data, b'\x01\x02\x03'))
                self.assertEqual(buffer.raw[:alignment], b'\xa5'*alignment)
                self.assertEqual(buffer.raw[alignment+size:alignment+size+5], b'guard')
        for size in (0, -1, -2147483648):
            buffer = ctypes.create_string_buffer(b'abc')
            self.lib.mu_data_xor3(buffer, size, KEY3)
            self.assertEqual(buffer.raw[:3], b'abc')
        self.lib.mu_data_xor3(None, 5, KEY3)
        buffer = ctypes.create_string_buffer(b'\0'*7)
        self.lib.mu_data_xor3_local(buffer, 7)
        self.assertEqual(buffer.raw[:7], xor3(b'\0'*7))

    def test_checksum_model_and_short_inputs(self):
        rng = random.Random(2)
        for size in list(range(4, 70))+[1023, 4096]:
            data = bytes(rng.randrange(256) for _ in range(size))
            for key in (0, 1, 0xe2f1, 0x5a18, 0xffff, 0x1e2f1):
                self.assertEqual(self.lib.mu_data_checksum(data, size, key), checksum(data, key))
        for size in range(4):
            self.assertEqual(self.lib.mu_data_checksum(b'\xff'*4, size, 0x1234), 0x1234 << 9)
        # trailing bytes beyond the last whole word are ignored
        self.assertEqual(self.lib.mu_data_checksum(b'abcdefg', 7, 0xe2f1), checksum(b'abcd', 0xe2f1))

    def test_xor3_key(self):
        data = bytes(range(50))
        buffer = ctypes.create_string_buffer(data)
        self.lib.mu_data_xor3_key(buffer, 50, KEY3, 0x12dc)
        self.assertEqual(buffer.raw[:50], xor3_key(data, 0x12dc))

    # ---- schedules on synthetic encoded files ----
    def test_counted_table_roundtrip_and_errors(self):
        records = [bytes((i*7+j) % 256 for j in range(13)) for i in range(5)]
        payload = b''.join(xor3(r) for r in records)   # per-record key phase, 13 % 3 != 0
        image = struct.pack('<I', 5)+payload+struct.pack('<I', checksum(payload, 0xe2f1))
        spec = Spec(b'x.bmd', b'', 0, COUNTED, 13, 0, 0xe2f1, 0, 0, HAS_CHECKSUM | COUNT_NONZERO)
        status, result, units, decoded = self.decode(spec, image)
        self.assertEqual(status, OK)
        self.assertEqual(decoded[4:4+65], b''.join(records))
        self.assertEqual([(o, n) for o, n, _ in units], [(4+13*i, 13) for i in range(5)])
        self.assertEqual((result.records, result.records_offset, result.checksum_length), (5, 4, 65))
        self.assertNotEqual(xor3(payload), b''.join(records))  # whole-payload phase would be wrong
        bad = bytearray(image)
        bad[-1] ^= 1
        status, result, units, decoded = self.decode(spec, bad)
        self.assertEqual((status, units, decoded), (BAD_CHECKSUM, [], bytes(bad)))
        zero = b'\0\0\0\0'+image[4:]
        self.assertEqual(self.decode(spec, zero)[0], ZERO_COUNT)
        self.assertEqual(self.decode(spec, image[:-5])[0], TRUNCATED)

    def test_fixed_with_stop_byte4(self):
        records = [bytes([1, 2, 3, 4, 9])+b'a'*3, bytes([1, 2, 3, 4, 0])+b'b'*3, bytes([5]*8)]
        payload = b''.join(xor3(r) for r in records)
        image = payload+struct.pack('<I', checksum(payload, 0x1234))
        spec = Spec(b'f.bmd', b'', 0, FIXED, 8, 3, 0x1234, 0, 0, HAS_CHECKSUM | STOP_BYTE4)
        status, result, units, decoded = self.decode(spec, image)
        self.assertEqual(status, OK)
        self.assertEqual(len(units), 2)  # stops after the record whose byte 4 is zero
        self.assertEqual(decoded[:16], records[0]+records[1])
        self.assertEqual(decoded[16:24], payload[16:24])

    def test_variable_schedules(self):
        # map lists: every field its own 4-byte unit
        plain = struct.pack('<II', 7, 2)+struct.pack('<II', 11, 12)+struct.pack('<II', 8, 0)
        image = b''.join(xor3(plain[i:i+4]) for i in range(0, len(plain), 4))
        status, result, units, decoded = self.decode(Spec(b'm', b'', 0, MAP_LISTS, 4, 0, 0, 0, 0, 0), image)
        self.assertEqual((status, decoded, len(units), result.records), (OK, plain, 6, 2))
        # words: 6-byte header (id, u16 length) then text, both separate units; zero length allowed
        texts = [b'Hello\0', b'', b'x'*9]
        image = b''.join(xor3(struct.pack('<IH', i, len(t)))+xor3(t) for i, t in enumerate(texts))
        status, result, units, decoded = self.decode(Spec(b'w', b'', 0, WORDS, 0, 0, 0, 0, 0, 0), image)
        self.assertEqual(status, OK)
        self.assertEqual([n for _, n, _ in units], [6, 6, 6, 0, 6, 9])
        self.assertEqual(decoded[6:12], b'Hello\0')
        # server list: 39-byte header with signed u16 length at 37, local-key codec
        header = b'S'*37+struct.pack('<h', 5)
        image = xor3(header)+xor3(b'entry')
        status, result, units, decoded = self.decode(Spec(b's', b'', 0, SERVER_LIST, 0, 0, 0, 1, 0, 0), image)
        self.assertEqual((status, decoded, [c for _, _, c in units]), (OK, header+b'entry', [1, 1]))
        negative = xor3(b'S'*37+struct.pack('<h', -1))
        self.assertEqual(self.decode(Spec(b's', b'', 0, SERVER_LIST, 0, 0, 0, 1, 0, 0), negative)[0], BAD_HEADER)

    def test_formula_pet_mix_two_counts_package(self):
        # formula: u32 records, u32 groups, groups of (id, count, count*R)
        r = 5
        groups = [(1, [b'abcde', b'fghij']), (2, [b'klmno'])]
        plain = b''.join(struct.pack('<II', g, len(rs))+b''.join(rs) for g, rs in groups)
        enc = b''.join(xor3(struct.pack('<I', g))+xor3(struct.pack('<I', len(rs)))+b''.join(xor3(x) for x in rs)
                       for g, rs in groups)
        image = struct.pack('<II', 3, 2)+enc+struct.pack('<I', checksum(enc, 0xe2f1))
        spec = Spec(b'f', b'', 0, FORMULA, r, 0, 0xe2f1, 0, 0, HAS_CHECKSUM | COUNT_NONZERO)
        status, result, units, decoded = self.decode(spec, image)
        self.assertEqual((status, decoded[8:-4], result.records), (OK, plain, 3))
        # pet: u32, u32 n, u32 count, records of 8n+16
        recs = [bytes([i])*24 for i in range(2)]
        enc = b''.join(xor3(x) for x in recs)
        image = struct.pack('<III', 9, 1, 2)+enc+struct.pack('<I', checksum(enc, 0x7f1d))
        status, result, units, decoded = self.decode(Spec(b'p', b'', 0, PET, 0, 0, 0x7f1d, 0, 0, HAS_CHECKSUM), image)
        self.assertEqual((status, decoded[12:-4]), (OK, b''.join(recs)))
        # mix: 22 counts decoded as one 88-byte unit, rejected above the group maximum
        counts = [1, 0, 2]+[0]*19
        recs = [bytes([0x40+i])*7 for i in range(3)]
        image = xor3(struct.pack('<22i', *counts))+b''.join(xor3(x) for x in recs)
        spec = Spec(b'x', b'', 0, MIX, 7, 3, 0, 0, 0, 0)
        status, result, units, decoded = self.decode(spec, image)
        self.assertEqual((status, decoded[88:], result.records), (OK, b''.join(recs), 3))
        image = xor3(struct.pack('<22i', 4, *([0]*21)))+b'\0'*28
        self.assertEqual(self.decode(spec, image)[0], BAD_HEADER)
        # two counts
        recs = [bytes([i])*4 for i in range(3)]
        enc = b''.join(xor3(x) for x in recs)
        image = struct.pack('<II', 1, 2)+enc+struct.pack('<I', checksum(enc, 0xe2f1))
        spec = Spec(b't', b'', 0, TWO_COUNTS, 4, 0, 0xe2f1, 0, 0, HAS_CHECKSUM | COUNT_NONZERO)
        self.assertEqual(self.decode(spec, image)[3][8:-4], b''.join(recs))
        # package: checksum over everything but the trailer, then one xor3+key unit
        body = b'PK\x03\x04synthetic'
        enc = xor3_key(body, 0x12dc)
        image = enc+struct.pack('<I', checksum(enc, 0x12dc))
        spec = Spec(b'l', b'', 0, PACKAGE, 0, 0, 0x12dc, 2, 0x12dc, HAS_CHECKSUM)
        status, result, units, decoded = self.decode(spec, image)
        self.assertEqual((status, decoded[:-4]), (OK, body))

    def test_until_eof_fixed_plain_count_bytes(self):
        recs = [bytes([i])*5 for i in range(4)]
        image = b''.join(xor3(x) for x in recs)+b'\x99\x98'
        status, result, units, decoded = self.decode(Spec(b'u', b'', 0, UNTIL_EOF, 5, 0, 0, 0, 0, 0), image)
        self.assertEqual((status, decoded[:20], decoded[20:], result.records), (OK, b''.join(recs), b'\x99\x98', 4))
        status, result, units, decoded = self.decode(Spec(b'q', b'', 0, FIXED_PLAIN, 5, 3, 0, 0, 0, 0), image)
        self.assertEqual((status, len(units)), (OK, 3))
        self.assertEqual(self.decode(Spec(b'q', b'', 0, FIXED_PLAIN, 5, 9, 0, 0, 0, 0), image)[0], TRUNCATED)
        body = bytes(range(10))
        enc = xor3(body)
        image = struct.pack('<I', 10)+enc+struct.pack('<I', checksum(enc, 0xc4a2))
        spec = Spec(b'e', b'', 0, COUNT_BYTES, 1, 0, 0xc4a2, 0, 0, HAS_CHECKSUM)
        self.assertEqual(self.decode(spec, image)[3][4:-4], body)

    def test_catalog(self):
        count = ctypes.c_size_t()
        specs = self.lib.mu_data_specs(ctypes.byref(count))
        names = [specs[i].file for i in range(count.value)]
        self.assertGreaterEqual(count.value, 40)
        self.assertEqual(len(names), len(set(names)))
        item = self.lib.mu_data_find(b'ITEM.BMD').contents
        self.assertEqual((item.loader, item.kind, item.record_size, item.checksum_key), (0x00cd4f2a, COUNTED, 708, 0xe2f1))
        self.assertFalse(self.lib.mu_data_find(b'missing.bmd'))
        for i in range(count.value):
            spec = specs[i]
            self.assertTrue(spec.loader)
            self.assertIn(spec.kind, range(1, 14))
        self.assertEqual(self.decode(Spec(b'z', b'', 0, COUNTED, 0, 0, 0, 0, 0, 0), b'\0'*8)[0], BAD_ARGUMENT)


if __name__ == '__main__':
    unittest.main()
