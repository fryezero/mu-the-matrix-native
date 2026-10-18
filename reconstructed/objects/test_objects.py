"""Synthetic checks for the authored static-object loader and model table.

Fixtures are authored here: plaintext object files built by an independent
Python statement of the loader walk (0x016d9ac5) and the v12 encoder (the
inverse of the immediates in 0x0098c5f2). No game data is used. The private
actual-instruction comparison is scripts/validate_objects.py (run by
tests/test_objects_private.py with MU_RECOVERY_INTEGRATION=1).
"""
import ctypes
from pathlib import Path
import random
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
V12_KEY = bytes((0xD1, 0x73, 0x52, 0xF6, 0xD2, 0x9A, 0xCB, 0x27, 0x3E, 0xAF, 0x59, 0x31, 0x37, 0xB3, 0xE7, 0xA2))
OK, TRUNCATED, BAD_ARGUMENT = range(3)


def v12_encode(plain):
    out, key = bytearray(len(plain)), 0x5e
    for i, p in enumerate(plain):
        c = ((p + key) & 0xff) ^ V12_KEY[i % 16]
        out[i], key = c, (c + 0x3d) & 0xff
    return bytes(out)


def record_size(version):
    return 30 + 2 * (version >= 1) + (version >= 2) + 12 * (version >= 3) + (version >= 4) + 8 * (version >= 5)


def expected_records(plain):
    """The 0x38-byte constructor record after the loader's reads (pad bytes zero)."""
    version, count = plain[0], struct.unpack_from('<h', plain, 2)[0]
    offset, out = 4, []
    for _ in range(max(count, 0)):
        p = plain[offset:offset + record_size(version)]
        rec = bytearray(0x38)
        struct.pack_into('<f', rec, 0x28, 1.0)
        rec[0x2c:0x30] = b'\x01\x01\x01\x00'
        struct.pack_into('<ff', rec, 0x30, 0.8, 0.2)
        rec[0:2], rec[4:16], rec[0x10:0x1c], rec[0x28:0x2c] = p[0:2], p[2:14], p[14:26], p[26:30]
        q = 30
        if version >= 1:
            rec[0x2c:0x2e] = p[q:q + 2]
            q += 2
        if version >= 2:
            rec[0x2e] = p[q]
            q += 1
        if version >= 3:
            rec[0x1c:0x28] = p[q:q + 12]
            q += 12
        if version >= 4:
            rec[0x2f] = p[q]
            q += 1
        if version >= 5:
            rec[0x30:0x38] = p[q:q + 8]
        out.append(bytes(rec))
        offset += record_size(version)
    return out


class Record(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int16), ('pad', ctypes.c_uint8 * 2), ('position', ctypes.c_float * 3),
                ('angle', ctypes.c_float * 3), ('vector', ctypes.c_float * 3), ('scale', ctypes.c_float),
                ('flag_2c', ctypes.c_uint8), ('flag_2d', ctypes.c_uint8), ('flag_2e', ctypes.c_uint8),
                ('hidden', ctypes.c_uint8), ('value_30', ctypes.c_float), ('value_34', ctypes.c_float)]


class Header(ctypes.Structure):
    _fields_ = [('version', ctypes.c_uint8), ('map', ctypes.c_uint8), ('count', ctypes.c_int16),
                ('record_size', ctypes.c_int32)]


class ObjectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(HERE)], check=True)
        name = 'libobjects.dylib' if sys.platform == 'darwin' else 'libobjects.so'
        cls.lib = ctypes.CDLL(str(HERE / name))
        cls.lib.mu_objects_parse.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(Header),
                                             ctypes.POINTER(Record), ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
        cls.lib.mu_objects_record_size.argtypes = [ctypes.c_uint8]
        cls.lib.mu_objects_model_file.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_char_p, ctypes.c_size_t]
        cls.lib.mu_objects_folder.argtypes = [ctypes.c_int32]
        cls.lib.mu_bmd12_decode.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]

    def parse(self, plain, capacity=4096):
        header, parsed = Header(), ctypes.c_int32()
        records = (Record * max(capacity, 1))()
        status = self.lib.mu_objects_parse(plain, len(plain), ctypes.byref(header), records, capacity,
                                           ctypes.byref(parsed))
        return status, header, [bytes(records[i]) for i in range(parsed.value)]

    def test_record_sizes(self):
        self.assertEqual([self.lib.mu_objects_record_size(v) for v in range(8)], [30, 32, 33, 45, 46, 54, 54, 54])
        self.assertEqual(self.lib.mu_objects_record_size(255), 54)

    def test_synthetic_files_round_trip(self):
        rng = random.Random(7)
        for version in range(8):
            for count in (0, 1, 2, 9):
                plain = bytes([version, rng.randrange(256)]) + struct.pack('<h', count) + \
                    bytes(rng.randrange(256) for _ in range(count * record_size(version)))
                decoded = ctypes.create_string_buffer(len(plain))
                encoded = v12_encode(plain)
                self.lib.mu_bmd12_decode(decoded, encoded, len(encoded))
                self.assertEqual(decoded.raw, plain)
                status, header, records = self.parse(decoded.raw)
                self.assertEqual(status, OK)
                self.assertEqual((header.version, header.map, header.count), (version, plain[1], count))
                self.assertEqual([r[:2] + b'\0\0' + r[4:] for r in records], expected_records(plain))

    def test_negative_count_reads_nothing(self):
        status, header, records = self.parse(bytes([3, 9]) + struct.pack('<h', -4))
        self.assertEqual((status, header.count, records), (OK, -4, []))

    def test_truncated(self):
        plain = bytes([0, 1]) + struct.pack('<h', 2) + bytes(30 + 29)
        status, header, records = self.parse(plain)
        self.assertEqual(status, TRUNCATED)
        self.assertEqual(len(records), 1)
        self.assertEqual(self.parse(b'\0\1')[0], TRUNCATED)

    def test_capacity_limits_output(self):
        plain = bytes([0, 1]) + struct.pack('<h', 3) + bytes(90)
        status, header, records = self.parse(plain, capacity=2)
        self.assertEqual((status, len(records)), (OK, 2))

    def model(self, world, type_):
        out = ctypes.create_string_buffer(300)
        return out.value.decode() if self.lib.mu_objects_model_file(world, type_, out, 300) else None

    def test_lorencia_table(self):
        self.assertEqual(self.model(0, 0), 'Data/Object1/Tree01.bmd')
        self.assertEqual(self.model(0, 12), 'Data/Object1/Tree13.bmd')
        self.assertIsNone(self.model(0, 13))
        self.assertEqual(self.model(0, 43), 'Data/Object1/SteelStatue01.bmd')
        self.assertEqual(self.model(0, 115), 'Data/Object1/House01.bmd')
        self.assertEqual(self.model(0, 153), 'Data/Object1/Beer03.bmd')
        self.assertIsNone(self.model(0, 299))
        named = sum(self.model(0, t) is not None for t in range(300))
        self.assertEqual(named, 112)

    def test_generic_table_and_folders(self):
        self.assertEqual(self.model(93, 0), 'Data/Object94/Object01.bmd')
        self.assertEqual(self.model(93, 13), 'Data/Object94/Object14.bmd')
        self.assertEqual(self.model(93, 299), 'Data/Object94/Object300.bmd')
        self.assertIsNone(self.model(93, 300))
        self.assertIsNone(self.model(93, -1))
        folders = {w: self.lib.mu_objects_folder(w) for w in range(150)}
        for w in list(range(11, 18)) + [52]:
            self.assertEqual(folders[w], 12)
        for w in list(range(18, 24)) + [53, 97]:
            self.assertEqual(folders[w], 19)
        for w in list(range(24, 30)) + [36]:
            self.assertEqual(folders[w], 25)
        for w in list(range(45, 51)) + [98, 99]:
            self.assertEqual(folders[w], 47)
        self.assertEqual([folders[w] for w in (82, 90, 123, 127, 128, 130, 131, 132, 133)],
                         [83, 83, 124, 124, 131, 131, 132, 133, 134])
        self.assertEqual(folders[1], 2)
        self.assertEqual(self.model(0x80, 0x42), 'Data/Object129/Object67.bmd')
        self.assertEqual(self.model(0x80, 0x41), 'Data/Object131/Object66.bmd')


if __name__ == '__main__':
    unittest.main()
