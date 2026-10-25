"""Portable checks of the C3/C4 CryptoModule module (NET-CRYPTO-001).

Synthetic data only; built and run in CI on macOS and Linux. No client bytes and no Unicorn.
Three kinds of check through the C ABI (native/build/libmucrypto, ctypes):

1. Known-answer tests for every one of the 17 factory cases, each anchored to something other
   than the library under test: published single-block vectors for the ten ciphers that have
   them (cited inline), compact independent reference implementations for RC5, GOST, SAFER-K
   and SAFER-SK, and structural builders over the verified DES case for DES-EDE2 and DES-XEX3.
   GOST(3) and GOST(8) are the same cipher reached at two factory indices.

2. Encrypt/decrypt round trips for every case over many lengths: the class Encrypt then Decrypt
   returns the plaintext, the output grows by pad + 1, and the length and pad rules hold.

3. Full-module round trips across rekey boundaries: an ENC map and a mirror DEC map, keyed from
   the same seed, exchange many packets per channel; every packet decrypts to its plaintext,
   the per-direction counters and the 128-byte state track each other, and both ends rekey
   together at the cipher's interval (8, 0x20 and the long 0x800).

The bit-exact agreement with the client's own instructions is a separate, private check
(scripts/validate_crypto.py, Unicorn; tests/test_crypto_private.py gates it on
MU_RECOVERY_INTEGRATION).
"""
import ctypes
import os
import random
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
LIB = NATIVE/'build'/f'libmucrypto.{SUFFIX}'

MU_CRYPTO_ENC, MU_CRYPTO_DEC, MU_CRYPTO_OUTSIDE = 0, 1, -2
CASES = ['TEA', '3-Way', 'CAST-128', 'GOST(3)', 'RC5', 'RC6', 'MARS', 'IDEA', 'GOST(8)', 'Twofish', 'DES',
         'DES-EDE2', 'DES-EDE3', 'DES-XEX3', 'SKIPJACK', 'SAFER-K', 'SAFER-SK']
BLOCK = [8, 12, 8, 8, 8, 16, 16, 8, 8, 16, 8, 8, 8, 8, 8, 8, 8]
KEYLEN = [16, 12, 16, 32, 16, 16, 16, 16, 32, 16, 8, 16, 24, 24, 10, 16, 16]
INTERVAL = [0x800]*9 + [8, 8, 8, 0x20, 8, 0x20, 8, 0x20]


def build():
    subprocess.run(['make', '-C', str(NATIVE), str(LIB.relative_to(NATIVE))], check=True, capture_output=True)


class Lib:
    def __init__(self):
        lib = self.lib = ctypes.CDLL(str(LIB))
        P, I32, U32, SZ, B = ctypes.c_void_p, ctypes.c_int32, ctypes.c_uint32, ctypes.c_size_t, ctypes.c_char_p
        lib.mu_crypto_new.restype = P
        lib.mu_crypto_free.argtypes = [P]
        lib.mu_crypto_open.argtypes = [P, ctypes.c_int, I32]
        lib.mu_crypto_call.argtypes = [P, ctypes.c_int, I32, P, SZ, B, SZ]
        lib.mu_crypto_call.restype = I32
        lib.mu_crypto_run.argtypes = [P, ctypes.c_int, I32, B, SZ, SZ, ctypes.POINTER(SZ)]
        lib.mu_crypto_run.restype = ctypes.c_int
        lib.mu_crypto_enc_count.argtypes = lib.mu_crypto_dec_count.argtypes = [P, ctypes.c_int, I32]
        lib.mu_crypto_enc_count.restype = lib.mu_crypto_dec_count.restype = I32
        lib.mu_crypto_cipher_new.argtypes = [U32, B, SZ]
        lib.mu_crypto_cipher_new.restype = P
        lib.mu_crypto_cipher_free.argtypes = [P]
        lib.mu_crypto_cipher_case.argtypes = [P]
        lib.mu_crypto_cipher_case.restype = I32
        lib.mu_crypto_cipher_interval.argtypes = lib.mu_crypto_cipher_block.argtypes = [P]
        lib.mu_crypto_cipher_interval.restype = lib.mu_crypto_cipher_block.restype = U32
        for name in ('mu_crypto_cipher_encrypt', 'mu_crypto_cipher_decrypt'):
            getattr(lib, name).argtypes = [P, P, SZ, B, SZ]
            getattr(lib, name).restype = I32
        lib.mu_crypto_block.argtypes = [I32, ctypes.c_int, B, SZ, B, B]
        lib.mu_crypto_block.restype = ctypes.c_int

    def block(self, case, decrypt, key, data):
        out = ctypes.create_string_buffer(len(data))
        r = self.lib.mu_crypto_block(case, 1 if decrypt else 0, key, len(key), data, out)
        return r, out.raw[:len(data)]


# ---- independent references --------------------------------------------------------------------

M = 0xffffffff


def rotl(x, n):
    n &= 31
    return ((x << n) | (x >> (32 - n))) & M if n else x & M


def ref_rc5(key, pt, rounds=16):
    """Rivest's RC5-32/r/b key schedule and round function (RFC 2040 / the original paper)."""
    c = max(1, (len(key) + 3)//4)
    words = [int.from_bytes(key[4*i:4*i + 4].ljust(4, b'\0'), 'little') for i in range(c)]
    t = 2*rounds + 2
    s = [(0xB7E15163 + i*0x9E3779B9) & M for i in range(t)]
    a = b = i = j = 0
    for _ in range(3*max(t, c)):
        a = s[i] = rotl((s[i] + a + b) & M, 3)
        b = words[j] = rotl((words[j] + a + b) & M, a + b)
        i, j = (i + 1) % t, (j + 1) % c
    x = (int.from_bytes(pt[:4], 'little') + s[0]) & M
    y = (int.from_bytes(pt[4:], 'little') + s[1]) & M
    for r in range(1, rounds + 1):
        x = (rotl(x ^ y, y) + s[2*r]) & M
        y = (rotl(y ^ x, x) + s[2*r + 1]) & M
    return x.to_bytes(4, 'little') + y.to_bytes(4, 'little')


_GOST_SBOX = [[4, 10, 9, 2, 13, 8, 0, 14, 6, 11, 1, 12, 7, 15, 5, 3],
              [14, 11, 4, 12, 6, 13, 15, 10, 2, 3, 8, 1, 0, 7, 5, 9],
              [5, 8, 1, 13, 10, 3, 4, 2, 14, 15, 12, 7, 6, 0, 9, 11],
              [7, 13, 10, 1, 0, 8, 9, 15, 14, 4, 6, 12, 11, 2, 5, 3],
              [6, 12, 7, 1, 5, 15, 13, 8, 4, 10, 9, 14, 0, 3, 11, 2],
              [4, 11, 10, 0, 7, 2, 1, 13, 3, 6, 8, 5, 9, 12, 15, 14],
              [13, 11, 4, 1, 3, 15, 5, 9, 0, 10, 14, 7, 6, 8, 2, 12],
              [1, 15, 13, 0, 5, 7, 10, 4, 9, 2, 3, 14, 6, 11, 8, 12]]


def ref_gost(key, pt):
    """GOST 28147-89 with Crypto++'s default S-box (the one its GOST class ships with)."""
    k = [int.from_bytes(key[4*i:4*i + 4], 'little') for i in range(8)]

    def f(x):
        y = 0
        for i in range(8):
            y |= _GOST_SBOX[i][(x >> (4*i)) & 15] << (4*i)
        return rotl(y, 11)
    n1, n2 = int.from_bytes(pt[:4], 'little'), int.from_bytes(pt[4:], 'little')
    order = k*3 + k[::-1]
    for i in range(0, 32, 2):
        n2 ^= f((n1 + order[i]) & M)
        n1 ^= f((n2 + order[i + 1]) & M)
    return n2.to_bytes(4, 'little') + n1.to_bytes(4, 'little')


_EXP = [0]*256
_v = 1
for _i in range(256):
    _EXP[_i] = _v & 0xff
    _v = (_v*45) % 257
_LOG = [0]*256
for _i in range(256):
    _LOG[_EXP[_i]] = _i


def _r8(x, n):
    return ((x << n) | (x >> (8 - n))) & 0xff


def ref_safer(key, pt, strengthened):
    """SAFER K-64/SK-64 style schedule and round (Massey), 10 rounds, as Crypto++'s SAFER_K /
    SAFER_SK with the 16-byte key split into two halves."""
    rounds = 10
    k1, k2 = key[:8], key[8:16]
    rk = [rounds]
    ka, kb = [0]*9, [0]*9
    for j in range(8):
        ka[j] = _r8(k1[j], 5)
        ka[8] ^= ka[j]
        kb[j] = k2[j]
        kb[8] ^= kb[j]
        rk.append(k2[j])
    for i in range(1, rounds + 1):
        for j in range(9):
            ka[j] = _r8(ka[j], 6)
            kb[j] = _r8(kb[j], 6)
        for j in range(8):
            rk.append((ka[(j + 2*i - 1) % 9] if strengthened else ka[j]) + _EXP[_EXP[18*i + j + 1]] & 0xff)
        for j in range(8):
            rk.append((kb[(j + 2*i) % 9] if strengthened else kb[j]) + _EXP[_EXP[18*i + j + 10]] & 0xff)
    a, b, c, d, e, f, g, h = pt
    k = 1
    for _ in range(rounds):
        a ^= rk[k]; b = (b + rk[k+1]) & 255; c = (c + rk[k+2]) & 255; d ^= rk[k+3]
        e ^= rk[k+4]; f = (f + rk[k+5]) & 255; g = (g + rk[k+6]) & 255; h ^= rk[k+7]
        a = (_EXP[a] + rk[k+8]) & 255; b = _LOG[b] ^ rk[k+9]; c = _LOG[c] ^ rk[k+10]; d = (_EXP[d] + rk[k+11]) & 255
        e = (_EXP[e] + rk[k+12]) & 255; f = _LOG[f] ^ rk[k+13]; g = _LOG[g] ^ rk[k+14]; h = (_EXP[h] + rk[k+15]) & 255
        k += 16

        def pht(x, y):
            y = (y + x) & 255
            return (x + y) & 255, y
        a, b = pht(a, b); c, d = pht(c, d); e, f = pht(e, f); g, h = pht(g, h)
        a, c = pht(a, c); e, g = pht(e, g); b, d = pht(b, d); f, h = pht(f, h)
        a, e = pht(a, e); b, f = pht(b, f); c, g = pht(c, g); d, h = pht(d, h)
        b, e, c = e, c, b
        d, f, g = f, g, d
    a ^= rk[k]; b = (b + rk[k+1]) & 255; c = (c + rk[k+2]) & 255; d ^= rk[k+3]
    e ^= rk[k+4]; f = (f + rk[k+5]) & 255; g = (g + rk[k+6]) & 255; h ^= rk[k+7]
    return bytes([a, b, c, d, e, f, g, h])


def xor(a, b):
    return bytes(i ^ j for i, j in zip(a, b))


def h(s):
    return bytes.fromhex(s)


# Published single-block vectors (key, plaintext, ciphertext), cited. Verified independently of
# the module under test. Structural / reference cases are checked in the test methods below.
PUBLISHED = {
    'TEA': (h('00000000000000000000000000000000'), h('0000000000000000'), h('41ea3a0a94baa940')),
    # Daemen 3-Way reference vectors (words shown in Crypto++ byte order).
    '3-Way-a': (h('000000000000000000000000'), h('000000010000000100000001'), h('4059c76e83ae9dc4ad21ecf7')),
    '3-Way-b': (h('000000060000000500000004'), h('000000030000000200000001'), h('d2f05b5ed6144138cab920cd')),
    'CAST-128': (h('0123456712345678234567893456789a'), h('0123456789abcdef'), h('238b4fe5847e44b2')),   # RFC 2144
    'RC6': (h('00000000000000000000000000000000'), h('00000000000000000000000000000000'),
            h('8fc3a53656b1f778c129df4e9848a41e')),   # RC6 AES-submission zero vector
    'MARS': (h('00000000000000000000000000000000'), h('00000000000000000000000000000000'),
             h('dcc07b8dfb0738d6e30a22dfcf27e886')),   # MARS AES-submission zero vector
    'IDEA': (h('00010002000300040005000600070008'), h('0000000100020003'), h('11fbed2b01986de5')),
    'Twofish': (h('00000000000000000000000000000000'), h('00000000000000000000000000000000'),
                h('9f589f5cf6122c32b6bfec2f2ae8c35a')),   # Twofish AES-submission zero vector
    'DES': (h('0123456789abcdef'), h('4e6f772069732074'), h('3fa40e8a984d4815')),   # FIPS PUB 81
    # NIST "SKIPJACK and KEA" spec example, in Crypto++'s byte order.
    'SKIPJACK': (h('11223344556677889900'), h('aabbccdd00112233'), h('00d3127ae2ca8725')),
    'DES-EDE3': (h('0123456789abcdef23456789abcdef01456789abcdef0123'), h('5468652071756663'),
                 h('a826fd8ce53b855f')),   # NIST SP 800-67 example
}


class KnownAnswerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()
        cls.m = Lib()

    def _kat(self, case, key, pt, ct):
        r, got = self.m.block(case, False, key, pt)
        self.assertEqual(r, 0, CASES[case])
        self.assertEqual(got, ct, f'{CASES[case]} encrypt')
        r, back = self.m.block(case, True, key, ct)
        self.assertEqual((r, back), (0, pt), f'{CASES[case]} decrypt')

    def test_published_vectors(self):
        self._kat(0, *PUBLISHED['TEA'])
        self._kat(1, *PUBLISHED['3-Way-a'])
        self._kat(1, *PUBLISHED['3-Way-b'])
        self._kat(2, *PUBLISHED['CAST-128'])
        self._kat(5, *PUBLISHED['RC6'])
        self._kat(6, *PUBLISHED['MARS'])
        self._kat(7, *PUBLISHED['IDEA'])
        self._kat(9, *PUBLISHED['Twofish'])
        self._kat(10, *PUBLISHED['DES'])
        self._kat(12, *PUBLISHED['DES-EDE3'])
        self._kat(14, *PUBLISHED['SKIPJACK'])

    def test_rc5_rivest_vectors(self):
        # RFC 2040 / Rivest RC5-32/12/16 reference vectors (12 rounds).
        vectors = [('00000000000000000000000000000000', '0000000000000000', '21a5dbee154b8f6d'),
                   ('915f4619be41b2516355a50110a9ce91', '21a5dbee154b8f6d', 'f7c013ac5b2b8952'),
                   ('783348e75aeb0f2fd7b169bb8dc16787', 'f7c013ac5b2b8952', '2f42b3b70369fc92'),
                   ('dc49db1375a5584f6485b413b5f12baf', '2f42b3b70369fc92', '65c178b284d197cc'),
                   ('5269f149d41ba0152497574d7f153125', '65c178b284d197cc', 'eb44e415da319824')]
        for k, p, c in vectors:
            self.assertEqual(ref_rc5(h(k), h(p), 12).hex(), c, 'RC5 reference vs RFC 2040')

    def test_rc5_reference(self):
        rng = random.Random(0x5c5)
        for _ in range(64):
            key, pt = rng.randbytes(16), rng.randbytes(8)   # Crypto++ RC5 default is 16 rounds
            self.assertEqual(self.m.block(4, False, key, pt)[1], ref_rc5(key, pt, 16))

    def test_gost_reference(self):
        rng = random.Random(0x905)
        for _ in range(64):
            key, pt = rng.randbytes(32), rng.randbytes(8)
            self.assertEqual(self.m.block(3, False, key, pt)[1], ref_gost(key, pt))   # index 3
            self.assertEqual(self.m.block(8, False, key, pt)[1], ref_gost(key, pt))   # index 8, same cipher

    def test_safer_reference(self):
        rng = random.Random(0x5afe)
        for _ in range(64):
            key, pt = rng.randbytes(16), rng.randbytes(8)
            self.assertEqual(self.m.block(15, False, key, pt)[1], ref_safer(key, pt, False), 'SAFER-K')
            self.assertEqual(self.m.block(16, False, key, pt)[1], ref_safer(key, pt, True), 'SAFER-SK')

    def test_des_variants_structural(self):
        # DES-EDE2 and DES-XEX3 built on the published DES case (index 10) and its key split.
        rng = random.Random(0xde5)
        for _ in range(64):
            k16, k24, pt = rng.randbytes(16), rng.randbytes(24), rng.randbytes(8)
            ede2 = self.m.block(10, False, k16[0:8], self.m.block(10, True, k16[8:16],
                                self.m.block(10, False, k16[0:8], pt)[1])[1])[1]
            self.assertEqual(self.m.block(11, False, k16, pt)[1], ede2, 'DES-EDE2 = E_k1 D_k2 E_k1')
            # DES-XEX3 = k[16:24] XOR DES_{k[8:16]}(pt XOR k[0:8]) (empirically the Crypto++ key split)
            xex3 = xor(k24[16:24], self.m.block(10, False, k24[8:16], xor(pt, k24[0:8]))[1])
            self.assertEqual(self.m.block(13, False, k24, pt)[1], xex3, 'DES-XEX3 whitening + DES')

    def test_every_case_reached(self):
        seen = set()
        for case in range(17):
            key = bytes(range(KEYLEN[case]))
            r, _ = self.m.block(case, False, key, bytes(BLOCK[case]))
            self.assertEqual(r, 0, CASES[case])
            seen.add(case)
        self.assertEqual(seen, set(range(17)), 'all 17 factory cases reached')

    def test_factory_index_9_sub_ciphers(self):
        # Factory index 9 selects the sub-cipher from key[0] & 7; cases 9..16 must all appear.
        seen = {}
        for sub in range(8):
            key = bytearray(32)
            key[0] = sub
            handle = self.m.lib.mu_crypto_cipher_new(9, bytes(key), 32)
            self.assertTrue(handle)
            seen[sub] = self.m.lib.mu_crypto_cipher_case(handle)
            self.m.lib.mu_crypto_cipher_free(handle)
        self.assertEqual(seen, {sub: 9 + sub for sub in range(8)})

    def test_bad_case_rejected(self):
        r, _ = self.m.block(17, False, bytes(16), bytes(8))
        self.assertEqual(r, -1)
        r, _ = self.m.block(-1, False, bytes(16), bytes(8))
        self.assertEqual(r, -1)


class RoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()
        cls.m = Lib()

    def test_wrapper_round_trip_and_padding(self):
        rng = random.Random(0x12345)
        for case in range(17):
            block = BLOCK[case]
            handle = None
            # Reach the case with a key of its own length (index 9 sub-cipher via key[0] & 7).
            index = case if case < 9 else 9
            key = bytearray(rng.randbytes(64))
            if case >= 9:
                key[0] = (key[0] & ~7) | (case - 9)
            handle = self.m.lib.mu_crypto_cipher_new(index, bytes(key), 64)
            self.assertTrue(handle, CASES[case])
            try:
                self.assertEqual(self.m.lib.mu_crypto_cipher_case(handle), case)
                self.assertEqual(self.m.lib.mu_crypto_cipher_block(handle), block)
                self.assertEqual(self.m.lib.mu_crypto_cipher_interval(handle), INTERVAL[case])
                # Length 0 is special: Encrypt yields the pad byte alone and Decrypt then
                # recovers length 0, which the client rejects (-1). Checked separately.
                empty = ctypes.create_string_buffer(0x1100)
                n0 = self.m.lib.mu_crypto_cipher_encrypt(handle, ctypes.cast(empty, ctypes.c_void_p), 0x1100, b'', 0)
                self.assertEqual(n0, 1, f'{CASES[case]} empty encrypt is one pad byte')
                self.assertEqual(self.m.lib.mu_crypto_cipher_decrypt(handle, ctypes.cast(empty, ctypes.c_void_p),
                                 0x1100, empty.raw[:1], 1), -1, 'empty plaintext does not round-trip')
                for length in [1, block - 1, block, block + 1, 2*block, 7, 8, 9, 37, 63, 200, 0xf00]:
                    plain = rng.randbytes(length)
                    out = ctypes.create_string_buffer(0x1100)
                    n = self.m.lib.mu_crypto_cipher_encrypt(handle, ctypes.cast(out, ctypes.c_void_p), 0x1100,
                                                            plain, length)
                    pad = (block - length % block) % block
                    self.assertEqual(n, length + 1 + pad, f'{CASES[case]} len {length}')
                    self.assertEqual(out.raw[n - 1], pad, 'trailing pad-count byte')
                    size_only = self.m.lib.mu_crypto_cipher_encrypt(handle, None, 0, plain, length)
                    self.assertEqual(size_only, n, 'size query')
                    back = ctypes.create_string_buffer(0x1100)
                    r = self.m.lib.mu_crypto_cipher_decrypt(handle, ctypes.cast(back, ctypes.c_void_p), 0x1100,
                                                            out.raw[:n], n)
                    self.assertEqual(r, length, f'{CASES[case]} decrypt length')
                    self.assertEqual(back.raw[:length], plain, f'{CASES[case]} round trip')
            finally:
                self.m.lib.mu_crypto_cipher_free(handle)

    def test_decrypt_length_rule(self):
        handle = self.m.lib.mu_crypto_cipher_new(10, bytes(8), 8)   # DES, block 8
        try:
            # len % block must be 1; anything else is -1.
            for length in (0, 8, 9, 16, 17):
                r = self.m.lib.mu_crypto_cipher_decrypt(handle, None, 0, bytes(length), length)
                self.assertEqual(r >= 0, length % 8 == 1, f'len {length}')
        finally:
            self.m.lib.mu_crypto_cipher_free(handle)


class ModuleRekeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()
        cls.m = Lib()

    def _exchange(self, channel, packets, rng):
        """An ENC map and a mirror DEC map, both from the seed on the same channel: every packet
        the sender encrypts the receiver decrypts to the plaintext, across rekey boundaries."""
        m = self.m.lib
        sender, receiver = m.mu_crypto_new(), m.mu_crypto_new()
        try:
            self.assertEqual(m.mu_crypto_open(sender, MU_CRYPTO_ENC, channel), 1)
            self.assertEqual(m.mu_crypto_open(receiver, MU_CRYPTO_DEC, channel), 1)
            rekeys = 0
            for i in range(packets):
                plain = rng.randbytes(rng.randrange(1, 48))
                enc = (m.mu_crypto_enc_count(sender, MU_CRYPTO_ENC, channel),)
                before = m.mu_crypto_enc_count(sender, MU_CRYPTO_ENC, channel)
                out = ctypes.create_string_buffer(0x1100)
                n = m.mu_crypto_call(sender, MU_CRYPTO_ENC, channel, ctypes.cast(out, ctypes.c_void_p), 0x1100,
                                     plain, len(plain))
                self.assertGreater(n, 0)
                back = ctypes.create_string_buffer(0x1100)
                r = m.mu_crypto_call(receiver, MU_CRYPTO_DEC, channel, ctypes.cast(back, ctypes.c_void_p), 0x1100,
                                     out.raw[:n], n)
                self.assertEqual(r, len(plain), f'packet {i} length')
                self.assertEqual(back.raw[:len(plain)], plain, f'packet {i} content')
                self.assertEqual(m.mu_crypto_enc_count(sender, MU_CRYPTO_ENC, channel),
                                 m.mu_crypto_dec_count(receiver, MU_CRYPTO_DEC, channel),
                                 'the two ends keep the same counter')
                after = m.mu_crypto_enc_count(sender, MU_CRYPTO_ENC, channel)
                if after < before:
                    rekeys += 1
            return rekeys
        finally:
            m.mu_crypto_free(sender)
            m.mu_crypto_free(receiver)

    def test_round_trip_short(self):
        # A short exchange on the socket channel (the seed's cipher, DES-XEX3, interval 0x20):
        # every packet round-trips; the first 0x20 boundary may already rekey both ends in step.
        rng = random.Random(1)
        self.assertGreaterEqual(self._exchange(0x06fca2d8, 30, rng), 0)

    def test_round_trip_across_rekey(self):
        # Many packets cross several rekey boundaries; every packet still round-trips because the
        # two ends evolve the same 128-byte state and rekey to the same cipher together.
        rng = random.Random(2)
        self.assertGreaterEqual(self._exchange(7, 0x900, rng), 2)

    def test_run_in_place(self):
        # mu_crypto_run (the sketch's in-place form) agrees with mu_crypto_call.
        m = self.m.lib
        enc, dec = m.mu_crypto_new(), m.mu_crypto_new()
        try:
            m.mu_crypto_open(enc, MU_CRYPTO_ENC, 3)
            m.mu_crypto_open(dec, MU_CRYPTO_DEC, 3)
            rng = random.Random(3)
            for _ in range(32):
                plain = rng.randbytes(rng.randrange(1, 40))
                buf = ctypes.create_string_buffer(plain, 0x1100)
                out_len = ctypes.c_size_t()
                rc = m.mu_crypto_run(enc, MU_CRYPTO_ENC, 3, buf, len(plain), 0x1100, ctypes.byref(out_len))
                self.assertEqual(rc, 0)
                buf2 = ctypes.create_string_buffer(buf.raw[:out_len.value], 0x1100)
                rc = m.mu_crypto_run(dec, MU_CRYPTO_DEC, 3, buf2, out_len.value, 0x1100, ctypes.byref(out_len))
                self.assertEqual(rc, 0)
                self.assertEqual(buf2.raw[:out_len.value], plain)
        finally:
            m.mu_crypto_free(enc)
            m.mu_crypto_free(dec)

    def test_missing_channel_and_bounds(self):
        m = self.m.lib
        c = m.mu_crypto_new()
        try:
            out = ctypes.create_string_buffer(0x1100)
            self.assertEqual(m.mu_crypto_call(c, MU_CRYPTO_ENC, 5, ctypes.cast(out, ctypes.c_void_p), 0x1100,
                                              b'abc', 3), -1)   # no context
            m.mu_crypto_open(c, MU_CRYPTO_ENC, 5)
            self.assertEqual(m.mu_crypto_call(c, MU_CRYPTO_ENC, 5, ctypes.cast(out, ctypes.c_void_p), 1,
                                              b'abcdefgh', 8), MU_CRYPTO_OUTSIDE)   # dst too small
        finally:
            m.mu_crypto_free(c)


if __name__ == '__main__':
    unittest.main()
