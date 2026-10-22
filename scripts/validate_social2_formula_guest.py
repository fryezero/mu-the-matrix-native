#!/usr/bin/env python3
"""Private bounded x86 FormulaData probe. No original bytes embedded.
Original parser/precedence/tokenizer/evaluator execute; C++ containers, string
bookkeeping, printf, atof, pow and gcvt are named models below.
Captures and synthetic/table inputs are passed by validate_social2.
"""
from pathlib import Path
import sys, struct, hashlib, ctypes as C, math, json, re, random, collections
import client_ui_machine as cm
from unicorn import UC_PROT_ALL, UC_HOOK_CODE
from unicorn.x86_const import *

H = 0x7FFA0000
HV = H + 0xF00
HO = H + 0xF10
libc = C.CDLL(None)
libc.gcvt.argtypes = [C.c_double, C.c_int, C.c_void_p]
libc.gcvt.restype = C.c_void_p
libc.atof.argtypes = [C.c_char_p]
libc.atof.restype = C.c_double


def gcvt(x):
    b = C.create_string_buffer(128)
    libc.gcvt(x, 10, b)
    return b.value.decode("ascii")


def s32(x):
    return C.c_int32(x).value


def cstring(m, p):
    b = bytearray()
    for i in range(4096):
        c = m.read(p + i, 1)
        if c == b"\0":
            return bytes(b).decode("latin1")
        b += c
    raise ValueError("unterminated string")


class FormulaMachine(cm.Machine):
    def __init__(self, text, data, rows):
        super().__init__(text, data)
        self.rows = {(x["group"], x["index"]): x["expr"] for x in rows}
        self.vectors = {}
        self.stacks = {}
        self.boundaries = collections.Counter()
        self.formatted = []
        self.postfix = []
        self.uc.mem_map(H, 0x1000, UC_PROT_ALL)
        self.uc.mem_write(H, b"\xdd\x05" + struct.pack("<I", HV) + b"\xc3")
        self.allowed = [
            (0x117B576, 0x117B727),
            (0x1200017, 0x1201364),
            (0x1201B96, 0x1201BDB),
        ]
        self.install()

    def this(self):
        return self.uc.reg_read(UC_X86_REG_ECX)

    def string(self, p):
        return cstring(self, self.u32(p) if self.u32(p + 20) >= 16 else p)

    def sets(self, p, s):
        b = s.encode("latin1")
        q = self.alloc(len(b) + 1)
        self.write(q, b + b"\0")
        self.write(p, struct.pack("<6I", q, 0, 0, 0, len(b), max(16, len(b))))
        return p

    def retfp(self, x):
        self.write(HV, struct.pack("<d", x))
        self.uc.reg_write(UC_X86_REG_EIP, H)
        return cm.REDIRECT

    def st(self, a, f, n=0):
        def wrap(m):
            m.boundaries[hex(a)] += 1
            return f(m)

        self.stub(a, wrap, n)

    def install(self):
        st = self.st
        st(0x8E6D00, lambda m: m.sets(m.this(), ""))
        for a in [0x94997E, 0x94AFDA]:
            st(a, lambda m: m.sets(m.this(), cstring(m, m.args(1)[0])), 4)
        for a in [0x8E62B0, 0x94AF7D, 0x8E7410, 0x8E80E0]:
            st(a, lambda m: m.sets(m.this(), m.string(m.args(1)[0])), 4)
        st(0x8E83A0, lambda m: 0)
        st(0x8E7940, lambda m: m.u32(m.this()))
        st(0x8E6D80, lambda m: m.u32(m.this() + 16))
        st(0x94B48C, lambda m: m.u32(m.this()) + m.args(1)[0], 4)
        st(0xB8EB3C, lambda m: m.sets(m.this(), chr(m.args(1)[0] & 255)), 4)
        st(
            0x8E6DA0,
            lambda m: m.sets(m.this(), m.string(m.this()) + m.string(m.args(1)[0])),
            4,
        )
        st(
            0x94B9F7,
            lambda m: m.sets(m.this(), m.string(m.this()) + cstring(m, m.args(1)[0])),
            4,
        )
        st(
            0x8E6200,
            lambda m: (
                m.put32(m.args(1)[0], m.u32(m.this()) + m.u32(m.this() + 16))
                or m.args(1)[0]
            ),
            4,
        )
        st(
            0x8E6290,
            lambda m: (m.put32(m.args(1)[0], m.u32(m.this())) or m.args(1)[0]),
            4,
        )

        def remove(m):
            out, start, end, cp = m.args(4)
            ch = m.read(cp, 1)
            b = m.read(start, end - start)
            q = start
            for c in b:
                if bytes([c]) != ch:
                    m.write(q, bytes([c]))
                    q += 1
            m.put32(out, q)
            return out

        st(0xC46F13, remove)

        def erase(m):
            out, a, b = m.args(3)
            start = m.u32(m.this())
            s = m.string(m.this())
            off = a - start
            new = m.sets(m.this(), s[:off] + s[b - start :])
            m.put32(out, m.u32(new) + off)
            return out

        st(0xC47143, erase, 12)
        st(
            0x1201813,
            lambda m: sum(
                c == m.read(m.args(3)[2], 1)[0]
                for c in m.read(m.args(3)[0], m.args(3)[1] - m.args(3)[0])
            ),
        )
        st(
            0x94498A,
            lambda m: m.sets(
                m.args(3)[0], cstring(m, m.args(3)[1]) + m.string(m.args(3)[2])
            ),
        )
        st(
            0x944959,
            lambda m: m.sets(
                m.args(3)[0], m.string(m.args(3)[1]) + cstring(m, m.args(3)[2])
            ),
        )
        st(0x96C6DA, lambda m: int(m.string(m.args(2)[0]) == cstring(m, m.args(2)[1])))
        st(0x90EDB0, lambda m: int(m.string(m.args(2)[0]) == m.string(m.args(2)[1])))
        st(0x949EDD, lambda m: (m.vectors.__setitem__(m.this(), []) or m.this()))
        st(
            0x9515A1,
            lambda m: (m.vectors[m.this()].append(m.string(m.args(1)[0])) or 0),
            4,
        )
        st(0x94AB97, lambda m: 0)
        st(0x96A4D8, lambda m: len(m.vectors[m.this()]))

        def vecat(m):
            p = m.alloc(24)
            return m.sets(p, m.vectors[m.this()][m.args(1)[0]])

        st(0xB3B292, vecat, 4)
        for a in [0x12019F9, 0x12019E4]:
            st(a, lambda m: (m.stacks.__setitem__(m.this(), []) or m.this()))
        for a in [0x1201B05, 0x1201AF3]:
            st(a, lambda m: 0)
        for a in [0x12021E8, 0x12021D7]:
            st(a, lambda m: int(not m.stacks[m.this()]))
        for a in [0x120224B, 0x1202239]:
            st(a, lambda m: (m.stacks[m.this()].pop() and 0))
        st(
            0x12022F7,
            lambda m: (m.stacks[m.this()].append(m.string(m.args(1)[0])) or 0),
            4,
        )

        def tokpush(m):
            m.stacks[m.this()].append(m.read(m.args(1)[0], 32))
            return 0

        st(0x1202315, tokpush, 4)

        def top(m):
            x = m.stacks[m.this()][-1]
            p = m.alloc(56)
            if isinstance(x, str):
                return m.sets(p, x)
            m.write(p, x)
            return p

        for a in [0x1202382, 0x1202371]:
            st(a, top)

        def tokcopy(m):
            p = m.args(1)[0]
            m.sets(m.this(), m.string(p))
            m.write(m.this() + 24, m.read(p + 24, 8))
            return m.this()

        st(0x1201B17, tokcopy, 4)
        st(
            0x194CD00,
            lambda m: (
                m.write(m.args(3)[0], bytes([m.args(3)[1] & 255]) * m.args(3)[2])
                or m.args(3)[0]
            ),
        )
        st(0x966C42, lambda m: 0x300F0000)
        st(0x117CD60, lambda m: 0x300F1000)
        st(0x1183AAA, lambda m: int(tuple(map(s32, m.args(2))) in m.rows), 8)
        # Two nested associative container operations; getter body, default and copy run.
        st(
            0x117CC98,
            lambda m: (
                m.savedkey.__setitem__(0, s32(m.u32(m.args(1)[0]))) or 0x300F2000
            ),
            4,
        )

        def inner(m):
            idx = s32(m.u32(m.args(1)[0]))
            expr = m.rows[(m.savedkey[0], idx)]
            p = m.alloc(260)
            m.write(p, struct.pack("<i", idx) + expr.encode() + b"\0")
            return p

        st(0x117CC4F, inner, 4)
        self.savedkey = [0]

        def fmt(m):
            out, fp, ap = m.args(3)
            f = cstring(m, fp)
            args = []
            for spec in re.findall(r"%(?:\.\d+)?[df]", f):
                if spec.endswith("d"):
                    args.append(s32(m.u32(ap)))
                    ap += 4
                else:
                    args.append(struct.unpack("<d", m.read(ap, 8))[0])
                    ap += 8
            s = f % tuple(args)
            assert len(s) < 256
            m.write(out, s.encode() + b"\0")
            m.formatted.append(s)
            return len(s)

        st(0x98D2AA, fmt)
        st(0x1985654, lambda m: m.retfp(libc.atof(cstring(m, m.args(1)[0]).encode())))
        st(
            0x198C480,
            lambda m: m.retfp(
                math.pow(
                    *struct.unpack("<dd", m.read(m.uc.reg_read(UC_X86_REG_ESP) + 4, 16))
                )
            ),
        )

        def gcvtstub(m):
            out, n, lo, hi, digits = m.args(5)
            assert n == 32 and digits == 10
            x = struct.unpack("<d", struct.pack("<II", lo, hi))[0]
            s = gcvt(x)
            assert len(s) < n
            m.write(out, s.encode() + b"\0")
            return 0

        st(0x19968FC, gcvtstub)

        def postfix(m):
            m.postfix.append(m.string(m.args(1)[0]))

        self.uc.hook_add(
            UC_HOOK_CODE,
            lambda u, a, z, d: postfix(self),
            begin=0x120102B,
            end=0x120102B,
        )

    def eval(self, g, i, words):
        self.reset()
        self.vectors = {}
        self.stacks = {}
        self.savedkey = [0]
        self.formatted = []
        self.postfix = []
        self.put32(0x300F0004, 0x300F0100)
        self.uc.reg_write(UC_X86_REG_FPCW, 0x27F)
        self.uc.reg_write(UC_X86_REG_FPSW, 0)
        self.uc.reg_write(UC_X86_REG_FPTAG, 0xFFFF)
        self.uc.mem_write(H, b"\xdd\x05" + struct.pack("<I", HV) + b"\xc3")
        argc = 3 + len(words)
        code = b""
        for _ in range(argc):
            code += b"\xff\x74\x24" + bytes([4 * argc])
        a = H + 0x100
        call = a + len(code)
        code += (
            b"\xe8"
            + struct.pack("<i", 0x117B5EB - call - 5)
            + b"\x83\xc4"
            + bytes([4 * argc])
            + b"\xdd\x1d"
            + struct.pack("<I", HO)
            + b"\xc3"
        )
        self.uc.mem_write(a, code)
        self.uc.ctl_flush_tb()
        self.call(a, [0x300F0000, g, i, *words], limit=200000)
        return struct.unpack("<d", self.read(HO, 8))[0]
