#!/usr/bin/env python3
"""Bounded original item-display instruction runner. No client bytes embedded.

Uses the existing pure-accessor probe's pinned captures and Machine's undefined
memory checks. All text/rows/hero inputs are authored synthetic fixtures.
Actual argument words at sprintf and the round helper are recorded before models.
String/container/initialized-manager/CRT printf/pow are explicit boundaries.
"""
from pathlib import Path
import sys, struct, math, re, json, collections, random, hashlib, ctypes
import client_ui_machine as cm
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *


def i32(x):
    return ctypes.c_int32(x).value


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def wordsd(x):
    return list(struct.unpack("<II", struct.pack("<d", x)))


def fb(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def samefp(x, y):
    return (math.isnan(x) and math.isnan(y)) or struct.pack("<d", x) == struct.pack(
        "<d", y
    )


def trunc(x):
    return (
        -2147483648
        if not math.isfinite(x) or not -2147483648 <= math.trunc(x) <= 2147483647
        else math.trunc(x)
    )


ORD = [
    0x58,
    0x59,
    0x6A1,
    0x5A,
    0x5B,
    0x57,
    0x5C,
    0x276,
    0x278,
    0x279,
    0x2E7,
    0x2E8,
    0x2EA,
    0x43F,
    0x440,
    0x3BF,
    0x1337,
    0x1943,
    0x1944,
]
SPECIAL_A = {0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x38}
LABEL_B = {0xC, 0xD, 0x1E, 0x4E, 0x54, 0x59, 0x5A, 0x72, 0x73}
BASES = [
    0x16BC789,
    0xCD0DFE,
    0xD01ED9,
    0x10A9107,
    0x10A9EB9,
    0x10A9FDF,
    0xCD241F,
    0xCD2711,
    0xCD2386,
    0xCD0995,
    0x185CB38,
    0xCCC591,
    0x95FBEB,
    0x987982,
    0x95FC2E,
    0xCD1E85,
    0xA00367,
    0xA00066,
    0xA000E9,
    0x139D8EA,
    0x139CB15,
    0xA0020F,
    0xA00232,
    0x96168C,
    0xC745C1,
    0x191C5E0,
]


class DisplayMachine(cm.Machine):
    def __init__(self, text, data):
        super().__init__(text, data)
        self.allowed = [(a, cm.function_extent(text, a)) for a in BASES]
        # The floor wrapper has backward dispatch; use explicit bounded ends.
        self.allowed += [(0x1990E30, 0x1990F47)]
        self.tr = cm.STUB_BASE + 0x80000
        self.dv = self.tr + 0x80
        self.rv = self.tr + 0x90
        self.wrap = self.tr + 0x100
        self.uc.mem_write(self.tr, b"\xdd\x05" + struct.pack("<I", self.dv) + b"\xc3")
        self.boundaries = collections.Counter()
        self.cover = collections.Counter()
        self.strings = {}
        self.events = []
        self.lookups = []
        self.roundcalls = []
        self.mode = ""
        self.install()
        self.uc.hook_add(UC_HOOK_CODE, self.round_seen, begin=0xD01ED9, end=0xD01ED9)
        for a in [
            0xA0020F,
            0xA00232,
            0x96168C,
            0xC745C1,
            0x1990E70,
            0x191C601,
            0x191C5F9,
        ]:
            self.uc.hook_add(
                UC_HOOK_CODE,
                lambda u, p, z, d: self.cover.update([hex(p)]),
                begin=a,
                end=a,
            )

    def this(self):
        return self.uc.reg_read(UC_X86_REG_ECX)

    def cstr(self, p):
        b = bytearray()
        for i in range(4096):
            c = self.read(p + i, 1)
            if c == b"\0":
                return bytes(b).decode("latin1")
            b += c
        raise cm.CaseError("unterminated synthetic/format string")

    def rawstr(self, s):
        p = self.alloc(len(s) + 1)
        self.write(p, s.encode("latin1") + b"\0")
        return p

    def sets(self, p, s):
        q = self.rawstr(s)
        self.strings[p] = s
        self.write(p, struct.pack("<6I", q, 0, 0, 0, len(s), max(16, len(s))))
        return p

    def st(self, a, f, n=0):
        def handler(m):
            m.boundaries[hex(a)] += 1
            return f(m)

        self.stub(a, handler, n)

    def fp(self, x):
        self.write(self.dv, struct.pack("<d", x))
        self.uc.reg_write(UC_X86_REG_EIP, self.tr)
        return cm.REDIRECT

    def install(self):
        self.st(0x8E6D00, lambda m: m.sets(m.this(), ""))
        for a in [0x94AFDA, 0x94997E]:
            self.st(a, lambda m: m.sets(m.this(), m.cstr(m.args(1)[0])), 4)
        self.st(0x8E7410, lambda m: m.sets(m.this(), m.strings[m.args(1)[0]]), 4)
        self.st(0x8E83A0, lambda m: 0)
        for a in [0x8E7940, 0x8E7F90]:
            self.st(a, lambda m: m.u32(m.this()))
        self.st(
            0x194CD00,
            lambda m: (
                m.write(m.args(3)[0], bytes([m.args(3)[1] & 255]) * m.args(3)[2])
                or m.args(3)[0]
            ),
        )
        self.st(0x11753C3, self.global_object, 4)
        self.st(0x95F027, self.global_cstr, 4)
        self.st(0x9619DD, self.sprintf)
        self.st(0xCD4EA8, lambda m: 0x31000000)
        self.st(0xCD5FAC, self.kind_by_code, 8)
        self.st(
            0x198C480,
            lambda m: m.fp(
                math.pow(
                    *struct.unpack("<dd", m.read(m.uc.reg_read(UC_X86_REG_ESP) + 4, 16))
                )
            ),
        )

    def global_object(self, m):
        key = m.args(1)[0]
        self.lookups.append(key)
        spec = "" if key == 0x2EA else ("%.9f" if key in (0x1943, 0x1944) else "%d")
        return m.sets(m.alloc(24), f"G{key:x}=" + spec)

    def global_cstr(self, m):
        key = m.args(1)[0]
        self.lookups.append(key)
        return m.rawstr(f"L{key:x}")

    def kind_by_code(self, m):
        code, a = m.args(2)
        self.kind_calls.append([i32(code), a])
        return int(0 <= i32(code) <= 0x2C00 and a == self.kind_a)

    def sprintf(self, m):
        out, fp = m.args(2)
        fmt = m.cstr(fp)
        ap = m.uc.reg_read(UC_X86_REG_ESP) + 12
        values = []
        raw = []
        kinds = []
        for match in re.finditer(r"%(?:[-+ #0]*\d*(?:\.\d+)?)?([diufs%])", fmt):
            kind = match.group(1)
            if kind == "%":
                continue
            if kind == "f":
                w = struct.unpack("<II", m.read(ap, 8))
                x = struct.unpack("<d", m.read(ap, 8))[0]
                ap += 8
            else:
                w = (m.u32(ap),)
                ap += 4
                x = (
                    m.cstr(w[0])
                    if kind == "s"
                    else (w[0] if kind == "u" else i32(w[0]))
                )
            values.append(x)
            raw.extend(w)
            kinds.append(kind)
        # Private logs identify fixed formats by address, never export their text.
        tag = f"fixed:{fp:x}" if 0x1A7C000 <= fp < 0x1CED000 else fmt
        self.events.append({"fmt": tag, "kinds": kinds, "values": values, "words": raw})
        rendered = fmt % tuple(values)
        assert len(rendered) < 4096
        m.write(out, rendered.encode("latin1") + b"\0")
        return len(rendered)

    def round_seen(self, u, a, z, d):
        lo, hi, n = self.args(3)
        self.roundcalls.append(
            [struct.unpack("<d", struct.pack("<II", lo, hi))[0], i32(n)]
        )

    def prepare(self):
        self.reset()
        self.strings = {}
        self.events = []
        self.lookups = []
        self.roundcalls = []
        self.kind_calls = []
        self.uc.mem_write(self.tr, b"\xdd\x05" + struct.pack("<I", self.dv) + b"\xc3")
        self.uc.reg_write(UC_X86_REG_FPCW, 0x27F)
        self.uc.reg_write(UC_X86_REG_FPSW, 0)
        self.uc.reg_write(UC_X86_REG_FPTAG, 0xFFFF)
        self.uc.reg_write(UC_X86_REG_MXCSR, 0x1F80)
        self.put32(0xBDCB280, 0)
        self.put32(0xBDD1CC8, 1)
        self.item = self.alloc(0x12C, True)
        self.row = self.alloc(0x2C4, True)
        self.hero = self.alloc(0x200, True)
        self.char = self.alloc(0x20, True)
        self.manager = self.alloc(0x68 + 3 * 0x20D0)
        self.out = self.alloc(512, True)
        self.write(self.out, b"UNCHANGED\0")
        self.put32(self.item, self.row)
        self.put32(self.item + 0x10, 1)
        self.put32(0x1D1DF1C, self.hero)
        self.put32(0xA39D754, self.char)
        self.kind_a = 0

    def item_fields(self, code=1, a=1, b=1, g=0):
        self.put32(self.item + 0x10, code)
        self.write(self.row + 0x250, bytes([a, b, g]))

    def callfp(self, a, args, ecx=0, cleanup=0, limit=20000):
        code = b"".join(
            b"\x68" + struct.pack("<I", x & 0xFFFFFFFF) for x in reversed(args)
        )
        code += b"\xb9" + struct.pack("<I", ecx)
        at = self.wrap + len(code)
        code += b"\xe8" + struct.pack("<i", a - at - 5)
        if cleanup:
            code += b"\x81\xc4" + struct.pack("<I", cleanup)
        code += b"\xdd\x1d" + struct.pack("<I", self.rv) + b"\xc3"
        self.uc.mem_write(self.wrap, code)
        self.uc.ctl_flush_tb()
        self.call(self.wrap, limit=limit)
        return struct.unpack("<d", self.read(self.rv, 8))[0]

    def ordinary(self, opt, value, code=1, flag=0, a=1, reuse=False):
        if not reuse:
            self.prepare()
        else:
            self.events = []
            self.lookups = []
            self.kind_calls = []
            self.write(self.out, b"UNCHANGED\0")
        self.kind_a = a
        ret = (
            self.call(0x16BC789, [code, self.out, opt, value, flag], limit=10000) & 255
        )
        return ret, self.cstr(self.out), self.events, self.lookups

    def excellent(
        self,
        mode,
        value,
        code=1,
        a=1,
        b=1,
        category=1,
        opt=0,
        level=400,
        master=0,
        hero_class=0,
        record_level=0,
    ):
        self.prepare()
        self.item_fields(code, a, b)
        self.write(self.item + 0xA3, bytes([category]))
        self.write(self.row + 0x254, struct.pack("<H", record_level))
        self.put32(self.hero, level)
        self.put32(self.hero + 0x18, master)
        self.write(self.hero + 0x187, bytes([hero_class]))
        fmt = {0: "E0=%d", 1: "E1=%s,%d", 2: "E2=%s,%.9f", 3: "E3=static"}.get(
            mode, "unused"
        )
        s = self.alloc(24)
        self.sets(s, fmt)
        args = [
            self.out,
            *struct.unpack("<6I", self.read(s, 24)),
            mode,
            opt,
            *wordsd(value),
        ]
        # By-value std::string object lives in the argument block, constructed by caller.
        esp = cm.STACK_BASE + cm.STACK_SIZE - 0x1000 - 4 * (len(args) + 1)
        self.strings[esp + 8] = fmt
        ret = self.call(0xCD0DFE, args, ecx=self.item, limit=20000)
        return (
            self.strings[self.out],
            self.events,
            self.lookups,
            self.roundcalls,
            ret == self.out,
        )

    def round(self, x, n, feature=0):
        self.prepare()
        self.put32(0xBDCB280, feature)
        return self.callfp(0xD01ED9, [*wordsd(x), n], cleanup=12)

    def socket(
        self,
        typ,
        value,
        class_byte=0,
        fields=(120003, 220005, 320007, 420009),
        seed=None,
        level=1,
        element=1,
    ):
        self.prepare()
        self.write(self.char + 0x12, bytes([class_byte]))
        for off, x in zip([0x40, 0x44, 0x70, 0x74], fields):
            self.put32(self.hero + off, x)
        if seed is None:
            self.call(
                0x10A9EB9, [self.out, typ, fb(value)], ecx=self.manager, limit=20000
            )
        else:
            r = self.manager + 0x68 + seed * 0xA8
            self.write(r, b"\0" * 0xA8)
            self.put32(r + 4, element)
            self.write(r + 12, f"row{seed}".encode() + b"\0")
            self.put32(r + 0x4C, typ)
            self.put32(r + 0x4C + 4 * level, value)
            self.call(0x10A9107, [self.out, seed, level], ecx=self.manager, limit=20000)
        return self.cstr(self.out), self.events, self.lookups

    def socketvalue(
        self, typ, value, class_byte=0, fields=(120003, 220005, 320007, 420009)
    ):
        self.prepare()
        self.write(self.char + 0x12, bytes([class_byte]))
        for off, x in zip([0x40, 0x44, 0x70, 0x74], fields):
            self.put32(self.hero + off, x)
        return self.callfp(0x10A9FDF, [typ, fb(value)], ecx=self.manager)

    def harmony(self, c):
        self.prepare()
        self.item_fields(c.get("code", 1), c.get("a", 1), c.get("b", 1), c.get("g", 0))
        self.write(self.item + 0x6E, struct.pack("<H", c.get("h", 1)))
        self.write(self.item + 0x3B, bytes([c.get("ancient", 0)]))
        self.write(self.item + 0x92, bytes([c.get("period", 0)]))
        self.write(self.row + 0x256, bytes([c.get("slot", 15)]))
        self.write(self.row + 0x2A8, bytes(c.get("flags", [0, 0, 0, 0])))
        return self.call(0xCD241F, ecx=self.item, limit=20000) & 255
