"""Synthetic social packet regressions, no captured data required."""

import ctypes as C
from pathlib import Path
import struct
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_social import Member, Party, Trade, Friends, Marker, native


class Social(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            ["make", "-C", str(ROOT / "reconstructed/social")],
            check=True,
            capture_output=True,
        )
        cls.l = native(ROOT / "reconstructed/social/libsocial.dylib")

    def test_original_formula_precedence_roundtrip_and_missing_states(self):
        lib = self.l
        lib.mu_social_formula_evaluate.argtypes = [
            C.c_char_p,
            C.c_void_p,
            C.c_size_t,
            C.POINTER(C.c_double),
        ]
        for expression, want in (
            (b"8/2^2", 16.0),
            (b"2^3^2", 64.0),
            (b"1/3*3", 0.9999999999),
        ):
            value = C.c_double()
            self.assertEqual(
                lib.mu_social_formula_evaluate(expression, None, 0, C.byref(value)), 1
            )
            self.assertEqual(value.value, want)
        value = C.c_double(99)
        self.assertEqual(
            lib.mu_social_formula_evaluate(None, None, 0, C.byref(value)), 2
        )
        self.assertEqual(value.value, 0.0)
        for expression in (b"", b"()", b"not an expression", b"1+"):
            self.assertEqual(
                lib.mu_social_formula_evaluate(expression, None, 0, C.byref(value)), 0
            )

    def test_party_transactional_bounds_and_resource_precision(self):
        p = Party()
        r = bytearray(44)
        r[:10] = b"ABCDEFGHIJ"
        r[10] = 4
        r[14] = 3
        r[16:18] = bytes([8, 240])
        struct.pack_into("<4i", r, 20, 51, 200, 1, 0)
        struct.pack_into("<i", r, 36, 100)
        b = b"\xc2\x00\x31\x42\x01" + r
        self.assertEqual(self.l.mu_social_party_receive(C.byref(p), b, len(b)), 1)
        self.assertEqual(
            (p.members[0].name, p.members[0].hp_percent, p.members[0].mp_percent),
            (b"ABCDEFGHIJ", 25, 0),
        )
        before = bytes(p)
        self.assertEqual(
            self.l.mu_social_party_receive(C.byref(p), b[:-1], len(b) - 1), 0
        )
        self.assertEqual(bytes(p), before)
        self.assertEqual(
            self.l.mu_social_party_receive(C.byref(p), b"\xc2\0\0\x42\x06", 5), 0
        )

    def test_bars_match_by_name_and_clamp(self):
        p = Party()
        p.count = 2
        p.members[0].name = b"Hero"
        p.members[1].name = b"Aeris"
        b = b"\xc1\x11\x44\x01\xff\x28" + b"Aeris\0\0\0\0\0\0"
        self.assertEqual(self.l.mu_social_party_receive(C.byref(p), b, len(b)), 1)
        self.assertEqual(
            (p.members[0].hp_percent, p.members[1].hp_percent, p.members[1].mp_percent),
            (0, 100, 40),
        )

    def test_marker_filters_and_clear(self):
        p = Party()
        p.count = 4
        for i, name in enumerate((b"Hero", b"Aeris", b"OtherMap", b"OtherSrv")):
            p.members[i].name = name
            p.members[i].slot = i
            p.members[i].server = 1
            p.members[i].world = 3
            p.members[i].x = 128
            p.members[i].y = 255
        p.members[2].world = 4
        p.members[3].server = 2
        out = (Marker * 5)()
        self.assertEqual(
            self.l.mu_social_party_markers(C.byref(p), b"Hero", 1, 3, out), 1
        )
        self.assertEqual((out[0].key, out[0].x, out[0].y), (1, 256, 2))
        self.l.mu_social_party_receive(C.byref(p), b"\xc1\x04\x43\0", 4)
        self.assertEqual(
            self.l.mu_social_party_markers(C.byref(p), b"Hero", 1, 3, out), 0
        )

    def test_trade_answer_items_money_unlock_and_result(self):
        l = self.l
        l.mu_social_trade_receive.argtypes = [C.POINTER(Trade), C.c_char_p, C.c_size_t]
        t = Trade()
        b = bytearray(20)
        b[:4] = b"\xc1\x14\x54\x01"
        b[4:14] = b"ABCDEFGHIJ"
        struct.pack_into("<Hi", b, 14, 400, 9)
        self.assertEqual(l.mu_social_trade_receive(C.byref(t), bytes(b), len(b)), 1)
        self.assertEqual((t.open, t.name, t.level, t.guild), (1, b"ABCDEFGHIJ", 400, 9))
        b = b"\xc1\x13\x39\x1f" + bytes(range(15))
        l.mu_social_trade_receive(C.byref(t), b, len(b))
        self.assertEqual(bytes(t.items[1][31].bytes), bytes(range(15)))
        before = bytes(t)
        self.assertEqual(l.mu_social_trade_receive(C.byref(t), b[:-1], len(b) - 1), 0)
        self.assertEqual(bytes(t), before)
        l.mu_social_trade_receive(
            C.byref(t), b"\xc1\x08\x3b\0" + struct.pack("<i", 123456), 8
        )
        self.assertEqual(t.zen1, 123456)
        t.ok[0] = 1
        l.mu_social_trade_receive(C.byref(t), b"\xc1\x04\x3e\x02", 4)
        self.assertEqual((tuple(t.ok), t.wait, t.warned), ((0, 0), 25, 1))
        l.mu_social_trade_receive(C.byref(t), b"\xc1\x04\xbd\x01", 4)
        self.assertEqual((t.open, t.result, t.notice), (0, 1, 0))

    def test_friend_names_and_whisper_bounds(self):
        f = Friends()
        b = b"\xc2\0\0\0\0\0\x01" + b"ABCDEFGHIJ\xff"
        self.assertEqual(self.l.mu_social_friends_receive(C.byref(f), b, len(b)), 1)
        self.assertEqual((f.list[0].name, f.list[0].server), (b"ABCDEFGHIJ", 255))
        before = bytes(f)
        self.assertEqual(
            self.l.mu_social_friends_receive(C.byref(f), b[:-1], len(b) - 1), 0
        )
        self.assertEqual(bytes(f), before)
        name = C.create_string_buffer(11)
        text = C.create_string_buffer(61)
        b = b"\xc1\x0e\x02" + b"ABCDEFGHIJ" + b"hello"
        self.assertFalse(self.l.mu_social_whisper(b, len(b), 0, 1, name, text))
        self.assertTrue(self.l.mu_social_whisper(b, len(b), 1, 1, name, text))
        self.assertEqual((name.value, text.value), (b"ABCDEFGHIJ", b"hello"))


if __name__ == "__main__":
    unittest.main()
