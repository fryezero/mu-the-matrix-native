#!/usr/bin/env python3
"""Compare native/net/crypto.cpp with the client's C3/C4 CryptoModule instructions (NET-CRYPTO-001).

The client's own routines run in Unicorn over the pinned restored text and the verified second
image section (scripts/client_ui_machine.py: the uncaptured third section and the case heap
are undefined until written; an undefined read, or execution outside the allowlisted ranges,
stops the case). The authored module (native/build/libmucrypto, ctypes) runs the same steps.
Families:

* ctor      0x018df200 on both module addresses (g_enc 0x06fce2fc, g_dec 0x06fce31c): empty
            map (MSVC head node), size 0, the 32-byte seed string;
* open      CreateCtx 0x018df700, Remove 0x018df3f0 and the getters 0x018df610 / 0x018df660 /
            0x018df6b0 over random sequences of channels (signed, extremes, the socket object
            address 0x06fca2d8), re-creation of a live channel included;
* set_key   SetKeyChannel 0x018df5c0 -> SetKey 0x018ea8d0 -> factory 0x018ea540 with keys
            crafted to reach every selector value (all ten entries of the table 0x018eaf30 and
            the default) with every one of the 17 factory cases, short (< 10) and long keys,
            and a missing channel;
* factory   the factory 0x018ea540 on a bare holder (ctor 0x018e5f90) for every case and the
            indices 0..19 and three large ones, re-keying a holder that already has a class,
            then the class Encrypt / Decrypt through the holder (0x018e9ec0 / 0x018e8be0):
            size queries, every length class, valid and damaged ciphertexts;
* encrypt   Encrypt 0x018df500 sequences on g_enc over 1..3 channels, starting from each case,
            size queries and missing channels interleaved, across rekey boundaries of every
            interval (8 and 0x20; 0x800 in the long cases);
* decrypt   Decrypt 0x018df460 sequences on g_dec over mirror ciphertexts (the reference
            build's ENC map plays the sender), with damaged pad bytes, lengths and bits,
            recovered lengths 0 and > 0x1000, dst NULL and missing channels, across rekey
            boundaries (clean cases stay in step with the sender; one long clean case).

Compared after every call: the return value, the whole destination buffer, every context of
the map (map order, channel, counters, the 128-byte state table, +0x8c, the cipher index
+0x94, the class and its interval), and the factory calls SetKey made (how many, and the
index, length and first 64 bytes of the key buffer of the last one).

Stubs (allocation only): operator new 0x0191ba7b and malloc 0x019a4da0 (case heap, sizes
recorded), operator delete 0x0191baab / 0x0191c490 and free 0x019a4d50 (the freed range is
made undefined again, so a use after free stops the case). Seeded globals: the security
cookie 0x01cf65c0 (MSVC default), the CPU-feature word 0x01cf6618 (pinned math capture), the
CRT words __favor 0x0bdcb284 = 0 and __isa_available 0x0bdcb280 = 0 (as validate_fidelity),
and the process-start zeros of two Crypto++ statics: GOST's sTableCalculated 0x0bdd0c30 and
g_x86DetectionDone 0x0bdd0c32 (DetectX86Features 0x00911830 then runs as client code).
g_nullNameValuePairs 0x01d04e70 is written by the client's own initializer 0x008dfa20. The
CRT memcpy / memset, the Crypto++ hashes and ciphers and the STL map code run as client code.

Inputs are generated with the reference build (native/build/libmucrypto) and seeded RNGs; the
build under test only answers. Planted mistakes: --mutations builds native/net/crypto.cpp
with -DMU_CRYPTO_MUTATION=k for each k in MUTATIONS and requires every one to be caught.
The JSON report goes to --report; the exit code is 0 only when every family matches,
coverage is complete and every planted mistake is caught (2: private inputs missing).
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import client_ui_machine as cm  # noqa: E402
import pins  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
LIB = ROOT/f'native/build/libmucrypto.{SUFFIX}'
MUTANT_DIR = ROOT/'native/build/crypto-mutants'

TEXT_BYTES, TEXT_SHA256 = pins.TEXT.size, pins.TEXT.sha256
DATA_BYTES, DATA_SHA256 = pins.DATA.size, pins.DATA.sha256
FEATURE_SHA256 = pins.FEATURE.sha256

MOD_ENC, MOD_DEC = 0x06fce2fc, 0x06fce31c
SOCKET = 0x06fca2d8
CTOR, CREATE, REMOVE, SETKEY_CHANNEL = 0x018df200, 0x018df700, 0x018df3f0, 0x018df5c0
ENCRYPT, DECRYPT, GET_INDEX, GET_DEC, GET_ENC = 0x018df500, 0x018df460, 0x018df610, 0x018df660, 0x018df6b0
SETKEY, FACTORY = 0x018ea8d0, 0x018ea540
HOLDER_CTOR, HOLDER_ENC, HOLDER_DEC = 0x018e5f90, 0x018e9ec0, 0x018e8be0
NVP_INIT = 0x008dfa20
NEW, DELETE_SIZED, DELETE, MALLOC, FREE = 0x0191ba7b, 0x0191baab, 0x0191c490, 0x019a4da0, 0x019a4d50
COOKIE, FEATURE, FAVOR, ISA = 0x01cf65c0, 0x01cf6618, 0x0bdcb284, 0x0bdcb280
GOST_TABLE_DONE, X86_DETECTION_DONE = 0x0bdd0c30, 0x0bdd0c32

# Executed code must stay inside these ranges (start, exclusive end); digests go to the report.
ALLOW = {
    'cryptopp_library': (0x008df000, 0x00912000),
    'cryptomodule_wrappers_hashes': (0x018de000, 0x018ec000),
    'crt_runtime': (0x0191b000, 0x0191e000),
    'crt_memcpy_memset': (0x0194c000, 0x0194d000),
    'crt_new_thunk': (0x01983100, 0x01983120),
}
# Routine bodies the families enter (start, exclusive end), reported by digest.
BODIES = {
    'ctor': (0x018df200, 0x018df278), 'remove': (0x018df3f0, 0x018df45e), 'decrypt': (0x018df460, 0x018df4f4),
    'encrypt': (0x018df500, 0x018df5bc), 'set_key_channel': (0x018df5c0, 0x018df610),
    'get_index': (0x018df610, 0x018df65c), 'get_dec': (0x018df660, 0x018df6a8), 'get_enc': (0x018df6b0, 0x018df6f8),
    'create': (0x018df700, 0x018df842), 'rekey': (0x018df9c0, 0x018df9dc), 'update': (0x018dfed0, 0x018dff6a),
    'factory': (0x018ea540, 0x018ea884), 'factory_tables': (0x018ea884, 0x018ea8cc),
    'set_key': (0x018ea8d0, 0x018eaf30), 'hash_table': (0x018eaf30, 0x018eaf58),
}

# The class vtables (RTTI ConcreteCipher<T, interval>) -> factory case (GOST: 3 or 8 by index).
VT_CASE = {0x01b285f0: 0, 0x01b28564: 1, 0x01b28578: 2, 0x01b285dc: 'gost', 0x01b2858c: 4, 0x01b285a0: 5,
           0x01b285b4: 6, 0x01b285c8: 7, 0x01b286dc: 9, 0x01b287c8: 10, 0x01b288b4: 11, 0x01b289a0: 12,
           0x01b28a8c: 13, 0x01b28b78: 14, 0x01b28c6c: 15, 0x01b28d60: 16}
CASE_NAMES = ['TEA', '3-Way', 'CAST-128', 'GOST(3)', 'RC5', 'RC6', 'MARS', 'IDEA', 'GOST(8)', 'Twofish', 'DES',
              'DES-EDE2', 'DES-EDE3', 'DES-XEX3', 'SKIPJACK', 'SAFER-K', 'SAFER-SK']
BLOCK = [8, 12, 8, 8, 8, 16, 16, 8, 8, 16, 8, 8, 8, 8, 8, 8, 8]
DST_CAP = 0x1100
SRC_CAP = 0x2100

MUTATIONS = {
    1: 'selector: (k0 ^ k1) <= k2 % 3 instead of <',
    2: 'selector % 10 instead of % 11',
    3: 'table entries 9 and 10 (RIPEMD-128 / RIPEMD-256) swapped',
    4: 'default entry takes digest[4] instead of digest[9]',
    5: 'index-9 sub-cipher from key[1] & 7 instead of key[0] & 7',
    6: 'SKIPJACK rekey interval 8 instead of 0x20',
    7: 'Encrypt pads a whole block when len % block == 0',
    8: 'Update records 8 bytes from n >= 8 instead of n > 8',
    9: 'Update indexes the state with b & 0x3f instead of b & 0x7f',
    10: 'rekey restarts the counter at 0 instead of 1',
    11: 'Decrypt accepts len % block == 0',
    12: 'Decrypt records the ciphertext instead of the plaintext',
    13: 'CreateCtx starts both counters at 0 instead of 1',
    14: 'short-key rule for key_len <= 10 instead of < 10',
}


def s32(value):
    value &= 0xffffffff
    return value - (1 << 32) if value & 0x80000000 else value


load_pinned = pins.loader(ValueError, '{label} does not match the pinned capture')


# ---- the authored module ----------------------------------------------------------------------

class Choice(ctypes.Structure):
    _fields_ = [('selector', ctypes.c_int32), ('hash', ctypes.c_int32), ('cipher', ctypes.c_int32),
                ('sub_cipher', ctypes.c_int32), ('cipher_case', ctypes.c_int32), ('rekey_interval', ctypes.c_uint32),
                ('key_len', ctypes.c_uint32), ('key', ctypes.c_uint8*64)]


class View(ctypes.Structure):
    _fields_ = [('channel', ctypes.c_int32), ('enc_count', ctypes.c_int32), ('dec_count', ctypes.c_int32),
                ('state', ctypes.c_uint8*128), ('word_8c', ctypes.c_int32), ('choice', Choice),
                ('keyings', ctypes.c_uint32)]


class Native:
    def __init__(self, path):
        lib = self.lib = ctypes.CDLL(str(path))
        P, I32, U32, SZ, B = ctypes.c_void_p, ctypes.c_int32, ctypes.c_uint32, ctypes.c_size_t, ctypes.c_char_p
        lib.mu_crypto_new.restype = P
        lib.mu_crypto_free.argtypes = [P]
        lib.mu_crypto_seed.argtypes = [P, ctypes.c_int, B, SZ]
        lib.mu_crypto_seed.restype = SZ
        lib.mu_crypto_open.argtypes = [P, ctypes.c_int, I32]
        lib.mu_crypto_close.argtypes = [P, ctypes.c_int, I32]
        lib.mu_crypto_set_key.argtypes = [P, ctypes.c_int, I32, B, SZ, ctypes.POINTER(Choice)]
        lib.mu_crypto_call.argtypes = [P, ctypes.c_int, I32, P, SZ, B, SZ]
        lib.mu_crypto_call.restype = I32
        for name in ('mu_crypto_cipher_index', 'mu_crypto_dec_count', 'mu_crypto_enc_count'):
            getattr(lib, name).argtypes = [P, ctypes.c_int, I32]
            getattr(lib, name).restype = I32
        lib.mu_crypto_view_channel.argtypes = [P, ctypes.c_int, I32, ctypes.POINTER(View)]
        lib.mu_crypto_channels.argtypes = [P, ctypes.c_int, ctypes.POINTER(I32), SZ]
        lib.mu_crypto_channels.restype = SZ
        lib.mu_crypto_cipher_new.argtypes = [U32, B, SZ]
        lib.mu_crypto_cipher_new.restype = P
        lib.mu_crypto_cipher_free.argtypes = [P]
        lib.mu_crypto_cipher_case.argtypes = [P]
        lib.mu_crypto_cipher_case.restype = I32
        for name in ('mu_crypto_cipher_interval', 'mu_crypto_cipher_block'):
            getattr(lib, name).argtypes = [P]
            getattr(lib, name).restype = U32
        for name in ('mu_crypto_cipher_encrypt', 'mu_crypto_cipher_decrypt'):
            getattr(lib, name).argtypes = [P, P, SZ, B, SZ]
            getattr(lib, name).restype = I32

    def new(self):
        return self.lib.mu_crypto_new()

    def free(self, c):
        self.lib.mu_crypto_free(c)

    def view(self, c, d, channel):
        v = View()
        return v if self.lib.mu_crypto_view_channel(c, d, channel, ctypes.byref(v)) == 0 else None

    def channels(self, c, d):
        n = self.lib.mu_crypto_channels(c, d, None, 0)
        out = (ctypes.c_int32*max(n, 1))()
        self.lib.mu_crypto_channels(c, d, out, n)
        return list(out)[:n]

    def snapshot(self, c, d):
        rows = []
        for ch in self.channels(c, d):
            v = self.view(c, d, ch)
            rows.append({'channel': v.channel, 'enc': v.enc_count, 'dec': v.dec_count, 'state': bytes(v.state).hex(),
                         'w8c': v.word_8c, 'index': v.choice.cipher, 'case': v.choice.cipher_case,
                         'interval': v.choice.rekey_interval})
        return rows

    def keyings(self, c, d, channel):
        v = self.view(c, d, channel)
        return v.keyings if v else 0

    def last_keying(self, c, d, channel):
        v = self.view(c, d, channel)
        return {'index': v.choice.cipher, 'len': v.choice.key_len, 'key': bytes(v.choice.key).hex()}

    def encrypt_bytes(self, c, channel, plain):
        out = ctypes.create_string_buffer(DST_CAP)
        r = self.lib.mu_crypto_call(c, 0, channel, ctypes.cast(out, ctypes.c_void_p), DST_CAP, plain, len(plain))
        return out.raw[:r] if r > 0 else None


# ---- the client --------------------------------------------------------------------------------

class Client:
    def __init__(self, text, data, feature):
        from unicorn import UC_HOOK_CODE
        self.m = m = cm.Machine(text, data)
        for lo, hi in ALLOW.values():
            m.allow((lo, hi))
        self.feature = feature
        self.sizes = {}
        self.factory_calls = []
        m.stub(NEW, lambda mm: self._alloc(mm.args(1)[0]), 0)
        m.stub(MALLOC, lambda mm: self._alloc(mm.args(1)[0]), 0)
        m.stub(DELETE_SIZED, lambda mm: self._free(mm.args(1)[0]), 0)
        m.stub(DELETE, lambda mm: self._free(mm.args(1)[0]), 0)
        m.stub(FREE, lambda mm: self._free(mm.args(1)[0]), 0)
        m.uc.hook_add(UC_HOOK_CODE, self._on_factory, begin=FACTORY, end=FACTORY)

    def _alloc(self, size):
        address = self.m.alloc(max(1, size))
        self.sizes[address] = max(1, size)
        return address

    def _free(self, address):
        if address == 0:
            return 0
        size = self.sizes.pop(address, 0)
        if not size:
            return self.m.fail(f'free of unknown pointer {address:#x}')
        self.m.defined.difference_update(range(address, address + size))
        return 0

    def _on_factory(self, uc, address, size, user):
        esp = uc.reg_read(cm.UC_X86_REG_ESP)
        index, key, length = struct.unpack('<3I', bytes(uc.mem_read(esp + 4, 12)))
        self.factory_calls.append({'index': index, 'len': length, 'key': bytes(uc.mem_read(key, 64)).hex()})

    def fresh(self, modules=(MOD_ENC, MOD_DEC)):
        m = self.m
        m.reset()
        self.sizes = {}
        self.factory_calls = []
        m.put32(COOKIE, 0xbb40e64e)
        m.write(FEATURE, self.feature)
        m.put32(FAVOR, 0)
        m.put32(ISA, 0)
        m.write(GOST_TABLE_DONE, b'\0')
        m.write(X86_DETECTION_DONE, b'\0')
        m.call(NVP_INIT)
        for module in modules:
            m.call(CTOR, ecx=module)
        self.src = m.alloc(SRC_CAP)
        self.dst = m.alloc(DST_CAP)

    def call(self, address, args=(), ecx=None):
        return self.m.call(address, list(args), ecx=ecx)

    def put_src(self, payload):
        """The case's source buffer: exactly len(payload) defined bytes."""
        self.m.defined.difference_update(range(self.src, self.src + SRC_CAP))
        if payload:
            self.m.write(self.src, payload)
        return self.src

    def put_dst(self, guard):
        self.m.write(self.dst, guard)
        return self.dst

    def buffer(self, payload, size=None):
        size = len(payload) if size is None else size
        address = self.m.alloc(max(size, 1))
        self.m.write(address, bytes(payload).ljust(size, b'\0'))
        return address

    def take_factory_calls(self):
        calls, self.factory_calls = self.factory_calls, []
        return calls

    # MSVC std::map nodes: +0 left, +4 parent, +8 right, +0xd isnil, +0x10 key, +0x14 value
    def contexts(self, module):
        m = self.m
        head = m.u32(module)
        out = []
        stack, node = [], m.u32(head + 4)
        while stack or (node and m.read(node + 0xd, 1) == b'\0'):
            while node and m.read(node + 0xd, 1) == b'\0':
                stack.append(node)
                node = m.u32(node)
            node = stack.pop()
            out.append((s32(m.u32(node + 0x10)), m.u32(node + 0x14)))
            node = m.u32(node + 8)
        if len(out) != m.u32(module + 4):
            raise cm.CaseError(f'map size {m.u32(module + 4)} but {len(out)} nodes')
        return out

    def case_of(self, wrapper, index):
        vt = self.m.u32(wrapper)
        case = VT_CASE.get(vt)
        if case is None:
            raise cm.CaseError(f'unknown cipher vtable {vt:#x}')
        if case == 'gost':
            case = 3 if index % 10 == 3 else 8 if index % 10 == 8 else -1
        return case

    def snapshot(self, module):
        m = self.m
        rows = []
        for channel, ctx in self.contexts(module):
            wrapper = m.u32(ctx + 0x90)
            index = s32(m.u32(ctx + 0x94))
            rows.append({'channel': s32(m.u32(ctx)), 'enc': s32(m.u32(ctx + 4)), 'dec': s32(m.u32(ctx + 8)),
                         'state': m.read(ctx + 0xc, 128).hex(), 'w8c': s32(m.u32(ctx + 0x8c)), 'index': index,
                         'case': self.case_of(wrapper, index), 'interval': m.u32(wrapper + 4)})
            if rows[-1]['channel'] != channel:
                raise cm.CaseError('context channel differs from its map key')
        return rows


# ---- comparison --------------------------------------------------------------------------------

class Mismatch(Exception):
    pass


class Family:
    def __init__(self, name):
        self.name = name
        self.cases = self.calls = 0
        self.failures = []
        self.coverage = {}
        self.seconds = 0.0

    def cover(self, key, value=1):
        self.coverage[key] = self.coverage.get(key, 0) + value

    def check(self, case, step, what, client, native):
        if client != native:
            if len(self.failures) < 6:
                self.failures.append({'case': case, 'step': step, 'what': what, 'client': client, 'native': native})
            raise Mismatch(what)

    def error(self, case, message):
        if len(self.failures) < 6:
            self.failures.append({'case': case, 'what': 'client case error', 'error': message})

    def report(self):
        return {'cases': self.cases, 'calls': self.calls, 'mismatches': len(self.failures),
                'failures': self.failures[:3], 'seconds': self.seconds,
                'coverage': dict(sorted(self.coverage.items(), key=lambda kv: str(kv[0])))}


def check_maps(fam, label, step, client, native, c, module, d):
    fam.check(label, step, 'contexts', client.snapshot(module), native.snapshot(c, d))


def check_keying(fam, label, step, client, native, c, d, channel, expected):
    """The client's factory calls of this step: `expected` of them (0 or 1), equal to the native's."""
    calls = client.take_factory_calls()
    fam.check(label, step, 'factory call count', len(calls), expected)
    if expected:
        fam.check(label, step, 'factory call', calls[-1], native.last_keying(c, d, channel))


def run_case(fam, label, body):
    fam.cases += 1
    try:
        body()
    except Mismatch:
        pass
    except cm.CaseError as error:
        fam.error(label, str(error))


# ---- case generation (reference build only) ----------------------------------------------------

def reachable(selector, case):
    """Selector 1 (SHA-256) takes the cipher index and the index-9 sub-cipher from the same byte
    digest[0]: digest[0] % 10 == 9 makes it odd, so the even sub-ciphers (Twofish, DES-EDE2,
    DES-XEX3, SAFER-K) cannot follow it. Every other selector reaches every case."""
    return not (selector == 1 and case in (9, 11, 13, 15))


def selector_for(rng, case):
    return rng.choice([s for s in range(11) if case is None or reachable(s, case)])

def crafted_key(rng, ref, selector, case, long_key=None, tries=6000):
    """A key whose SetKey selector is `selector` and whose factory case is `case`, searched with
    the reference build (the comparison itself is against the client)."""
    c = ref.new()
    ref.lib.mu_crypto_open(c, 0, 1)
    choice = Choice()
    try:
        for _ in range(tries):
            lk = rng.random() < 0.7 if long_key is None else long_key
            top = 256 // 11 - (1 if selector > 2 else 0)
            if lk:
                key = bytearray(rng.randrange(256) for _ in range(rng.choice([10, 11, 16, 20, 32, 64, 128, 200])))
                if rng.random() < 0.8:
                    key[1] = key[0]
                    key[2] = 3*rng.randrange(85)
                    key[3] = 0
                    key[4] = selector + 11*rng.randrange(top)
            else:
                key = bytearray(rng.randrange(256) for _ in range(rng.randrange(1, 10)))
                key[0] = selector + 11*rng.randrange(top)
            ref.lib.mu_crypto_set_key(c, 0, 1, bytes(key), len(key), ctypes.byref(choice))
            if choice.selector == selector and (case is None or choice.cipher_case == case):
                return bytes(key)
    finally:
        ref.free(c)
    return None


def random_channel(rng):
    return rng.choice([0, 1, -1, 7, SOCKET, 0x7fffffff, -0x80000000, rng.randrange(-0x80000000, 0x80000000),
                       rng.randrange(-50, 50)])


def payload_length(rng, block, long_ok=True):
    pick = rng.random()
    if pick < 0.15:
        return rng.choice([0, 1, 7, 8, 9, block - 1, block, block + 1, 2*block, 2*block + 1])
    if pick < 0.8:
        return rng.randrange(0, 64)
    if pick < 0.95 or not long_ok:
        return rng.randrange(64, 600)
    return rng.randrange(600, 0x1000 - 2*block)


# ---- families ----------------------------------------------------------------------------------

def family_ctor(client, native, ref, rng, scale, fam):
    for module, d in ((MOD_ENC, 0), (MOD_DEC, 1)):
        label = f'ctor {module:#x}'

        def body():
            client.fresh(modules=(module,))
            m = client.m
            head = m.u32(module)
            c = native.new()
            try:
                seed = ctypes.create_string_buffer(64)
                n = native.lib.mu_crypto_seed(c, d, seed, 64)
                length, capacity = m.u32(module + 0x18), m.u32(module + 0x1c)
                text = m.read(m.u32(module + 8) if capacity >= 0x10 else module + 8, length)
                got = {'head_links': [m.u32(head + k) == head for k in (0, 4, 8)],
                       'head_flags': m.read(head + 0xc, 2).hex(), 'size': m.u32(module + 4), 'seed': text.hex()}
                want = {'head_links': [True, True, True], 'head_flags': '0101', 'size': len(native.channels(c, d)),
                        'seed': seed.raw[:n].hex()}
                fam.calls += 1
                fam.check(label, 0, 'module', got, want)
                fam.cover(f'seed length {length} capacity {capacity}')
            finally:
                native.free(c)
        run_case(fam, label, body)


GETTERS = (('index', GET_INDEX, 'mu_crypto_cipher_index'), ('dec', GET_DEC, 'mu_crypto_dec_count'),
           ('enc', GET_ENC, 'mu_crypto_enc_count'))


def family_open(client, native, ref, rng, scale, fam):
    for k in range(max(1, 60*scale)):
        label = f'open {k}'

        def body():
            client.fresh()
            c = native.new()
            try:
                pool = [random_channel(rng) for _ in range(rng.randrange(1, 5))]
                for step in range(rng.randrange(3, 14)):
                    module, d = rng.choice(((MOD_ENC, 0), (MOD_DEC, 1)))
                    ch = rng.choice(pool)
                    op = rng.random()
                    fam.calls += 1
                    if op < 0.55:
                        existed = native.view(c, d, ch) is not None
                        r_client = client.call(CREATE, [ch & 0xffffffff], ecx=module) & 0xff
                        r_native = native.lib.mu_crypto_open(c, d, ch)
                        fam.check(label, step, 'create result', r_client, r_native)
                        check_keying(fam, label, step, client, native, c, d, ch, 1)
                        fam.cover('create again' if existed else 'create')
                    elif op < 0.8:
                        client.call(REMOVE, [ch & 0xffffffff], ecx=module)
                        native.lib.mu_crypto_close(c, d, ch)
                        check_keying(fam, label, step, client, native, c, d, ch, 0)
                        fam.cover('remove')
                    else:
                        for name, address, fn in GETTERS:
                            r_client = s32(client.call(address, [ch & 0xffffffff], ecx=module))
                            fam.check(label, step, f'get {name}', r_client, getattr(native.lib, fn)(c, d, ch))
                        fam.cover('getters present' if native.view(c, d, ch) else 'getters absent')
                    check_maps(fam, label, step, client, native, c, module, d)
            finally:
                native.free(c)
        run_case(fam, label, body)


def family_set_key(client, native, ref, rng, scale, fam):
    jobs = [(selector, case, None) for selector in range(11) for case in range(17) for _ in range(max(1, scale // 2))
            if reachable(selector, case)]
    jobs += [(rng.randrange(11), None, None) for _ in range(40*scale)]
    jobs += [(selector, None, long_key) for selector in range(11) for long_key in (False, True)]
    rng.shuffle(jobs)
    for k, (selector, case, long_key) in enumerate(jobs):
        key = crafted_key(rng, ref, selector, case, long_key)
        if key is None:
            raise RuntimeError(f'no key found for selector {selector} case {case}')
        label = f'set_key {k} s{selector} c{case} len{len(key)}'

        def body():
            client.fresh()
            c = native.new()
            try:
                module, d = rng.choice(((MOD_ENC, 0), (MOD_DEC, 1)))
                ch = random_channel(rng)
                client.call(CREATE, [ch & 0xffffffff], ecx=module)
                native.lib.mu_crypto_open(c, d, ch)
                client.take_factory_calls()
                for again in range(rng.choice([1, 1, 1, 2])):
                    missing = rng.random() < 0.05
                    target = (ch + 1 if ch < 0x7fffffff else ch - 1) if missing else ch
                    use = key if again == 0 else crafted_key(rng, ref, rng.randrange(11), None)
                    address = client.buffer(use)
                    r_client = client.call(SETKEY_CHANNEL, [target & 0xffffffff, address, len(use)], ecx=module)
                    choice = Choice()
                    r_native = native.lib.mu_crypto_set_key(c, d, target, use, len(use), ctypes.byref(choice))
                    fam.calls += 1
                    if missing:
                        fam.check(label, again, 'missing channel', r_native, -1)
                        check_keying(fam, label, again, client, native, c, d, ch, 0)
                        fam.cover('missing channel')
                    else:
                        fam.check(label, again, 'set_key result', r_client & 0xff, r_native)
                        check_keying(fam, label, again, client, native, c, d, ch, 1)
                        fam.cover(f'selector {choice.selector}')
                        fam.cover(f'case {choice.cipher_case:02d} {CASE_NAMES[choice.cipher_case]}')
                        fam.cover('short key' if len(use) < 10 else 'key of 10' if len(use) == 10 else 'long key')
                    check_maps(fam, label, again, client, native, c, module, d)
            finally:
                native.free(c)
        run_case(fam, label, body)


def damaged(rng, body, block, fam):
    body = bytearray(body)
    pick = rng.random()
    if pick < 0.15 and body:
        body[-1] = rng.randrange(256)
        fam.cover('damage pad byte')
    elif pick < 0.25:
        body = body[:max(0, len(body) - rng.randrange(1, block + 1))]
        fam.cover('damage length')
    elif pick < 0.3 and body:
        body[rng.randrange(len(body))] ^= 0x40
        fam.cover('damage bit')
    return bytes(body)


def family_factory(client, native, ref, rng, scale, fam):
    jobs = []
    for index in list(range(20)) + [0xffffffff, 0x80000009, 0x7ffffff3]:
        for sub in (range(8) if index % 10 == 9 else [None]):
            jobs += [(index, sub)]*max(1, scale)
    for k, (index, sub) in enumerate(jobs):
        key_len = rng.choice([0, 1, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64])
        key = bytearray(rng.randrange(256) for _ in range(key_len))
        if sub is not None and (key_len or sub):
            if not key:
                key, key_len = bytearray(1), 1
            key[0] = (key[0] & ~7) | sub
        key = bytes(key)
        label = f'factory {k} index {index:#x} sub {sub} key_len {key_len}'

        def body():
            client.fresh(modules=())
            m = client.m
            h = native.lib.mu_crypto_cipher_new(index, key, key_len)
            h_ref = ref.lib.mu_crypto_cipher_new(index, key, key_len)
            try:
                holder = m.alloc(8)
                client.call(HOLDER_CTOR, ecx=holder)
                if rng.random() < 0.3:   # a holder that already has a class: the factory deletes it
                    other = client.buffer(rng.randbytes(64), 0x800)
                    client.call(FACTORY, [rng.randrange(10), other, 64], ecx=holder)
                    fam.cover('factory replaces a class')
                buf = client.buffer(key, 0x800)
                r = client.call(FACTORY, [index, buf, key_len], ecx=holder) & 0xff
                wrapper = m.u32(holder)
                got = {'result': r, 'case': client.case_of(wrapper, index), 'interval': m.u32(wrapper + 4)}
                want = {'result': 1, 'case': native.lib.mu_crypto_cipher_case(h),
                        'interval': native.lib.mu_crypto_cipher_interval(h)}
                fam.calls += 1
                fam.check(label, 0, 'class', got, want)
                case = want['case']
                fam.cover(f'case {case:02d} {CASE_NAMES[case]}')
                block = BLOCK[case]
                for step in range(1, 7):
                    enc = rng.random() < 0.5
                    if enc:
                        src = rng.randbytes(payload_length(rng, block))
                    else:
                        plain = rng.randbytes(payload_length(rng, block))
                        out = ctypes.create_string_buffer(DST_CAP)
                        r = ref.lib.mu_crypto_cipher_encrypt(h_ref, ctypes.cast(out, ctypes.c_void_p), DST_CAP,
                                                             plain, len(plain))
                        src = damaged(rng, out.raw[:r], block, fam)
                    size_query = rng.random() < 0.15
                    guard = rng.randbytes(DST_CAP)
                    src_addr = client.put_src(src)
                    dst_addr = 0 if size_query else client.put_dst(guard)
                    r_client = s32(client.call(HOLDER_ENC if enc else HOLDER_DEC, [dst_addr, src_addr, len(src)],
                                               ecx=holder))
                    out = ctypes.create_string_buffer(guard, DST_CAP)
                    fn = native.lib.mu_crypto_cipher_encrypt if enc else native.lib.mu_crypto_cipher_decrypt
                    r_native = fn(h, None if size_query else ctypes.cast(out, ctypes.c_void_p), DST_CAP, src, len(src))
                    fam.calls += 1
                    fam.check(label, step, 'encrypt' if enc else 'decrypt', r_client, r_native)
                    if not size_query:
                        fam.check(label, step, 'dst', m.read(dst_addr, DST_CAP).hex(), out.raw[:DST_CAP].hex())
                    fam.cover(('encrypt' if enc else 'decrypt') + (' size query' if size_query else '') +
                              (' -1' if r_client < 0 else ''))
            finally:
                native.lib.mu_crypto_cipher_free(h)
                ref.lib.mu_crypto_cipher_free(h_ref)
        run_case(fam, label, body)


def open_channels(client, native, ref, rng, c, module, d, start_case, mirror=None):
    """Open 1..3 channels; the first is re-keyed into `start_case` (None: the seed's cipher)."""
    chans = []
    while len(chans) < rng.randrange(1, 4):
        ch = random_channel(rng)
        if ch not in chans:
            chans.append(ch)
    for i, ch in enumerate(chans):
        client.call(CREATE, [ch & 0xffffffff], ecx=module)
        native.lib.mu_crypto_open(c, d, ch)
        if mirror is not None:
            ref.lib.mu_crypto_open(mirror, 0, ch)
        case = start_case if i == 0 else rng.choice([None, rng.randrange(17)])
        if case is not None:
            key = crafted_key(rng, ref, selector_for(rng, case), case)
            address = client.buffer(key)
            client.call(SETKEY_CHANNEL, [ch & 0xffffffff, address, len(key)], ecx=module)
            native.lib.mu_crypto_set_key(c, d, ch, key, len(key), None)
            if mirror is not None:
                ref.lib.mu_crypto_set_key(mirror, 0, ch, key, len(key), None)
    client.take_factory_calls()
    return chans


def one_call(client, native, fam, label, step, c, module, d, ch, src, with_dst):
    """One Encrypt (d 0) or Decrypt (d 1) on both sides, compared."""
    rows = {row['channel']: row for row in client.snapshot(module)}
    current = rows.get(ch)
    before = native.keyings(c, d, ch)
    guard = random.Random(f'{label}:{step}').randbytes(DST_CAP)
    src_addr = client.put_src(src)
    dst_addr = client.put_dst(guard) if with_dst else 0
    r_client = s32(client.call(ENCRYPT if d == 0 else DECRYPT, [ch & 0xffffffff, dst_addr, src_addr, len(src)],
                               ecx=module))
    out = ctypes.create_string_buffer(guard, DST_CAP)
    r_native = native.lib.mu_crypto_call(c, d, ch, ctypes.cast(out, ctypes.c_void_p) if with_dst else None, DST_CAP,
                                         src, len(src))
    fam.calls += 1
    fam.check(label, step, 'result', r_client, r_native)
    if with_dst:
        fam.check(label, step, 'dst', client.m.read(dst_addr, DST_CAP).hex(), out.raw[:DST_CAP].hex())
    rekeyed = native.keyings(c, d, ch) - before
    check_keying(fam, label, step, client, native, c, d, ch, rekeyed)
    check_maps(fam, label, step, client, native, c, module, d)
    if current:
        fam.cover(f'case {current["case"]:02d} {CASE_NAMES[current["case"]]}')
        if rekeyed:
            fam.cover(f'rekey after interval {current["interval"]:#x}')
    fam.cover('result ok' if r_client >= 0 else f'result {r_client}')
    return r_client


def family_encrypt(client, native, ref, rng, scale, fam, long_cases=2):
    jobs = [rng.choice([None] + list(range(17))) for _ in range(12*scale)] + list(range(17)) + [None]
    jobs += ['long']*long_cases
    for k, start in enumerate(jobs):
        label = f'encrypt {k} start {start}'

        def body():
            client.fresh()
            c = native.new()
            try:
                long_case = start == 'long'
                chans = open_channels(client, native, ref, rng, c, MOD_ENC, 0,
                                      rng.randrange(9) if long_case else start)
                if long_case:
                    chans = chans[:1]
                for step in range(0x800 + 40 if long_case else rng.randrange(20, 75)):
                    pick = rng.random()
                    ch = rng.choice(chans) if long_case or pick > 0.04 else random_channel(rng)
                    rows = {row['channel']: row for row in client.snapshot(MOD_ENC)}
                    block = BLOCK[rows[ch]['case']] if ch in rows else 8
                    src = rng.randbytes(payload_length(rng, block, not long_case))
                    one_call(client, native, fam, label, step, c, MOD_ENC, 0, ch, src, long_case or pick >= 0.15)
            finally:
                native.free(c)
        run_case(fam, label, body)


def family_decrypt(client, native, ref, rng, scale, fam, long_cases=1):
    jobs = [rng.choice([None] + list(range(17))) for _ in range(12*scale)] + list(range(17)) + [None]
    jobs += ['long']*long_cases
    for k, start in enumerate(jobs):
        label = f'decrypt {k} start {start}'

        def body():
            client.fresh()
            c = native.new()
            sender = ref.new()   # the other end: a reference ENC map keyed alike
            try:
                long_case = start == 'long'
                clean = long_case or rng.random() < 0.35
                chans = open_channels(client, native, ref, rng, c, MOD_DEC, 1,
                                      rng.randrange(9) if long_case else start, mirror=sender)
                if long_case:
                    chans = chans[:1]
                for step in range(0x800 + 80 if long_case else rng.randrange(20, 75)):
                    pick = rng.random()
                    ch = rng.choice(chans) if long_case or pick > 0.03 else random_channel(rng)
                    rows = {row['channel']: row for row in client.snapshot(MOD_DEC)}
                    block = BLOCK[rows[ch]['case']] if ch in rows else 8
                    # An empty payload encrypts to the pad byte alone, which Decrypt rejects (recovered
                    # length 0) after the sender counted it: clean cases keep both ends in step.
                    n = payload_length(rng, block, not long_case)
                    plain = rng.randbytes(max(n, 1) if clean else n)
                    kind = 'data' if clean else rng.choices(
                        ['data', 'pad', 'length', 'bit', 'huge', 'zero', 'null_dst'], [70, 7, 7, 5, 4, 3, 4])[0]
                    with_dst = kind != 'null_dst'
                    if kind in ('data', 'pad', 'bit'):
                        body_bytes = ref.encrypt_bytes(sender, ch, plain) or b''
                        if kind == 'pad' and body_bytes:
                            body_bytes = body_bytes[:-1] + bytes([rng.choice([body_bytes[-1] + 1, 0xff,
                                                                              rng.randrange(256)]) & 0xff])
                        elif kind == 'bit' and body_bytes:
                            i = rng.randrange(len(body_bytes))
                            body_bytes = body_bytes[:i] + bytes([body_bytes[i] ^ (1 << rng.randrange(8))]) + \
                                body_bytes[i + 1:]
                    elif kind == 'length':   # never sent: the sender keeps its count
                        n = rng.randrange(0, 200)
                        body_bytes = rng.randbytes(n + (1 if n % block == 1 else 0))
                    elif kind == 'huge':     # recovered length > 0x1000: the client's early -1
                        n = rng.choice([0x1101, 0x1201, 0x2001]) + block
                        n += (1 - n) % block
                        body_bytes = rng.randbytes(n - 1) + bytes([rng.randrange(0x40)])
                    elif kind == 'zero':     # recovered length 0
                        body_bytes = rng.randbytes(block) + bytes([block])
                    else:
                        body_bytes = rng.randbytes(block + 1)
                    fam.cover(f'input {kind}')
                    one_call(client, native, fam, label, step, c, MOD_DEC, 1, ch, body_bytes, with_dst)
            finally:
                native.free(c)
                ref.free(sender)
        run_case(fam, label, body)


FAMILIES = ['ctor', 'open', 'set_key', 'factory', 'encrypt', 'decrypt']
REQUIRED_CASES = {f'case {k:02d} {CASE_NAMES[k]}' for k in range(17)}


def coverage_problems(families):
    problems = []
    for name in ('set_key', 'factory', 'encrypt', 'decrypt'):
        if name in families:
            missing = sorted(REQUIRED_CASES - set(families[name].coverage))
            if missing:
                problems.append(f'{name}: cases not reached {missing}')
    if 'set_key' in families:
        sel = sorted({f'selector {s}' for s in range(11)} - set(families['set_key'].coverage))
        if sel:
            problems.append(f'set_key: selectors not reached {sel}')
    for name in ('encrypt', 'decrypt'):
        if name in families:
            for interval in (8, 0x20, 0x800):
                if not families[name].coverage.get(f'rekey after interval {interval:#x}'):
                    problems.append(f'{name}: no rekey after interval {interval:#x}')
    return problems


def run_families(client, native, ref, seed, names, scale, long_cases=True, stop_on_mismatch=False):
    families = {}
    for name in names:
        fam = Family(name)
        rng = random.Random(f'{seed}:{name}')
        t0 = time.time()
        fn = globals()['family_' + name]
        if name == 'encrypt':
            fn(client, native, ref, rng, scale, fam, long_cases=2 if long_cases else 0)
        elif name == 'decrypt':
            fn(client, native, ref, rng, scale, fam, long_cases=1 if long_cases else 0)
        else:
            fn(client, native, ref, rng, scale, fam)
        fam.seconds = round(time.time() - t0, 1)
        families[name] = fam
        print(f'  {name}: {fam.cases} cases, {fam.calls} calls, {len(fam.failures)} mismatches ({fam.seconds} s)',
              flush=True)
        if stop_on_mismatch and fam.failures:
            break
    return families


def build(path):
    subprocess.run(['make', '-C', str(ROOT/'native'), str(path.relative_to(ROOT/'native'))], check=True,
                   capture_output=True)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--text', default=None)
    ap.add_argument('--data', default=None)
    ap.add_argument('--feature', default=None)
    ap.add_argument('--seed', type=int, default=20261025)
    ap.add_argument('--scale', type=int, default=4, help='case-count multiplier')
    ap.add_argument('--families', default=','.join(FAMILIES))
    ap.add_argument('--mutations', action='store_true', help='also build and run every planted mistake')
    ap.add_argument('--mutants-only', action='store_true')
    ap.add_argument('--report', default=None)
    args = ap.parse_args(argv)
    inputs = [pin.path(given) for pin, given in ((pins.TEXT, args.text), (pins.DATA, args.data),
                                                 (pins.FEATURE, args.feature))]
    for path in inputs:
        if not path.is_file():
            print(f'skip: private input missing: {path}')
            return 2
    text = load_pinned(inputs[0], TEXT_BYTES, TEXT_SHA256, 'restored text')
    data = load_pinned(inputs[1], DATA_BYTES, DATA_SHA256, 'image data')
    feature = load_pinned(inputs[2], 4, FEATURE_SHA256, 'CPU feature word')
    t0 = time.time()

    def digest(lo, hi, n=64):
        return hashlib.sha256(text[lo - cm.TEXT_BASE:hi - cm.TEXT_BASE]).hexdigest()[:n]
    report = {'milestone': 'NET-CRYPTO-001', 'text_sha256': TEXT_SHA256, 'data_sha256': DATA_SHA256,
              'feature_sha256': FEATURE_SHA256, 'seed': args.seed, 'scale': args.scale,
              'allowlist': {name: [hex(lo), hex(hi), digest(lo, hi)] for name, (lo, hi) in ALLOW.items()},
              'bodies': {name: [hex(lo), hex(hi), digest(lo, hi, 16)] for name, (lo, hi) in BODIES.items()},
              'seeded_globals': {'security_cookie': hex(COOKIE), 'cpu_feature_word': hex(FEATURE), '__favor': hex(FAVOR),
                                 '__isa_available': hex(ISA), 'gost_sTableCalculated': hex(GOST_TABLE_DONE),
                                 'g_x86DetectionDone': hex(X86_DETECTION_DONE)}}
    ref = Native(build(LIB))
    client = Client(text, data, feature)
    names = [n for n in args.families.split(',') if n]
    ok = True
    if not args.mutants_only:
        print('families (reference build):', flush=True)
        families = run_families(client, ref, ref, args.seed, names, args.scale)
        problems = coverage_problems(families) if names == FAMILIES else []
        report['families'] = {name: fam.report() for name, fam in families.items()}
        report['coverage_problems'] = problems
        ok = all(not fam.failures for fam in families.values()) and not problems
        for problem in problems:
            print('coverage:', problem, flush=True)
    if args.mutations or args.mutants_only:
        caught = {}
        for k, description in MUTATIONS.items():
            mutant = Native(build(MUTANT_DIR/f'libmucrypto_m{k}.{SUFFIX}'))
            print(f'mutation {k}: {description}', flush=True)
            fams = run_families(client, mutant, ref, args.seed + k, names, max(1, args.scale // 4), long_cases=False,
                                stop_on_mismatch=True)
            hit = [name for name, fam in fams.items() if fam.failures]
            caught[k] = {'description': description, 'caught': bool(hit), 'families': hit,
                         'first': next((fam.failures[0] for fam in fams.values() if fam.failures), None)}
        report['mutations'] = caught
        report['mutations_caught'] = f'{sum(1 for v in caught.values() if v["caught"])}/{len(caught)}'
        ok = ok and all(v['caught'] for v in caught.values())
    report['seconds'] = round(time.time() - t0, 1)
    report['ok'] = ok
    out = json.dumps(report, indent=1, default=str)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(out)
    summary = {k: report[k] for k in ('mutations_caught', 'coverage_problems', 'ok', 'seconds') if k in report}
    if 'families' in report:
        summary['families'] = {n: {k: f[k] for k in ('cases', 'calls', 'mismatches')}
                               for n, f in report['families'].items()}
        for name, fam in report['families'].items():
            for failure in fam['failures'][:1]:
                print('FAIL', name, json.dumps(failure)[:3000])
    print(json.dumps(summary, indent=1))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
