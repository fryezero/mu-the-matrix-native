#!/usr/bin/env python3
"""Compare reconstructed/progress (NATIVE-PROGRESS-001) with the client's instructions in Unicorn.

The client routines run over the pinned restored text and second image section
(scripts/client_ui_machine.py); reconstructed/progress runs through ctypes from the same inputs.
Both report every call into another subsystem as one text line (see progress.h); the lines, the
attribute record, the stat machine and the window fields are compared.

Families (client entry points):

* calc      the class formula, vtable slot 0 of the 16 stat machine classes (0x0099a917 ...), and
            the stat totals 0x0098d2c4; buffs and equipment answers are random per case
* bar       the experience bar 0x00c5125b (setExpData), normal and master class, the cache
* levelup   the level-up answer 0x01250b05 (opcode 0xA0 sub 0x06)
* point     the stat point answer 0x01223f04 (0xA0 sub 0x11)
* exp       the experience of a kill 0x01234c08 (opcode 0x16)
* master    the master level answers 0x01285b68 (0xA0 0x22) and 0x01285efa (0xA0 0x60)
* button    the character window's "+" buttons 0x00b469c4 (onClickButton) and the request 0x00b48aca
* options   the options window: load 0x00c76115 / 0x00c76314, setDatas 0x00c767d9, onChange 0x00c75bb2,
            apply 0x00c7635f, close 0x00c75fe2, the setters 0x00c76022 .. 0x00c760fa

Modelled (not client code), each a recorded boundary: the GFx value API and invokes, GlobalText,
std::string, the C runtime (memset, sprintf-family formatters), the packet builder, the buff and
equipment queries, the effect/sound/chat/window routines the handlers call (recorded as lines),
FMOD (the sound groups) and the INI file API.  Entry points whose first five bytes jump into IGC.dll
(0x00c51256, 0x00b46a27) are entered after the displaced instructions, restated in the case setup.
"""
import argparse
import ctypes
from ctypes import CFUNCTYPE, POINTER, Structure, c_char_p, c_int, c_int32, c_uint8, c_void_p
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import client_ui_machine as cm  # noqa: E402

TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'
EVIDENCE = ROOT / 'evidence' if (ROOT / 'evidence').exists() else Path.home() / 'Documents/main-exe-study/evidence'
PRGDIR = ROOT / 'reconstructed' / 'progress'
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'

ATTR_SIZE, MACHINE_SIZE = 0x200, 0x1e4
HERO_GLOBAL, ATTR_GLOBAL, HERO_CHAR = 0x01d1df18, 0x01d1df1c, 0x0a39d754
SSE_LEVEL = 0x0bdcb280
FAKE_BASE = 0x7e000000
HERO, CHAR, MACHINE = FAKE_BASE + 0x10000, FAKE_BASE + 0x20000, FAKE_BASE + 0x30000
ATTR = HERO + 8
ITEMS, ITEM_STRIDE = 0x1b58, 0x12c

CLASS_SLOT0 = (0x0099a917, 0x009991f8, 0x0099d6f4, 0x009a789c, 0x00999e9a, 0x009f5fc4, 0x009d842f, 0x0099e486,
               0x009da301, 0x009ea4ea, 0x0099edde, 0x009ff69c, 0x009a6f75, 0x009a5b41, 0x0098702b, 0x00998a96)
TOTALS = 0x0098d2c4
GETTERS = (0x00a00367, 0x00a00066, 0x00a000e9, 0x0139d8ea, 0x0139cb15)
BUFF_TEST, ITEM_VALID, WEAPON_KIND, ITEM_IS = 0x0139f66e, 0x00993731, 0x0139d95f, 0x00987982


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def body_end(text, start):
    return cm.function_extent(text, start)


# ---- the C side ----------------------------------------------------------------------------------------------

EMIT_FN = CFUNCTYPE(None, c_void_p, c_char_p)
TEXT_FN = CFUNCTYPE(c_void_p, c_void_p, c_int32)
BUFF_FN = CFUNCTYPE(c_int, c_void_p, c_int32)
VALID_FN = CFUNCTYPE(c_int, c_void_p, c_int32)
KIND_FN = CFUNCTYPE(c_int32, c_void_p, c_int32)
BYTE_FN = CFUNCTYPE(c_uint8, c_void_p, c_int32)
IS_FN = CFUNCTYPE(c_int, c_void_p, c_int32, c_int32)


class Env(Structure):
    _fields_ = [('user', c_void_p), ('attr', POINTER(c_uint8)), ('hero_class', c_uint8),
                ('emit', EMIT_FN), ('global_text', TEXT_FN), ('has_buff', BUFF_FN),
                ('item_valid', VALID_FN), ('item_weapon_kind', KIND_FN), ('item_byte38', BYTE_FN),
                ('item_is', IS_FN), ('window', CFUNCTYPE(c_int, c_void_p, ctypes.c_uint32)),
                ('hero', POINTER(c_uint8)),
                ('character', CFUNCTYPE(c_void_p, c_void_p, c_int32, POINTER(c_int32))),
                ('world_hides_damage', CFUNCTYPE(c_int, c_void_p)),
                ('tree', CFUNCTYPE(c_int, c_void_p)), ('tree_map', CFUNCTYPE(c_int32, c_void_p, c_int32, c_int32)),
                ('tree_node', CFUNCTYPE(c_int, c_void_p, c_int32, c_int32, POINTER(c_int32))),
                ('has_effect', CFUNCTYPE(c_int, c_void_p, c_int32))]


class Native:
    def __init__(self, mutation=0, work=None):
        sources = sorted(str(p) for p in PRGDIR.glob('progress_*.c'))
        if mutation:
            lib = Path(work) / f'libprogress-m{mutation}.{SUFFIX}'
            subprocess.run(['cc', '-std=c11', '-O2', '-fPIC', '-shared', '-ffp-contract=off', '-fno-fast-math',
                            f'-DMU_PROGRESS_MUTATION={mutation}', *sources, '-o', str(lib)], check=True)
        else:
            lib = PRGDIR / f'libprogress.{SUFFIX}'
            subprocess.run(['make', '-s', '-C', str(PRGDIR)], check=True)
        L = self.L = ctypes.CDLL(str(lib))
        L.mu_prg_calc_class.argtypes = [POINTER(Env), c_int, POINTER(c_int32 * 5)]
        L.mu_prg_calc_totals.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_int32 * 5)]
        for name in ('mu_prg_recv_levelup', 'mu_prg_recv_point', 'mu_prg_recv_master_levelup',
                     'mu_prg_recv_master_exp'):
            getattr(L, name).argtypes = [POINTER(Env), POINTER(c_uint8 * 0x100)]
        L.mu_prg_recv_kill_exp.argtypes = [POINTER(Env), POINTER(c_uint8 * 0x100), c_int, POINTER(c_uint8 * 5)]
        self.lines = []
        self.case = None
        self._keep = []

    def env(self, attr_buf, case):
        self.lines = []
        self.case = case
        e = Env()
        e.attr = ctypes.cast(attr_buf, POINTER(c_uint8))
        e.hero_class = case.get('hero_class', 0)
        e.emit = EMIT_FN(lambda u, line: self.lines.append(line.decode('latin1')))
        self.texts = {}

        def global_text(u, i):
            if i not in self.texts:
                self.texts[i] = ctypes.create_string_buffer(getattr(self, 'gt', lambda k: b'GT%d' % k)(i))
            return ctypes.addressof(self.texts[i])
        e.global_text = TEXT_FN(global_text)
        e.has_buff = BUFF_FN(lambda u, b: int(case['buffs'].get(b, 0)))
        e.item_valid = VALID_FN(lambda u, s: int(case['items'][s]['valid']))
        e.item_weapon_kind = KIND_FN(lambda u, s: case['items'][s]['kind'])
        e.item_byte38 = BYTE_FN(lambda u, s: case['items'][s]['b38'])
        e.item_is = IS_FN(lambda u, s, k: int(case['items'][s]['is'].get(k, 0)))
        e.window = Env._fields_[10][1](lambda u, g: int(case.get('windows', {}).get(g, 0)))
        self.hero_buf = (c_uint8 * 0x400).from_buffer_copy(case.get('hero', bytes(0x400)))
        e.hero = ctypes.cast(self.hero_buf, POINTER(c_uint8))
        self.obj_buf = (c_uint8 * 0x400).from_buffer_copy(case.get('object', bytes(0x400)))

        def character(u, key, index):
            if not case.get('object_present'):
                return None
            index[0] = case['object_index']
            return ctypes.addressof(self.obj_buf)
        e.character = Env._fields_[12][1](character)
        e.world_hides_damage = Env._fields_[13][1](lambda u: int(case.get('hides', 0)))
        e.tree = Env._fields_[14][1](lambda u: int(case.get('tree', 0)))
        e.tree_map = Env._fields_[15][1](lambda u, c, v: case.get('tree_map', -1))

        def tree_node(u, ident, key, out):
            if ident != case.get('tree_id_expect', ident) or not case.get('node', 0):
                return 0
            out[0] = case.get('bonus', 0)
            return 1
        e.tree_node = Env._fields_[16][1](tree_node)
        e.has_effect = Env._fields_[17][1](lambda u, x: int(case.get('effects', {}).get(x, 0)))
        self._keep = [e]
        return e


# ---- the client side ------------------------------------------------------------------------------------------

class Client:
    def __init__(self, text, data):
        self.text = text
        self.m = cm.Machine(text, data)
        self.m.heap_checks(False)
        self.case = None
        self.lines = []

    def allow_routines(self, *starts):
        for s in starts:
            self.m.allow((s, body_end(self.text, s)))

    def item_slot(self, ptr):
        off = ptr - HERO - ITEMS
        if off < 0 or off % ITEM_STRIDE:
            raise cm.CaseError(f'unexpected item pointer {ptr:#x}')
        return off // ITEM_STRIDE

    def install_calc(self):
        m = self.m

        def buff(mm):
            char, b = mm.args(2)
            if char != CHAR:
                return mm.fail(f'buff test on {char:#x}')
            return int(self.case['buffs'].get(b, 0))
        m.stub(BUFF_TEST, buff, 0)

        def valid(mm):
            item, = mm.args(1)
            return int(self.case['items'][self.item_slot(item)]['valid'])
        m.stub(ITEM_VALID, valid, 4)

        def kind(mm):
            item, = mm.args(1)
            return self.case['items'][self.item_slot(item)]['kind'] & 0xffffffff
        m.stub(WEAPON_KIND, kind, 0)

        def is_kind(mm):
            from unicorn.x86_const import UC_X86_REG_ECX
            item = mm.uc.reg_read(UC_X86_REG_ECX)
            k, = mm.args(1)
            return int(self.case['items'][self.item_slot(item)]['is'].get(k, 0))
        m.stub(ITEM_IS, is_kind, 4)

    def setup_hero(self, attr):
        m = self.m
        m.write(HERO, bytes(0x4000))
        m.write(ATTR, attr)
        for s, it in enumerate(self.case.get('items', [])):
            m.write(HERO + ITEMS + s * ITEM_STRIDE + 0x38, bytes([it['b38']]))
        m.write(CHAR, bytes(0x4000))
        m.write(CHAR + 0x12, bytes([self.case.get('hero_class', 0)]))
        m.write(MACHINE, bytes(MACHINE_SIZE))
        m.put32(MACHINE + 4, HERO)
        m.put32(MACHINE + 8, ATTR)
        m.put32(HERO_GLOBAL, HERO)
        m.put32(ATTR_GLOBAL, ATTR)
        m.put32(HERO_CHAR, CHAR)
        m.put32(SSE_LEVEL, 2)


def map_fake(m):
    m.uc.mem_map(FAKE_BASE, 0x100000, cm.UC_PROT_ALL)


# ---- cases ----------------------------------------------------------------------------------------------------

def random_attr(rng, cls):
    a = bytearray(ATTR_SIZE)
    level = rng.choice([1, 2, 50, 150, 400, rng.randint(1, 400), rng.randint(0, 0x7fff)])
    struct.pack_into('<i', a, 0, level)
    struct.pack_into('<i', a, 0x18, rng.choice([0, 1, 200, rng.randint(0, 2000)]))
    flags = rng.choice([0, 0x10, 0x20, 0x30, rng.randint(0, 15) << 4])
    a[0x187] = (cls & 0xf) | flags
    for off in range(0x18a, 0x1e8, 2):
        mode = rng.random()
        v = rng.randint(0, 0xffff) if mode < 0.25 else rng.randint(0, 5000) if mode < 0.8 else rng.randint(0, 40)
        struct.pack_into('<H', a, off, v)
    return bytes(a)


def random_items(rng):
    return [{'valid': rng.random() < 0.5, 'kind': rng.choice([0, 1, 2, 3, -1]), 'b38': rng.choice([0, 0, 1, 255]),
             'is': {0x4b: rng.random() < 0.5, 0xc: rng.random() < 0.3, 0x19: rng.random() < 0.3}} for _ in range(15)]


def calc_cases(rng, n):
    for k in range(n):
        cls = k % 16
        case = {'cls': cls, 'attr': random_attr(rng, cls), 'items': random_items(rng),
                'buffs': {b: rng.random() < 0.5 for b in (0x145, 0x12d, 0x17c)},
                'extra': [rng.choice([0, rng.randint(0, 3000), rng.randint(-50, 50)]) for _ in range(5)]}
        case['hero_class'] = case['attr'][0x187]
        yield case


def run_calc(client, native, case):
    m = client.m
    m.reset()
    client.case = case
    client.setup_hero(case['attr'])
    words = [x & 0xffffffff for x in case['extra']]
    m.call(CLASS_SLOT0[case['cls']], words, ecx=MACHINE)
    m.call(TOTALS, words, ecx=MACHINE)
    want_attr = m.read(ATTR, ATTR_SIZE)
    want_mach = m.read(MACHINE, MACHINE_SIZE)
    abuf = (c_uint8 * ATTR_SIZE).from_buffer_copy(case['attr'])
    mbuf = (c_uint8 * MACHINE_SIZE)()
    struct.pack_into('<II', mbuf, 4, HERO, ATTR)
    env = native.env(abuf, case)
    extra = (c_int32 * 5)(*case['extra'])
    native.L.mu_prg_calc_class(ctypes.byref(env), case['cls'], ctypes.byref(extra))
    native.L.mu_prg_calc_totals(abuf, mbuf, ctypes.byref(extra))
    diffs = []
    got_attr, got_mach = bytes(abuf), bytes(mbuf)
    for off in range(0, ATTR_SIZE, 2):
        if want_attr[off:off + 2] != got_attr[off:off + 2]:
            diffs.append(f'attr+{off:#x} client {want_attr[off:off+2].hex()} c {got_attr[off:off+2].hex()}')
    for off in range(0, MACHINE_SIZE, 4):
        if want_mach[off:off + 4] != got_mach[off:off + 4]:
            diffs.append(f'machine+{off:#x} client {want_mach[off:off+4].hex()} c {got_mach[off:off+4].hex()}')
    return diffs


FAMILIES = {}


def family_calc(client, native, rng, n, report):
    m = client.m
    client.allow_routines(*CLASS_SLOT0, TOTALS, *GETTERS)
    client.install_calc()
    fails = 0
    count = 0
    for case in calc_cases(rng, n):
        count += 1
        diffs = run_calc(client, native, case)
        if diffs:
            fails += 1
            if fails <= 5:
                report.setdefault('examples', []).append({'cls': case['cls'], 'diffs': diffs[:6]})
    return count, fails


FAMILIES['calc'] = family_calc


# ---- GFx values, formatters ---------------------------------------------------------------------------------

def cformat(mm, fmt, words):
    """A printf model for the client's formatters (%d %u %x %s %I64d %lld %%)."""
    out, i, k = bytearray(), 0, 0
    while i < len(fmt):
        c = fmt[i:i + 1]
        if c != b'%':
            out += c
            i += 1
            continue
        j = i + 1
        for spec, size in ((b'I64d', 2), (b'lld', 2), (b'd', 1), (b'u', 1), (b'x', 1), (b's', 1), (b'%', 0)):
            if fmt[j:j + len(spec)] == spec:
                if spec == b'%':
                    out += b'%'
                elif size == 2:
                    v = words[k] | words[k + 1] << 32
                    out += b'%d' % (v - (1 << 64) if v >> 63 else v)
                elif spec == b's':
                    out += mm.cstr(words[k])
                elif spec == b'd':
                    out += b'%d' % struct.unpack('<i', struct.pack('<I', words[k]))[0]
                elif spec == b'u':
                    out += b'%d' % words[k]
                else:
                    out += b'%x' % words[k]
                k += size
                i = j + len(spec)
                break
        else:
            raise cm.CaseError(f'unsupported format {fmt!r}')
    return bytes(out)


def cstr(mm, address, limit=4096):
    raw = mm.read(address, limit)
    return raw.split(b'\0')[0]


cm.Machine.cstr = cstr


class Gfx:
    """The GFx value API of the window objects, recorded as lines (see progress.h)."""

    def __init__(self, client):
        self.client = client
        self.values = {}

    def install(self, m):
        def ctor(mm):
            from unicorn.x86_const import UC_X86_REG_ECX
            self.values[mm.uc.reg_read(UC_X86_REG_ECX)] = []
            return 0
        m.stub(0x00aad26b, ctor, 0)
        m.stub(0x00aad299, lambda mm: 0, 0)

        def new_object(mm):
            v, = mm.args(1)
            self.values[v] = []
            return 0
        m.stub(0x00c8f5f4, new_object, 4)

        def member(kind):
            def h(mm):
                v, name, value = mm.args(3)
                if kind == 'int':
                    value = struct.unpack('<i', struct.pack('<I', value))[0]
                elif kind == 'bool':
                    value = bool(value & 0xff)
                else:
                    value = mm.cstr(value).decode('latin1')
                self.values.setdefault(v, []).append((mm.cstr(name).decode('latin1'), value))
                return 0
            return h
        m.stub(0x00ae957f, member('int'), 12)
        m.stub(0x00ae94c9, member('str'), 12)
        m.stub(0x00aecd73, member('bool'), 12)

        def invoke(mm):
            name, v = mm.args(2)
            obj = '{' + ','.join(json.dumps(k) + ':' + json.dumps(x, ensure_ascii=False, separators=(',', ':'))
                                 for k, x in self.values.get(v, [])) + '}'
            self.client.lines.append('invoke %s %s' % (mm.cstr(name).decode('latin1'), obj))
            return 0
        m.stub(0x00c8fac2, invoke, 8)


def install_crt(client):
    m = client.m

    def memset(mm):
        d, v, n = mm.args(3)
        mm.write(d, bytes([v & 0xff]) * n)
        return d
    m.stub(0x0194cd00, memset, 0)

    def sprintf(mm):
        w = mm.args(16)
        text = cformat(mm, mm.cstr(w[1]), w[2:])
        mm.write(w[0], text + b'\0')
        return len(text)
    m.stub(0x0098d0a9, sprintf, 0)
    m.stub(0x009619dd, sprintf, 0)
    m.write(0x01cf6610, b'\x20')   # __isa_available flags: the SSE2 path of __ltod3 0x0191c350
    m.allow((0x0191c5a0, 0x0191c5e0), (0x0191c350, 0x0191c392), (0x0191c250, 0x0191c350), (0x0191c990, 0x0191c9b0), (0x0191be60, 0x0191be94))


TRAMPOLINE = FAKE_BASE + 0x8000


def trampoline(m, target, displaced):
    """An entry whose first bytes jump into IGC.dll: run the displaced instructions, then jump on."""
    code = bytes(displaced)
    rel = target - (TRAMPOLINE + len(code) + 5)
    m.write(TRAMPOLINE, code + b'\xe9' + struct.pack('<i', rel))
    m.allow((TRAMPOLINE, TRAMPOLINE + len(code) + 5))
    return TRAMPOLINE


BAR, BAR_WINDOW = 0x00c5125b, FAKE_BASE + 0x40000
BAR_GETTERS = (0x00a0008e, 0x00a000ba, 0x00a000e9, 0x00a00131, 0x00a0015d, 0x0139cb8a, 0x0139d8ea, 0x0139cb15,
               0x00c54a49, 0x00afa53a)
MASTER_CAP = 0x016963bf


class BarCache(Structure):
    _fields_ = [('stage', c_int32), ('unused', c_int32), ('exp', ctypes.c_uint64), ('next', ctypes.c_uint64)]


def u64_choice(rng):
    return rng.choice([0, 1, 9, 10, 99, 1000, rng.randint(0, 1 << 20), rng.randint(0, 1 << 34), rng.randint(0, 1 << 62),
                       rng.randint(0, 1 << 64) - 1, (1 << 63) + rng.randint(0, 1000), (1 << 64) - 1])


def family_bar(client, native, rng, n, report):
    m = client.m
    gfx = Gfx(client)
    gfx.install(m)
    install_crt(client)
    client.allow_routines(BAR, *BAR_GETTERS)
    native.L.mu_prg_exp_bar.argtypes = [POINTER(Env), POINTER(BarCache), c_int32]
    native.L.mu_prg_exp_bar.restype = c_int
    cap_value = [0]
    m.stub(MASTER_CAP, lambda mm: cap_value[0], 0)
    fails = count = 0
    for k in range(n):
        count += 1
        attr = bytearray(random_attr(rng, rng.randint(0, 15)))
        for off in (0x08, 0x10, 0x20, 0x28):
            struct.pack_into('<Q', attr, off, u64_choice(rng))
        if rng.random() < 0.2:
            attr[0x10:0x18] = attr[0x08:0x10]
        hero_class = rng.choice([attr[0x187], rng.randint(0, 255), 0x21, 0x10, 0x00, 0x40, 0x80])
        cap_value[0] = rng.choice([400, 500, 1350, rng.randint(0, 2000)])
        struct.pack_into('<i', attr, 0x18, rng.choice([cap_value[0], cap_value[0] - 1, rng.randint(0, 2000)]))
        cache = BarCache(0, 0, 0, 0)
        if rng.random() < 0.3:
            stage = native.L.mu_prg_class_stage(hero_class)
            hi = attr[0x187]
            cache = BarCache(stage, rng.randint(0, 5), *struct.unpack_from('<QQ', attr, 0x20 if stage >= 3 else 0x08))
            if rng.random() < 0.3:
                cache.next ^= 1
        case = {'hero_class': hero_class, 'items': [], 'buffs': {}}
        m.reset()
        client.case = case
        client.lines = []
        client.setup_hero(bytes(attr))
        m.write(BAR_WINDOW, bytes(0x200))
        m.write(BAR_WINDOW + 0x88, bytes(cache))
        m.write(0x01cf6610, b'\x20')
        entry = trampoline(m, BAR, b'\x55\x8b\xec\x6a\xff')
        m.call(entry, [], ecx=BAR_WINDOW)
        want = (list(client.lines), m.read(BAR_WINDOW, 0x200))
        abuf = (c_uint8 * ATTR_SIZE).from_buffer_copy(bytes(attr))
        env = native.env(abuf, case)
        env.hero_class = hero_class
        wcache = BarCache.from_buffer_copy(bytes(cache))
        native.L.mu_prg_exp_bar(ctypes.byref(env), ctypes.byref(wcache), cap_value[0])
        window = bytearray(0x200)
        window[0x88:0x88 + ctypes.sizeof(BarCache)] = bytes(wcache)
        got = (list(native.lines), bytes(window))
        if want != got:
            fails += 1
            if fails <= 5:
                report.setdefault('examples', []).append({'client': want[0], 'c': got[0],
                                                          'window_equal': want[1] == got[1]})
    return count, fails


FAMILIES['bar'] = family_bar


# ---- the server's answers -----------------------------------------------------------------------------------

UIMGR, GFXMGR, CHATWIN, GT_OBJ = FAKE_BASE + 0x50000, FAKE_BASE + 0x51000, FAKE_BASE + 0x52000, FAKE_BASE + 0x53000
OBJECT = FAKE_BASE + 0x60000
GETTERS_WIN = {0x0095c50b: FAKE_BASE + 0x54000, 0x0095c5da: FAKE_BASE + 0x55000, 0x009a19ae: FAKE_BASE + 0x56000}
MGR_FIELDS = {0x21c: FAKE_BASE + 0x57000, 0x298: FAKE_BASE + 0x58000, 0x254: FAKE_BASE + 0x59000,
              0x1f8: FAKE_BASE + 0x5a000, 0x1f4: FAKE_BASE + 0x5b000, 0x88: FAKE_BASE + 0x5c000}
OBJ_OFF = 0x3254


def install_recv(client):
    """The boundaries of the receive handlers (see progress_recv.c's line list)."""
    m = client.m
    from unicorn.x86_const import UC_X86_REG_ECX

    def ecx():
        return m.uc.reg_read(UC_X86_REG_ECX)

    def line(text):
        client.lines.append(text)

    def getter(address):
        def h(mm):
            out, = mm.args(1)
            present = client.case.get('windows', {}).get(address, 0)
            mm.write(out, struct.pack('<II', GETTERS_WIN[address] if present else 0, 0))
            return out
        m.stub(address, h, 4)
    for address in GETTERS_WIN:
        getter(address)
    m.stub(0x0095f0bd, lambda mm: int(mm.u32(ecx()) != 0), 0)
    m.stub(0x0095f17c, lambda mm: mm.u32(ecx()), 0)
    m.stub(0x0095ebd0, lambda mm: 0, 0)
    m.stub(0x009617c6, lambda mm: mm.fail('release of a window reference'), 0)

    def simple(address, cleanup=0, nargs=0, fmt=None):
        def h(mm):
            args = mm.args(nargs)
            if fmt:
                line(fmt(mm, args))
            else:
                line('call %08x' % address + ''.join(' %x' % a for a in args))
            return 0
        m.stub(address, h, cleanup)
    for address in (0x00c71772, 0x00b45719, 0x00b458f2, 0x00b45a48, 0x00b45c36, 0x00c349cb, 0x00c42e9e,
                    0x00c239c2, 0x00c23c52, 0x00a00f4a, 0x00a00fb7, 0x00c84990, 0x00c51256):
        simple(address)
    simple(0x00c8d968, 4, 1)
    simple(0x00bb0803, 4, 1)
    m.stub(0x00aae6f9, lambda mm: int(client.case.get('windows', {}).get(0x00aae6f9, 0)), 0)
    m.stub(0x00ac3bf7, lambda mm: GFXMGR, 0)
    m.write(GFXMGR, bytes(0x400))
    for off, value in MGR_FIELDS.items():
        m.put32(GFXMGR + off, value)

    def gt(mm):
        idx, = mm.args(1)
        text = client.global_text(idx)
        buf = mm.alloc(len(text) + 1, define=True)
        mm.write(buf, text + b'\0')
        obj = mm.alloc(0x18, define=True)
        mm.put32(obj, buf)
        return obj
    m.stub(0x011753c3, gt, 4)
    m.stub(0x008e7f90, lambda mm: mm.u32(ecx()), 0)

    def string_ctor(mm):
        ptr, = mm.args(1)
        mm.put32(ecx(), ptr)
        return ecx()
    m.stub(0x0094997e, string_ctor, 4)
    m.stub(0x0094f183, lambda mm: 0, 0)

    def chat(address):
        def h(mm):
            s_, = mm.args(1)
            line('call %08x %s' % (address, json.dumps(mm.cstr(mm.u32(s_)).decode('latin1'))))
            return 0
        m.stub(address, h, 4)
    chat(0x01219a39)
    chat(0x0095f547)
    m.stub(0x00cfc94a, lambda mm: ecx(), 0)

    def ptr(v):
        o = CHAR + OBJ_OFF
        if o <= v < o + 0x400:
            return 'o' if v == o else 'o+%x' % (v - o)
        if OBJECT + OBJ_OFF <= v < OBJECT + OBJ_OFF + 0x400:
            return 'm' if v == OBJECT + OBJ_OFF else 'm+%x' % (v - OBJECT - OBJ_OFF)
        return '%x' % v

    def joint(mm):
        a = mm.args(14)
        line('call 0153b02c %x %s %s %s %x %s %08x %x %x %x %x %x %x %x' % (
            a[0], ptr(a[1]), ptr(a[2]), ptr(a[3]), a[4], ptr(a[5]), a[6], a[7], a[8], a[9], a[10], a[11], a[12],
            a[13]))
        return 0
    m.stub(0x0153b02c, joint, 0)

    def effect(mm):
        a = mm.args(14)
        line('call 013c0eaa %x %s %s %s %x %s %x %x %x %x %08x %x %x %x' % (
            a[0], ptr(a[1]), ptr(a[2]), ptr(a[3]), a[4], ptr(a[5]), *a[6:14]))
        return 0
    m.stub(0x013c0eaa, effect, 0)
    simple(0x00a6ac96, 0, 3)

    # characters by key (kill experience)
    def key_index(mm):
        key, = mm.args(1)
        if key != client.case['key']:
            return mm.fail(f'unexpected key {key:#x}')
        return client.case['object_index']
    m.stub(0x0137c724, key_index, 0)
    m.stub(0x0095f6db, lambda mm: 0x13572468, 0)
    m.stub(0x009a13f4, lambda mm: OBJECT if client.case.get('object_present') else 0, 4)

    def die(mm):
        o, = mm.args(1)
        line('call 01393a61 %s' % ('o' if o == OBJECT else '%x' % o))
        return 0
    m.stub(0x01393a61, die, 0)
    m.stub(0x009dacb8, lambda mm: int(client.case.get('hides', 0)), 0)

    def point(mm):
        a = mm.args(8)
        o = OBJECT + OBJ_OFF + 0x158
        color = mm.read(a[2], 12)
        line('call 016912ae %s %x %08x %08x %08x %08x %x %x %08x %x' % (
            'o+158' if a[0] == o else '%x' % a[0], a[1], *struct.unpack('<3I', color), a[3], a[4], a[5], a[6], a[7]))
        return 0
    m.stub(0x016912ae, point, 32)
    # the packet builder (report path)
    m.stub(0x00d51b91, lambda mm: 0, 0)
    m.stub(0x00d51ba6, lambda mm: 0, 0)

    def begin(mm):
        head, op = mm.args(2)
        client.packet = [head & 0xff, op & 0xff]
        return 0
    m.stub(0x0095c204, lambda mm: mm.fail('0x0095c204 must run as client code'), 4) if False else None
    m.stub(0x00d51baf, begin, 8)

    def add(mm):
        p_, n, flag = mm.args(3)
        client.packet += list(mm.read(p_, n))
        return ecx()
    m.stub(0x00d51c9b, add, 12)

    def send(mm):
        a, b = mm.args(2)
        line('call 00d51d4f %x %x' % (a, b))
        return 0
    m.stub(0x00d51d4f, send, 8)
    m.put32(0x01d22c6c, CHATWIN)
    m.put32(0x01cf15fc, 0)


def gt_text(idx):
    if idx in (0x1e6, 0x6d6):
        return b'GT%d got %%lld exp' % idx
    return b'GT%d' % idx


def recv_case(rng):
    cls = rng.randint(0, 15)
    attr = bytearray(random_attr(rng, cls))
    for off in (0x08, 0x10, 0x20, 0x28):
        struct.pack_into('<Q', attr, off, u64_choice(rng))
    for off in range(0x68, 0x90, 4):
        struct.pack_into('<i', attr, off, rng.randint(-5, 100000))
    hero_class = rng.choice([attr[0x187], rng.randint(0, 255), 0x20, 0x40, 0x60, 0x00])
    windows = {g: rng.random() < 0.7 for g in (0x0095c50b, 0x0095c5da, 0x009a19ae, 0x00aae6f9)}
    hero = bytearray(rng.randint(0, 255) for _ in range(0x400))
    hero[0x12] = hero_class
    return {'attr': bytes(attr), 'hero_class': hero_class, 'items': [], 'buffs': {}, 'windows': windows,
            'hero': bytes(hero)}


def random_packet(rng, n):
    p = bytearray(rng.randint(0, 255) for _ in range(n))
    for off in range(4, n - 1, 2):
        if rng.random() < 0.4:
            struct.pack_into('<H', p, off, rng.choice([0, 1, 2, 399, 400, 401, 0xffff, rng.randint(0, 3000)]))
    return bytes(p)


def run_handler(client, native, case, address, args, c_call, compare_char=False):
    m = client.m
    m.reset()
    client.case = case
    client.lines = []
    client.packet = []
    client.setup_hero(case['attr'])
    m.write(CHAR, case['hero'])
    m.write(CHAR + 0x12, bytes([case['hero_class']]))
    m.write(OBJECT, bytes(0x4000))
    m.write(OBJECT, case.get('object', bytes(0x400)))
    m.write(cm.STACK_BASE + cm.STACK_SIZE - 0x20000, bytes(0x20000))
    install_recv_state(client)
    pkt = m.alloc(0x100, define=True)
    m.write(pkt, case['packet'])
    words = [pkt if a == 'packet' else a for a in args]
    ret = m.call(address, words)
    want = {'lines': list(client.lines), 'attr': m.read(ATTR, ATTR_SIZE).hex(), 'packet': client.packet,
            'ret': ret & 0xff if ret is not None else None}
    if compare_char:
        want['hero'] = m.read(CHAR, 0x400).hex()
        want['object'] = m.read(OBJECT, 0x400).hex()
    abuf = (c_uint8 * ATTR_SIZE).from_buffer_copy(case['attr'])
    env = native.env(abuf, case)
    env.hero_class = case['hero_class']
    got_ret, got_packet = c_call(env)
    got = {'lines': list(native.lines), 'attr': bytes(abuf).hex(), 'packet': got_packet,
           'ret': got_ret}
    if compare_char:
        got['hero'] = bytes(native.hero_buf).hex()
        got['object'] = bytes(native.obj_buf).hex()
    return want, got


def install_recv_state(client):
    client.m.put32(0x01d22c6c, CHATWIN)
    client.m.put32(0x01cf15fc, 0)
    client.m.write(GFXMGR, bytes(0x400))
    for off, value in MGR_FIELDS.items():
        client.m.put32(GFXMGR + off, value)


def diff_report(want, got):
    out = {}
    for k in want:
        if want[k] != got.get(k):
            if k in ('attr', 'hero', 'object'):
                a, b = bytes.fromhex(want[k]), bytes.fromhex(got[k])
                out[k] = ['+%#x %02x/%02x' % (i, a[i], b[i]) for i in range(len(a)) if a[i] != b[i]][:8]
            elif k == 'lines':
                a, b = want[k], got.get(k)
                i = next((j for j in range(min(len(a), len(b))) if a[j] != b[j]), min(len(a), len(b)))
                out[k] = {'at': i, 'client': a[i:i + 3], 'c': b[i:i + 3], 'lengths': [len(a), len(b)]}
            else:
                out[k] = {'client': want[k], 'c': got.get(k)}
    return out


def recv_family(address, size, setup, call_native, args=('packet',), compare_char=False, ret_byte=False):
    def family(client, native, rng, n, report):
        client.allow_routines(address, 0x00a00031, 0x00a00386, 0x00a000cc, 0x00a00117, 0x00a00143, 0x00a00192,
                              0x00a0016f, 0x00a001d8, 0x00a0008e, 0x00a000ba, 0x00a00131, 0x00a0015d, 0x00a00074,
                              0x00a000e9, 0x00a00066, 0x00a00367, 0x0139d8ea, 0x0139cb15, 0x0139cb3c)
        install_crt(client)
        install_recv(client)
        client.global_text = gt_text
        native.gt = gt_text
        client.m.allow((0x0191c5a0, 0x0191c5e0))
        fails = count = 0
        for _ in range(n):
            count += 1
            case = recv_case(rng)
            case['packet'] = random_packet(rng, size)
            setup(rng, case)
            want, got = run_handler(client, native, case, address, [a if a != 'packet' else 'packet' for a in
                                                                      case.get('args', args)],
                                    lambda env: call_native(native, env, case), compare_char)
            if not ret_byte:
                want['ret'] = got['ret'] = None
            if want != got:
                fails += 1
                if fails <= 4:
                    d = diff_report(want, got)
                    d['hero_class'] = case['hero_class']
                    report.setdefault('examples', []).append(d)
        return count, fails
    return family


def _packet_arg(case):
    return (ctypes.c_uint8 * 0x100).from_buffer_copy(case['packet'] + bytes(0x100 - len(case['packet'])))


def native_levelup(native, env, case):
    native.L.mu_prg_recv_levelup(ctypes.byref(env), _packet_arg(case))
    return None, []


def native_point(native, env, case):
    native.L.mu_prg_recv_point(ctypes.byref(env), _packet_arg(case))
    return None, []


def native_kill(native, env, case):
    report = (ctypes.c_uint8 * 5)()
    r = native.L.mu_prg_recv_kill_exp(ctypes.byref(env), _packet_arg(case), case['args'][1], report)
    return r & 0xff, list(report) if not case['args'][1] else []


def native_master_up(native, env, case):
    native.L.mu_prg_recv_master_levelup(ctypes.byref(env), _packet_arg(case))
    return None, []


def native_master_exp(native, env, case):
    native.L.mu_prg_recv_master_exp(ctypes.byref(env), _packet_arg(case))
    return None, []


def setup_none(rng, case):
    pass


def setup_point(rng, case):
    p = bytearray(case['packet'])
    p[4] = rng.choice([0x10, 0x11, 0x12, 0x13, 0x14, 0x02, 0x03, 0x00, rng.randint(0, 255)])
    case['packet'] = bytes(p)


def setup_kill(rng, case):
    p = bytearray(case['packet'])
    if rng.random() < 0.3:
        p[7] = p[8] = 0
    if rng.random() < 0.2:
        p[5] = p[6] = 0
    case['packet'] = bytes(p)
    case['key'] = ((p[3] << 8) | p[4]) & 0x7fff
    case['object_index'] = rng.randint(0, 400)
    case['object_present'] = rng.random() < 0.7
    case['object'] = bytes(rng.randint(0, 255) for _ in range(0x400))
    case['hides'] = rng.random() < 0.3
    case['args'] = ['packet', rng.choice([1, 1, 1, 0])]


def setup_master_exp(rng, case):
    if rng.random() < 0.4:
        p = bytearray(case['packet'])
        struct.pack_into('<h', p, 4, struct.unpack_from('<i', case['attr'], 0x18)[0] & 0xffff)
        case['packet'] = bytes(p)


def family_table(client, native, rng, n, report):
    """The experience table 0x00a00e79 over every level -2 .. 1500 and random 64-bit levels, and the level
    reset 0x00a00f4a over random attribute records."""
    m = client.m
    install_crt(client)
    client.allow_routines(0x00a00e79, 0x00a00f4a, 0x00a00074, 0x00a000a0, 0x00a00066)
    native.L.mu_prg_exp_table.argtypes = [ctypes.c_int64]
    native.L.mu_prg_exp_table.restype = ctypes.c_int64
    native.L.mu_prg_level_exp.argtypes = [POINTER(c_uint8)]
    levels = list(range(-2, 1501)) + [rng.randint(-(1 << 63), (1 << 63) - 1) for _ in range(n)] + \
        [rng.randint(0, 100000) for _ in range(n)]
    fails = count = 0
    m.reset()
    client.case = {'items': [], 'buffs': {}}
    client.setup_hero(bytes(ATTR_SIZE))
    for level in levels:
        count += 1
        r = m.call(0x00a00e79, [level & 0xffffffff, (level >> 32) & 0xffffffff], ecx=HERO)
        from unicorn.x86_const import UC_X86_REG_EDX
        want = r | m.uc.reg_read(UC_X86_REG_EDX) << 32
        got = native.L.mu_prg_exp_table(level) & ((1 << 64) - 1)
        if want != got:
            fails += 1
            if fails <= 5:
                report.setdefault('examples', []).append({'level': level, 'client': want, 'c': got})
    for _ in range(n):
        count += 1
        attr = bytearray(random_attr(rng, 0))
        struct.pack_into('<i', attr, 0, rng.choice([rng.randint(-5, 1500), rng.randint(-(1 << 31), (1 << 31) - 1)]))
        struct.pack_into('<QQ', attr, 8, u64_choice(rng), u64_choice(rng))
        m.reset()
        client.setup_hero(bytes(attr))
        m.call(0x00a00f4a, [], ecx=HERO)
        want = m.read(ATTR, ATTR_SIZE)
        abuf = (c_uint8 * ATTR_SIZE).from_buffer_copy(bytes(attr))
        native.L.mu_prg_level_exp(abuf)
        if want != bytes(abuf):
            fails += 1
            if fails <= 5:
                report.setdefault('examples', []).append({'reset_level': struct.unpack_from('<i', attr, 0)[0]})
    return count, fails


FAMILIES['table'] = family_table


BUTTON, REQUEST, LAST_TICK, TICK_SLOT = 0x00b469c4, 0x00b48aca, 0x01d22d4c, 0x01a7c9a4
BUTTON_WINDOW, GFX_ARGS = FAKE_BASE + 0x70000, FAKE_BASE + 0x71000


def family_button(client, native, rng, n, report):
    """onClickButton 0x00b469c4 with the request 0x00b48aca (client code), the row as a GFx number."""
    m = client.m
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP
    install_crt(client)
    install_recv(client)
    client.allow_routines(REQUEST, 0x00ab06fb, 0x0095c204)
    m.allow((BUTTON, 0x00b46e30))   # the body (function_extent stops at the IGC.dll jump)
    m.stub(0x00aaf5d3, lambda mm: 0, 0x10)

    def strcmp(mm):
        a, b = mm.args(2)
        x, y = mm.cstr(a), mm.cstr(b)
        return 0 if x == y else (1 if x > y else 0xffffffff)
    m.stub(0x0195a3d0, strcmp, 0)
    tick = m._new_stub()
    now = [0]
    m.stub(tick, lambda mm: now[0], 0)

    def displaced(uc, address, size, user):   # 0x00b46a27: jmp IGC.dll, displaced "mov eax, [0x01d1df1c]"
        uc.reg_write(UC_X86_REG_EAX, m.u32(ATTR_GLOBAL))
        uc.reg_write(UC_X86_REG_EIP, 0x00b46a2c)
    m.uc.hook_add(UC_HOOK_CODE, displaced, begin=0x00b46a27, end=0x00b46a27)
    native.L.mu_prg_stat_button.argtypes = [POINTER(c_uint8), ctypes.c_double]
    native.L.mu_prg_stat_button.restype = c_int32
    native.L.mu_prg_stat_request.argtypes = [POINTER(Env), POINTER(ctypes.c_uint32), ctypes.c_uint32, c_int32,
                                            POINTER(c_uint8 * 5)]
    name_buf = FAKE_BASE + 0x72000
    fails = count = 0
    for _ in range(n):
        count += 1
        attr = bytearray(random_attr(rng, rng.randint(0, 15)))
        struct.pack_into('<H', attr, 0x1e2, rng.choice([0, 0, 1, 5, 0x8000, 0xffff, rng.randint(0, 3000)]))
        row = rng.choice([8.0, 13.0, 24.0, 29.0, 42.0, 8.0, 42.0, 9.0, 0.0, -8.0, 8.5, 13.000001, float('nan'),
                          float(rng.randint(0, 200))])
        name = b'onClickButton'
        last = rng.choice([0, 0xfffffff0, rng.randint(0, 1 << 32) - 1])
        now[0] = rng.choice([last + rng.randint(0, 200), rng.randint(0, (1 << 32) - 1), last + 99, last + 100]) & 0xffffffff
        case = {'items': [], 'buffs': {}, 'hero_class': attr[0x187]}
        m.reset()
        client.case = case
        client.lines = []
        client.packet = []
        client.setup_hero(bytes(attr))
        install_recv_state(client)
        m.put32(TICK_SLOT, tick)
        m.put32(LAST_TICK, last)
        m.write(name_buf, name + b'\0')
        m.write(GFX_ARGS, bytes(0x40))
        m.write(GFX_ARGS + 8, struct.pack('<d', row))
        m.write(BUTTON_WINDOW, bytes(0x400))
        m.call(BUTTON, [FAKE_BASE + 0x73000, name_buf, GFX_ARGS, 1], ecx=BUTTON_WINDOW)
        want = (list(client.lines), client.packet, m.u32(LAST_TICK))
        stat = native.L.mu_prg_stat_button((c_uint8 * ATTR_SIZE).from_buffer_copy(bytes(attr)), row)
        abuf = (c_uint8 * ATTR_SIZE).from_buffer_copy(bytes(attr))
        env = native.env(abuf, case)
        lt = ctypes.c_uint32(last)
        pkt = (c_uint8 * 5)()
        packet = []
        if stat >= 0 and native.L.mu_prg_stat_request(ctypes.byref(env), ctypes.byref(lt), now[0], stat, pkt):
            packet = [pkt[0], pkt[2], pkt[3], pkt[4]]
        got = (list(native.lines), packet, lt.value)
        if want != got:
            fails += 1
            if fails <= 5:
                report.setdefault('examples', []).append({'row': row, 'points': struct.unpack_from('<H', attr, 0x1e2)[0],
                                                          'client': want, 'c': got})
    return count, fails


FAMILIES['button'] = family_button


STATS, STATS_WINDOW = 0x00b3ee5e, FAKE_BASE + 0x74000


class StatWindow(Structure):
    _fields_ = [('shown', ctypes.c_uint16 * 10), ('total', ctypes.c_uint16 * 5), ('rate', ctypes.c_float),
                ('dirty', c_uint8)]


def family_stats(client, native, rng, n, report):
    """The character window's stat values 0x00b3ee5e (opcode 0x55 sub 0x57 through 0x0122a5f6)."""
    m = client.m
    install_crt(client)
    install_recv(client)
    client.allow_routines(STATS)
    strings = {}

    def fmt(address):
        def h(mm):
            out, row, value, _ = mm.args(4)
            client.lines.append('call %08x %x %x' % (address, row, value))
            return out
        return h
    m.stub(0x00b3e773, fmt(0x00b3e773), 0x10)
    m.stub(0x00b3e935, fmt(0x00b3e935), 0x10)

    def item(mm):
        row, a, b = mm.args(3)
        client.lines.append('call 00b3e2ed %x' % row)
        return 0
    m.stub(0x00b3e2ed, item, 0xc)

    def ffmt(mm):
        out, row, value, _ = mm.args(4)
        client.lines.append('call 00b3e3d5 %x %08x' % (row, value))
        return out
    m.stub(0x00b3e3d5, ffmt, 0x10)

    def item1(mm):
        row, a = mm.args(2)
        client.lines.append('call 00b3e2a4 %x' % row)
        return 0
    m.stub(0x00b3e2a4, item1, 8)
    m.stub(0x008e6d00, lambda mm: 0, 0)
    m.stub(0x008e83a0, lambda mm: 0, 0)

    def invoke(mm):
        win, name, fmt_, value = mm.args(4)
        client.lines.append('invoke %s [%d]' % (mm.cstr(name).decode(), value))
        return 0
    m.stub(0x00aae7e0, invoke, 0)
    native.L.mu_prg_recv_stats.argtypes = [POINTER(Env), POINTER(StatWindow), POINTER(c_uint8 * 0x100)]
    fails = count = 0
    for _ in range(n):
        count += 1
        attr = bytearray(random_attr(rng, rng.randint(0, 15)))
        win = bytearray(rng.randint(0, 255) for _ in range(0x200))
        p = bytearray(rng.randint(0, 255) for _ in range(0x1c))
        for i in range(5):
            mode = rng.random()
            base, add = struct.unpack_from('<HH', attr, 0x18a + 2 * i), None
            b0 = struct.unpack_from('<H', attr, (0x18a, 0x18c, 0x18e, 0x190, 0x192)[i])[0]
            a0 = struct.unpack_from('<H', attr, (0x198, 0x19a, 0x19c, 0x19e, 0x1a4)[i])[0]
            if mode < 0.5:   # unchanged in the attribute; the window copy may differ
                struct.pack_into('<HH', p, 4 + 4 * i, b0, a0)
                if rng.random() < 0.7:
                    struct.pack_into('<HH', win, 0x119 + 4 * i, b0, a0)
        if rng.random() < 0.5:
            win[0x13d:0x141] = p[0x18:0x1c]
        if rng.random() < 0.1:
            p[0x18:0x1c] = struct.pack('<f', float('nan'))
            win[0x13d:0x141] = p[0x18:0x1c]
        case = {'items': [], 'buffs': {}, 'hero_class': attr[0x187]}
        m.reset()
        client.case = case
        client.lines = []
        client.setup_hero(bytes(attr))
        install_recv_state(client)
        m.write(STATS_WINDOW, bytes(win))
        pkt = m.alloc(0x100, define=True)
        m.write(pkt, bytes(p))
        m.call(STATS, [pkt], ecx=STATS_WINDOW)
        wwin = m.read(STATS_WINDOW, 0x200)
        want = (list(client.lines), m.read(ATTR, ATTR_SIZE).hex(),
                [struct.unpack_from('<H', wwin, 0x119 + 2 * k)[0] for k in range(10)],
                [struct.unpack_from('<H', wwin, 0xa8 + 2 * k)[0] for k in range(5)], wwin[0x13d:0x141].hex(), wwin[0x10c])
        sw = StatWindow()
        for k in range(10):
            sw.shown[k] = struct.unpack_from('<H', win, 0x119 + 2 * k)[0]
        for k in range(5):
            sw.total[k] = struct.unpack_from('<H', win, 0xa8 + 2 * k)[0]
        ctypes.memmove(ctypes.addressof(sw) + StatWindow.rate.offset, bytes(win[0x13d:0x141]), 4)
        sw.dirty = win[0x10c]
        abuf = (c_uint8 * ATTR_SIZE).from_buffer_copy(bytes(attr))
        env = native.env(abuf, case)
        native.L.mu_prg_recv_stats(ctypes.byref(env), ctypes.byref(sw),
                                   (c_uint8 * 0x100).from_buffer_copy(bytes(p) + bytes(0x100 - len(p))))
        rate = bytes((ctypes.c_uint8 * 4).from_address(ctypes.addressof(sw) + StatWindow.rate.offset))
        got = (list(native.lines), bytes(abuf).hex(), list(sw.shown), list(sw.total), rate.hex(), sw.dirty)
        if want != got:
            fails += 1
            if fails <= 5:
                report.setdefault('examples', []).append({'client': [want[0], want[2:]], 'c': [got[0], got[2:]],
                                                          'attr_equal': want[1] == got[1]})
    return count, fails


FAMILIES['stats'] = family_stats


SPEED_ROW, SPEED_PACKET, SPEED_WINDOW, TREE, NODE = 0x00b40380, 0x0122a13d, FAKE_BASE + 0x75000, FAKE_BASE + 0x76000, \
    FAKE_BASE + 0x77000


def family_speed(client, native, rng, n, report):
    """The speed row 0x00b40380 (with the class machine of 0x00a0088d) and the speed packet 0x0122a13d."""
    m = client.m
    install_crt(client)
    install_recv(client)
    client.allow_routines(SPEED_ROW, SPEED_PACKET, 0x00a0088d, 0x00a0315b, 0x00b48a68, 0x00b48a7a, 0x0095fb49,
                          0x0095fb5b, 0x0095f5cc, 0x009942bf, 0x00993796, 0x009937fe, 0x0099426e, 0x009a9036, 0x009d8d49)
    ctors = (0x0099b13f, 0x00999df2, 0x0099e3de, 0x009a8fc3, 0x0099a86f, 0x009f8266, 0x009d8ce0, 0x0099ed36,
             0x009dac06, 0x009ead97, 0x009a064f, 0x009fff7f, 0x009a77ea, 0x009a623f, 0x00986fb8, 0x00998a2d)
    client.allow_routines(*ctors)

    def new(mm):
        size, = mm.args(1)
        return mm.alloc(size, define=True)
    m.stub(0x0191ba7b, new, 0)
    m.stub(0x00aae6f9, lambda mm: int(client.case.get('visible', 1)), 0)
    m.stub(0x00c354b7, lambda mm: client.case.get('tree_map', -1) & 0xffffffff, 8)

    def node(mm):
        ident, = mm.args(1)
        client.case['tree_id_seen'] = ident
        return NODE if client.case.get('node') else 0
    m.stub(0x00c2a236, node, 4)
    m.stub(0x00b48a9e, lambda mm: client.case.get('bonus', 0) & 0xffffffff, 4)

    def effect(mm):
        x, = mm.args(1)
        return int(client.case.get('effects', {}).get(x, 0))
    m.stub(0x01295ade, effect, 4)

    def gt(mm):
        idx, = mm.args(1)
        text = b'%d / %d' if idx == 0x10be and client.case.get('gt_real') else b'GT%d' % idx
        buf = mm.alloc(len(text) + 1, define=True)
        mm.write(buf, text + b'\0')
        return buf
    m.stub(0x0095f027, gt, 4)

    def row_text(mm):
        out, row, text, _ = mm.args(4)
        client.lines.append('call 00b3e33f %x %s' % (row, json.dumps(mm.cstr(text).decode('latin1'))))
        return out
    m.stub(0x00b3e33f, row_text, 0x10)

    def item1(mm):
        row, a = mm.args(2)
        client.lines.append('call 00b3e2a4 %x' % row)
        return 0
    m.stub(0x00b3e2a4, item1, 8)
    m.stub(0x008e6d00, lambda mm: 0, 0)
    m.stub(0x008e83a0, lambda mm: 0, 0)

    def invoke(mm):
        win, name, fmt_, value = mm.args(4)
        client.lines.append('invoke %s [%d]' % (mm.cstr(name).decode(), value))
        return 0
    m.stub(0x00aae7e0, invoke, 0)
    m.stub(0x00b40380, lambda mm: client.lines.append('call 00b40380') or 0, 0) if False else None
    native.L.mu_prg_speed_row.argtypes = [POINTER(Env), c_int32, POINTER(ctypes.c_uint16 * 2), c_int]
    native.L.mu_prg_recv_speed.argtypes = [POINTER(Env), POINTER(c_uint8 * 0x100)]
    fails = count = 0
    for k in range(n):
        count += 1
        cls = k % 16
        attr = bytearray(random_attr(rng, cls))
        attr[0x1a6] = rng.choice([0, 1, 8, 9, 2, rng.randint(0, 255)])
        hero = bytearray(0x400)
        hero[0x12] = rng.choice([cls, rng.randint(0, 255)])
        hero[0x32] = rng.randint(0, 3)
        case = {'items': [], 'buffs': {}, 'hero_class': hero[0x12], 'hero': bytes(hero),
                'visible': rng.random() < 0.9, 'tree': rng.random() < 0.5, 'tree_map': rng.choice([-1, -1, 7, 300]),
                'node': rng.random() < 0.6, 'bonus': rng.choice([0, 5, 40, rng.randint(0, 600)]),
                'effects': {0xb0: rng.random() < 0.3}, 'gt_real': rng.random() < 0.7}
        value = struct.unpack_from('<H', attr, 0x1e6 + 2 * hero[0x32])[0]
        case['tree_id_expect'] = case['tree_map'] if case['tree_map'] != -1 else value
        cache = [rng.choice([0, 100, rng.randint(0, 0xffff)]), rng.choice([0, 0x11c, rng.randint(0, 0xffff)])]
        packet = case_packet = bytes(rng.randint(0, 255) for _ in range(12))
        use_packet = rng.random() < 0.3
        m.reset()
        client.case = case
        client.lines = []
        client.setup_hero(bytes(attr))
        m.write(CHAR, bytes(hero))
        install_recv_state(client)
        m.put32(GFXMGR + 0x1f8, TREE if case['tree'] else 0)
        m.call(0x00a0088d, [cls], ecx=HERO)
        m.write(SPEED_WINDOW, bytes(0x200))
        m.write(SPEED_WINDOW + 0xbc, struct.pack('<HH', *cache))
        if use_packet:
            pkt = m.alloc(0x100, define=True)
            m.write(pkt, packet)
            m.put32(GFXMGR + 0x21c, SPEED_WINDOW)
            m.call(SPEED_PACKET, [pkt])
        else:
            m.call(SPEED_ROW, [], ecx=SPEED_WINDOW)
        want = (list(client.lines), m.read(ATTR, ATTR_SIZE).hex(), list(struct.unpack('<HH', m.read(SPEED_WINDOW + 0xbc, 4))))
        abuf = (c_uint8 * ATTR_SIZE).from_buffer_copy(bytes(attr))
        native.gt = (lambda i: b'%d / %d' if i == 0x10be and case['gt_real'] else b'GT%d' % i)
        env = native.env(abuf, case)
        env.hero_class = hero[0x12]
        c_cache = (ctypes.c_uint16 * 2)(*cache)
        if use_packet:
            native.L.mu_prg_recv_speed(ctypes.byref(env), (c_uint8 * 0x100).from_buffer_copy(packet + bytes(0x100 - 12)))
            lines = []
            for line in native.lines:
                if line == 'call 00b40380':
                    native.lines = []
                    native.L.mu_prg_speed_row(ctypes.byref(env), cls, c_cache, int(case['visible']))
                    lines += native.lines
                else:
                    lines.append(line)
            got_lines = lines
        else:
            native.L.mu_prg_speed_row(ctypes.byref(env), cls, c_cache, int(case['visible']))
            got_lines = list(native.lines)
        got = (got_lines, bytes(abuf).hex(), list(c_cache))
        if want != got:
            fails += 1
            if fails <= 5:
                report.setdefault('examples', []).append({'cls': cls, 'client': [want[0], want[2]],
                                                          'c': [got[0], got[2]], 'attr_equal': want[1] == got[1]})
    return count, fails


FAMILIES['speed'] = family_speed
FAMILIES['levelup'] = recv_family(0x01250b05, 0x18, setup_none, native_levelup)
FAMILIES['point'] = recv_family(0x01223f04, 0x0c, setup_point, native_point)
FAMILIES['exp'] = recv_family(0x01234c08, 0x0a, setup_kill, native_kill, compare_char=True, ret_byte=True)
FAMILIES['master'] = recv_family(0x01285b68, 0x0c, setup_none, native_master_up)
FAMILIES['master_exp'] = recv_family(0x01285efa, 0x18, setup_master_exp, native_master_exp)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--text', type=Path, default=EVIDENCE / 'x86-text-capture-09/client-text.bin')
    ap.add_argument('--data', type=Path, default=EVIDENCE / 'image-data-run10/data-capture-10/client-image-data.bin')
    ap.add_argument('--cases', type=int, default=200)
    ap.add_argument('--seed', type=int, default=20261022)
    ap.add_argument('--only', nargs='*', default=None)
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('--work', type=Path, default=Path('/tmp/validate_progress'))
    ap.add_argument('--report', type=Path)
    args = ap.parse_args()
    text, data = args.text.read_bytes(), args.data.read_bytes()
    if sha256(text) != TEXT_SHA256 or sha256(data) != DATA_SHA256:
        sys.exit('the pinned captures do not match')
    args.work.mkdir(parents=True, exist_ok=True)
    report = {'text': TEXT_SHA256, 'data': DATA_SHA256, 'families': {}}
    names = args.only or list(FAMILIES)
    ok = True
    native = Native()
    for name in names:
        client = Client(text, data)
        map_fake(client.m)
        rng = random.Random(f'{args.seed}-{name}')
        t0 = time.time()
        fam = {}
        count, fails = FAMILIES[name](client, native, rng, args.cases, fam)
        fam.update(cases=count, mismatches=fails, seconds=round(time.time() - t0, 1))
        report['families'][name] = fam
        print(name, json.dumps(fam)[:2000])
        ok &= fails == 0
    if args.mutations:
        report['mutations'] = {}
        for k, (mname, fname) in enumerate(MUTATIONS, 1):
            if fname not in names:
                continue
            mut = Native(k, args.work)
            client = Client(text, data)
            map_fake(client.m)
            rng = random.Random(f'{args.seed}-{fname}')
            fam = {}
            count, fails = FAMILIES[fname](client, mut, rng, args.cases, fam)
            report['mutations'][mname] = {'family': fname, 'detected': fails > 0, 'mismatching_cases': fails}
            print('mutation', mname, json.dumps(report['mutations'][mname]))
            ok &= fails > 0
    if args.report:
        args.report.write_text(json.dumps(report, indent=1))
    print('OK' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


MUTATIONS = [('dw_pvp_rate_4.5', 'calc'), ('bar_master_stage_4', 'bar'), ('bar_rate_tenth', 'bar'),
             ('table_times_9', 'table'), ('levelup_ag_floor_0', 'levelup'), ('point_energy_is_4', 'point'),
             ('button_command_is_energy', 'button'), ('speed_effect_quarter', 'speed')]

if __name__ == '__main__':
    main()
