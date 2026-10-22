"""Portable checks of reconstructed/progress (NATIVE-PROGRESS-001).

The client comparison is scripts/validate_progress.py (Unicorn, private captures).  These checks build
libprogress and test it against independent statements of the same rules (written here from the
client's instructions, docs/research/client-progression.md): the experience table and the level's
experience, the class stage, a few class formulas, the experience bar's object, the level-up and stat
answers, the "+" button rule and the request's rate limit, and the options window (option.ini, setDatas,
the sound groups).
"""
import ctypes
from ctypes import CFUNCTYPE, POINTER, Structure, c_double, c_int, c_int32, c_uint8, c_uint32, c_void_p
from pathlib import Path
import random
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
LIB = HERE / ('libprogress.dylib' if sys.platform == 'darwin' else 'libprogress.so')

EMIT = CFUNCTYPE(None, c_void_p, ctypes.c_char_p)
TEXT = CFUNCTYPE(c_void_p, c_void_p, c_int32)


class Env(Structure):
    _fields_ = [('user', c_void_p), ('attr', POINTER(c_uint8)), ('hero_class', c_uint8), ('emit', EMIT),
                ('global_text', TEXT), ('has_buff', CFUNCTYPE(c_int, c_void_p, c_int32)),
                ('item_valid', CFUNCTYPE(c_int, c_void_p, c_int32)),
                ('item_weapon_kind', CFUNCTYPE(c_int32, c_void_p, c_int32)),
                ('item_byte38', CFUNCTYPE(c_uint8, c_void_p, c_int32)),
                ('item_is', CFUNCTYPE(c_int, c_void_p, c_int32, c_int32)),
                ('window', CFUNCTYPE(c_int, c_void_p, c_uint32)), ('hero', POINTER(c_uint8)),
                ('character', CFUNCTYPE(c_void_p, c_void_p, c_int32, POINTER(c_int32))),
                ('world_hides_damage', CFUNCTYPE(c_int, c_void_p))]


class BarCache(Structure):
    _fields_ = [('stage', c_int32), ('unused', c_int32), ('exp', ctypes.c_uint64), ('next', ctypes.c_uint64)]


def exp_table(level):
    """0x00a00e79, restated: n = level - 1; (n + 9) n^2 10, plus (m + 9) m^2 1000 (32-bit) above 255."""
    n = level - 1
    if n <= 0:
        return 0
    r = ((n + 9) * n * n * 10) & ((1 << 64) - 1)
    if n > 255:
        m = (n - 255) & 0xffffffff
        t = ((m + 9) * m * m) & 0xffffffff
        t = t - (1 << 32) if t >> 31 else t
        r = (r + t * 1000) & ((1 << 64) - 1)
    r = r - (1 << 64) if r >> 63 else r
    return max(r, 0)


class Lib:
    def __init__(self):
        subprocess.run(['make', '-s', '-C', str(HERE)], check=True)
        L = self.L = ctypes.CDLL(str(LIB))
        L.mu_prg_exp_table.argtypes = [ctypes.c_int64]
        L.mu_prg_exp_table.restype = ctypes.c_int64
        L.mu_prg_level_exp.argtypes = [POINTER(c_uint8)]
        L.mu_prg_class_stage.argtypes = [c_uint8]
        L.mu_prg_effective_level.argtypes = [POINTER(c_uint8)]
        L.mu_prg_calc_class.argtypes = [POINTER(Env), c_int, POINTER(c_int32 * 5)]
        L.mu_prg_exp_bar.argtypes = [POINTER(Env), POINTER(BarCache), c_int32]
        L.mu_prg_stat_button.argtypes = [POINTER(c_uint8), c_double]
        L.mu_prg_stat_button.restype = c_int32
        L.mu_prg_stat_request.argtypes = [POINTER(Env), POINTER(c_uint32), c_uint32, c_int32, POINTER(c_uint8 * 5)]
        for name in ('mu_prg_recv_levelup', 'mu_prg_recv_point'):
            getattr(L, name).argtypes = [POINTER(Env), POINTER(c_uint8 * 0x100)]
        self.lines = []
        self.keep = []

    def env(self, attr, hero_class=0, buffs=()):
        self.lines = []
        e = Env()
        e.attr = ctypes.cast(attr, POINTER(c_uint8))
        e.hero_class = hero_class
        e.emit = EMIT(lambda u, line: self.lines.append(line.decode('latin1')))
        texts = {}

        def text(u, i):
            texts[i] = ctypes.create_string_buffer(b'GT%d %%lld' % i)
            return ctypes.addressof(texts[i])
        e.global_text = TEXT(text)
        e.has_buff = Env._fields_[5][1](lambda u, b: int(b in buffs))
        e.window = Env._fields_[10][1](lambda u, g: 1)
        self.keep = [e, texts]
        return e


def attr_buffer(level=1, cls=0, stats=(20, 20, 20, 20, 0), add=(0, 0, 0, 0, 0)):
    a = (c_uint8 * 0x200)()
    struct.pack_into('<i', a, 0, level)
    a[0x187] = cls
    for off, v in zip((0x18a, 0x18c, 0x18e, 0x190, 0x192), stats):
        struct.pack_into('<H', a, off, v)
    for off, v in zip((0x198, 0x19a, 0x19c, 0x19e, 0x1a4), add):
        struct.pack_into('<H', a, off, v)
    return a


def u16(a, off):
    return struct.unpack_from('<H', a, off)[0]


class Progress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = Lib()

    def test_exp_table(self):
        rng = random.Random(1)
        for level in list(range(-3, 1200)) + [rng.randint(-(1 << 40), 1 << 40) for _ in range(200)]:
            self.assertEqual(self.lib.L.mu_prg_exp_table(level), exp_table(level), level)
        self.assertEqual(exp_table(2), 100)

    def test_level_experience(self):
        a = attr_buffer(level=57)
        struct.pack_into('<QQ', a, 8, 123, 456)
        self.lib.L.mu_prg_level_exp(a)
        self.assertEqual(struct.unpack_from('<QQ', a, 8), (0, exp_table(58) - exp_table(57)))

    def test_class_stage(self):
        for b in range(256):
            v = b >> 4
            want = 1 if not v else max(i + 2 for i in range(4) if v >> i & 1)
            self.assertEqual(self.lib.L.mu_prg_class_stage(b), want, b)

    def test_effective_level_counts_master_only_for_third_class(self):
        a = attr_buffer(level=400, cls=0x21)
        struct.pack_into('<i', a, 0x18, 77)
        self.assertEqual(self.lib.L.mu_prg_effective_level(a), 477)
        a[0x187] = 0x11
        self.assertEqual(self.lib.L.mu_prg_effective_level(a), 400)

    def test_dark_wizard_formula(self):
        a = attr_buffer(level=100, cls=0, stats=(120, 90, 50, 300, 0), add=(10, 6, 0, 30, 0))
        e = self.lib.env(a)
        extra = (c_int32 * 5)(2, 4, 0, 6, 0)
        self.lib.L.mu_prg_calc_class(ctypes.byref(e), 0, ctypes.byref(extra))
        s, d, n = 132, 100, 336
        self.assertEqual([u16(a, o) for o in (0x1ba, 0x1bc, 0x1be, 0x1c0)], [s // 8, s // 4, s // 8, s // 4])
        self.assertEqual((u16(a, 0x1c4), u16(a, 0x1c6)), (n // 9, n // 4))
        self.assertEqual(u16(a, 0x1b8), 100 * 5 + d * 3 // 2 + s // 4)
        self.assertEqual(u16(a, 0x194), int(100 * 3.0 + d * 4.0))
        self.assertEqual((u16(a, 0x1dc), u16(a, 0x1da)), (d // 4, d // 3))
        self.assertEqual(u16(a, 0x196), int(100 * 2.0 + d * 0.25))

    def test_dark_knight_buff(self):
        a = attr_buffer(level=50, cls=1, stats=(900, 300, 100, 30, 0))
        e = self.lib.env(a, buffs=(0x145,))
        zero = (c_int32 * 5)()
        self.lib.L.mu_prg_calc_class(ctypes.byref(e), 1, ctypes.byref(zero))
        self.assertEqual((u16(a, 0x1ba), u16(a, 0x1bc)), (900 // 9, 900 // 6))
        self.assertEqual(u16(a, 0x1dc), 300 // 2)
        e = self.lib.env(a)
        self.lib.L.mu_prg_calc_class(ctypes.byref(e), 1, ctypes.byref(zero))
        self.assertEqual((u16(a, 0x1ba), u16(a, 0x1bc)), (900 // 6, 900 // 4))
        self.assertEqual(u16(a, 0x1dc), 300 // 3)

    def test_stats_are_sixteen_bit(self):
        a = attr_buffer(level=1, cls=8, stats=(0xfff0, 10, 10, 10, 0), add=(0x20, 0, 0, 0, 0))
        e = self.lib.env(a)
        zero = (c_int32 * 5)()
        self.lib.L.mu_prg_calc_class(ctypes.byref(e), 8, ctypes.byref(zero))
        self.assertEqual(u16(a, 0x1ba), 0x10 // 8)   # (0xfff0 + 0x20) & 0xffff = 0x10

    def test_exp_bar_object(self):
        a = attr_buffer(level=10)
        struct.pack_into('<QQ', a, 8, 1234, 5000)
        e = self.lib.env(a, hero_class=0x01)
        self.assertEqual(self.lib.L.mu_prg_exp_bar(ctypes.byref(e), None, 1350), 1)
        seg = 5000 / 10
        page = int(1234 / seg)
        rate = int((1234 - page * seg) / seg * 100)
        self.assertEqual(self.lib.lines, ['invoke setExpData {"ClassLevel":1,"curExp":"1234","maxExp":"5000",'
                                          '"page":%d,"rate":%d}' % (page, rate)])
        cache = BarCache(1, 0, 1234, 5000)
        self.assertEqual(self.lib.L.mu_prg_exp_bar(ctypes.byref(e), ctypes.byref(cache), 1350), 0)

    def test_exp_bar_master_full(self):
        a = attr_buffer(level=400, cls=0x21)
        struct.pack_into('<i', a, 0x18, 1350)
        struct.pack_into('<QQ', a, 0x20, 10, 20)
        e = self.lib.env(a, hero_class=0x21)
        self.lib.L.mu_prg_exp_bar(ctypes.byref(e), None, 1350)
        self.assertEqual(self.lib.lines, ['invoke setExpData {"ClassLevel":3,"curExp":"0","maxExp":"0","page":0,"rate":0}'])

    def test_level_up_answer(self):
        a = attr_buffer(level=9)
        struct.pack_into('<QQ', a, 8, 100, 900)
        p = (c_uint8 * 0x100)(*([0xc1, 0x18, 0xa0, 0x06] + [0] * 0xfc))
        struct.pack_into('<8H', p, 4, 10, 5, 300, 0, 200, 50, 7, 8)
        e = self.lib.env(a, hero_class=0x01)
        self.lib.L.mu_prg_recv_levelup(ctypes.byref(e), p)
        self.assertEqual(struct.unpack_from('<i', a, 0)[0], 10)
        self.assertEqual(u16(a, 0x1e2), 5)
        # HP, MP (at least 0), HP max, MP max (at least 1), +0x78, SD max
        self.assertEqual(struct.unpack_from('<6i', a, 0x68), (300, 0, 300, 1, 0, 200))
        self.assertEqual(struct.unpack_from('<i', a, 0x7c)[0], 200)
        self.assertEqual(struct.unpack_from('<i', a, 0x84)[0], 50)
        self.assertIn('call 01219a39 "GT486 800"', self.lib.lines)
        self.assertEqual(sum(1 for l in self.lib.lines if l.startswith('call 0153b02c 7f78')), 15)
        self.assertEqual(self.lib.lines[-1], 'call 00a6ac96 98 0 0')
        self.assertIn('call 013c0eaa 7f84 o+158 o+164 o+ec 0 o ffffffff 0 0 0 00000000 ffffffff 0 0', self.lib.lines)

    def test_level_is_capped(self):
        a = attr_buffer(level=399)
        p = (c_uint8 * 0x100)()
        struct.pack_into('<H', p, 4, 401)
        e = self.lib.env(a)
        self.lib.L.mu_prg_recv_levelup(ctypes.byref(e), p)
        self.assertEqual(struct.unpack_from('<i', a, 0)[0], 400)

    def test_point_answer(self):
        a = attr_buffer()
        struct.pack_into('<H', a, 0x1e2, 3)
        p = (c_uint8 * 0x100)()
        p[4] = 0x12
        struct.pack_into('<3H', p, 6, 500, 60, 70)
        e = self.lib.env(a)
        self.lib.L.mu_prg_recv_point(ctypes.byref(e), p)
        self.assertEqual(u16(a, 0x1e2), 2)
        self.assertEqual(struct.unpack_from('<i', a, 0x70)[0], 500)
        self.assertEqual((struct.unpack_from('<i', a, 0x7c)[0], struct.unpack_from('<i', a, 0x84)[0]), (60, 70))
        p[4] = 0x02   # refused: nothing changes, the point text refreshes
        e = self.lib.env(a)
        self.lib.L.mu_prg_recv_point(ctypes.byref(e), p)
        self.assertEqual(u16(a, 0x1e2), 2)
        self.assertEqual(self.lib.lines, ['call 00b458f2'])

    def test_button_rows(self):
        a = attr_buffer()
        self.assertEqual(self.lib.L.mu_prg_stat_button(a, 8.0), -1)   # no points
        struct.pack_into('<H', a, 0x1e2, 1)
        for row, stat in ((8.0, 0), (13.0, 1), (24.0, 2), (29.0, 3), (42.0, 4), (9.0, -1), (8.5, -1)):
            self.assertEqual(self.lib.L.mu_prg_stat_button(a, row), stat, row)
        struct.pack_into('<H', a, 0x1e2, 0x8000)   # the word is tested as a zero-extended value
        self.assertEqual(self.lib.L.mu_prg_stat_button(a, 42.0), 4)

    def test_request_rate_limit(self):
        a = attr_buffer()
        e = self.lib.env(a)
        last = c_uint32(1000)
        out = (c_uint8 * 5)()
        self.assertEqual(self.lib.L.mu_prg_stat_request(ctypes.byref(e), ctypes.byref(last), 1099, 2, out), 0)
        self.assertEqual(self.lib.L.mu_prg_stat_request(ctypes.byref(e), ctypes.byref(last), 1100, 2, out), 5)
        self.assertEqual(list(out), [0xc1, 5, 0x01, 0x00, 2])
        self.assertEqual(last.value, 1100)
        self.assertEqual(self.lib.lines, ['call 00d51d4f 0 0', 'call 00a6ac96 19 0 0'])
        last.value = 0xffffffff   # the unsigned difference wraps
        self.assertEqual(self.lib.L.mu_prg_stat_request(ctypes.byref(e), ctypes.byref(last), 98, 0, out), 0)
        self.assertEqual(self.lib.L.mu_prg_stat_request(ctypes.byref(e), ctypes.byref(last), 99, 0, out), 5)


if __name__ == '__main__':
    unittest.main()
