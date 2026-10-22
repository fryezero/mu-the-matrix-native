"""Whole original option finalizer/value routines with explicit synthetic external inputs.

No client bytes are embedded. Tiny x86 return/call wrappers below are authored
ABI fixtures. Captures are passed by the hash-checking validation entry point.
"""

import argparse, collections, hashlib, json, math, random, struct, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
from client_ui_machine import Machine, TEXT_BASE, STUB_BASE, REDIRECT, function_extent
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP

PHYS = set(range(1, 12)) | {0x4B, 0x51, 0x7B}
MAG = {0xC, 0xD, 0x4E, 0x54, 0x59, 0x5A, 0x72, 0x73}
ARM = set(range(0x10, 0x15))
SPECIAL_A = {0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x38}
LUCK = {1, 3, 6, 14, 15, 18, 27, 33, 55}
# Ordered branches ccce34..ccd9a4. Lists are authored from immediate comparisons.
GROUPS = [
    ("single6", [0x1800]),
    ("single1", [0x1801, 0x1829, 0x189B]),
    ("single0", [0x1802, 0x18AC, 0x18AD, 0x2A00]),
    ("bit20_6_0", [0x1803, 0x19A8]),
    ("bit20_1_6", [0x1804, 0x19A6, 0x189C, 0x189D]),
    ("bit20_0_6", [0x1805, 0x19A7, 0x18AE, 0x18AF]),
    ("bit20_0_1", [0x1806, 0x19A9]),
    ("single0", [0x1A1E, 0x19AA, 0x1917, 0x191A]),
    ("dual01", [0x1918]),
    ("class", [0x1919]),
    ("bit20_0_6", [0x1831, 0x190D, 0x19AC, 0x19AD]),
    ("bit20_1_2", [0x182A, 0x19AB]),
    (
        "bits10_0_4_6",
        [
            0x1824,
            0x19AF,
            0x199F,
            0x19B7,
            0x18B0,
            0x18B1,
            0x18B2,
            0x18B3,
            0x18B5,
            0x18C1,
            0x2A01,
            0x2A02,
            0x2A03,
            0x2A04,
            0x2A05,
        ],
    ),
    (
        "bits10_1_4_6",
        [
            0x1825,
            0x19AE,
            0x199E,
            0x19B6,
            0x19D3,
            0x19D4,
            0x19D5,
            0x19D6,
            0x19E9,
            0x19F0,
            0x19EA,
            0x19F1,
            0x189E,
            0x189F,
            0x18A0,
            0x18A1,
            0x181B,
            0x181C,
            0x1898,
            0x1899,
            0x18B4,
            0x18BC,
            0x18BE,
            0x18BF,
            0x18C0,
            0x18C2,
            0x18C3,
            0x18C4,
            0x18C5,
            0x18C6,
        ],
    ),
    ("bits10_0_4_6", [0x1826, 0x19B0, 0x19A0, 0x19B8, 0x18B6]),
    ("bits10_0_1_6", [0x1827, 0x19B1, 0x19A1, 0x19B9, 0x18B7]),
    (
        "bits10_0_4_6",
        [
            0x1828,
            0x1832,
            0x190E,
            0x19B2,
            0x19B4,
            0x19B5,
            0x19A2,
            0x19A4,
            0x19A5,
            0x19BA,
            0x19BC,
            0x19BD,
            0x18B8,
            0x18BA,
            0x18BB,
        ],
    ),
    ("bits10_1_2_6", [0x182B, 0x19B3, 0x19A3, 0x19BB, 0x18B9]),
    ("bits10_0_4_6", [0x19D8, 0x19D9, 0x19DA, 0x19DB, 0x18BD]),
]
CODE_GROUP = {c: n for n, cs in GROUPS for c in cs}


def i32(x):
    return (x + 2**31) % 2**32 - 2**31


def formula(family, index, p1, p2):
    # Synthetic callback deliberately includes negative fractions. No real table values.
    return ((family * 13 + index * 7 + p1 * 3 - p2 * 5) % 101 - 50) / 4 + 0.125


def formula_selector(opt, cat):
    return {
        (1, 6): 0,
        (1, 7): 1,
        (2, 6): 2,
        (2, 7): 3,
        (2, 8): 4,
        (2, 9): 5,
        (2, 10): 6,
        (2, 11): 9,
        (2, 12): 10,
    }.get((cat, opt), -1)


def classify(a, b, cache):
    if cache[0]:
        return list(cache)
    if a in {1, 2, 14, 0x2D}:
        return [1, 1]
    if a in {3, 4, 15, 18, 27, 33, 55, 0x2E, 0x2F, 0x30, 0x31, 0x38}:
        return [1, 2]
    if a == 6:
        return [2, b]
    return list(cache)


BASE = {
    "a": 1,
    "b": 1,
    "g": 0,
    "code": 1,
    "L": 0,
    "E": 0,
    "N": 0,
    "level_word": 0,
    "ancient": 0,
    "class_byte": 5,
    "char_stat": 1234,
    "record_skill": 321,
    "skill_initial": 99,
    "special_level": 7,
    "enabled": 1,
    "present": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 254],
    "cache": [0, 0],
    "excellent_initial": 0,
    "ex_initial": [255] * 9,
    "extra": [255] * 3,
    "special_row": 1,
    "special_enabled": 1,
    "special_tag": 77,
    "special_bonus": [11, 22, 33],
    "special_lows": [1, 2, 3],
}


def case(**kw):
    r = dict(BASE)
    r.update(kw)
    return r


class Oracle:
    def __init__(self, TEXT, DATA):
        self.m = m = Machine(TEXT, DATA)
        self.trace = []
        self.requests = []
        self.vectors = {}
        self.cover = collections.Counter()
        starts = [
            0xCCC993,
            0xCCFFF3,
            0xCCC591,
            0x95FC2E,
            0x987982,
            0x95FBEB,
            0xCD0995,
            0xCD1DFC,
            0xCD1E38,
            0xCD1E65,
            0xCD1E85,
            0xCD1ED8,
            0xCD21F6,
            0xCD2175,
            0xCD2326,
            0xCD0033,
            0xCD01D4,
            0xCD0253,
            0xCD032A,
            0xC93C17,
            0x95F5CC,
            0xCD5E16,
            0xCD5E73,
            0xCD5EDA,
            0xCD0D49,
            0x117B857,
        ]
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32

        dis = Cs(CS_ARCH_X86, CS_MODE_32)
        # Real map lookup and all direct descendants, deliberately excluding insertion/file I/O.
        pending = [0xCD9F0F, 0xCD9EBB, 0xCD8C94, 0xCD8D0A]
        seen = set()
        while pending:
            a = pending.pop()
            if a in seen:
                continue
            seen.add(a)
            end = function_extent(TEXT, a)
            assert end - a < 0x1000
            for ins in dis.disasm(TEXT[a - TEXT_BASE : end - TEXT_BASE], a):
                if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
                    pending.append(int(ins.op_str, 16))
        starts += sorted(seen)
        for a in set(starts):
            m.allow((a, function_extent(TEXT, a)))
        self.real_ranges = sorted(set(m.allowed))
        m.stub(0xCD4EA8, lambda m: self.manager)
        m.stub(0xCD1534, lambda m: self.c["enabled"])
        m.stub(0xC9362D, lambda m: self.special)
        m.stub(0x966C42, lambda m: 0x31415920)
        m.stub(0x117B5EB, self.eval)
        m.stub(0xA00367, lambda m: self.c.get("char_level", 350))
        m.stub(0xCCB9B6, self.copy)
        m.stub(0x194CD00, self.zero)
        m.stub(0xA6E8D1, self.clearvec)
        m.stub(0xCD4923, self.appendvec, 4)
        m.stub(0xA6E46A, lambda m: 0)
        m.stub(0xCD410A, lambda m: 0)
        m.stub(0x10ED9F5, self.specialrow, 8)
        m.stub(0x10EDA8D, self.specialbonus, 8)
        m.uc.hook_add(UC_HOOK_CODE, self.record_request, begin=0xCD01D4, end=0xCD01D4)
        # Synthetic x87 return trampoline, with original return address still on stack.
        self.tramp = STUB_BASE + 0x80000
        self.double = STUB_BASE + 0x80080
        m.uc.mem_write(
            self.tramp, b"\xdd\x05" + struct.pack("<I", self.double) + b"\xc3"
        )
        self.value_wrapper = STUB_BASE + 0x80100

    def copy(self, m):
        dst, cap, src, n = m.args(4)
        assert n <= cap
        m.write(dst, m.read(src, n))
        return 0

    def zero(self, m):
        dst, v, n = m.args(3)
        m.write(dst, bytes([v & 255]) * n)
        return dst

    def clearvec(self, m):
        self.vectors[m.uc.reg_read(UC_X86_REG_ECX)] = []
        return 0

    def appendvec(self, m):
        p = m.args(1)[0]
        v = [m.u32(p), m.read(p + 4, 1)[0], m.read(p + 5, 1)[0]]
        self.vectors.setdefault(m.uc.reg_read(UC_X86_REG_ECX), []).append(v)
        return 0

    def specialrow(self, m):
        out, keyptr = m.args(2)
        assert m.u32(keyptr) == self.c.get("row_key", 42)
        m.write(
            out, b"\0" * 0xDC + struct.pack("<i", 0 if self.c["special_row"] else -1)
        )
        m.write(out + 0xD4, bytes([self.c["special_tag"]]))
        return out

    def specialbonus(self, m):
        out, row = m.args(2)
        m.write(out, b"\0" * 0x80)
        m.put32(out, self.c["special_enabled"])
        for i, (v, lo) in enumerate(
            zip(self.c["special_bonus"], self.c["special_lows"])
        ):
            m.put32(out + 0x20 + 4 * i, v)
            m.write(out + 0x2C + 4 * i, bytes([lo]))
        return out

    def record_request(self, uc, a, n, u):
        self.requests.append(self.m.args(2))

    def eval(self, m):
        mgr, f, idx, p, q = m.args(5)
        assert mgr == 0x31415920
        f, idx, p, q = map(i32, (f, idx, p, q))
        self.trace.append([f, idx, p, q])
        v = formula(f, idx, p, q)
        m.uc.mem_write(self.double, struct.pack("<d", v))
        m.uc.reg_write(UC_X86_REG_EIP, self.tramp)
        return REDIRECT

    def tree(self, ptr, rows):
        m = self.m
        head = m.alloc(0x18, True)
        m.write(head, b"\0" * 0x18)
        m.write(head + 0xD, b"\1")

        def rec(items, parent):
            if not items:
                return head
            k, r = items[len(items) // 2]
            node = m.alloc(0x18, True)
            m.write(node, b"\0" * 0x18)
            m.put32(node + 4, parent)
            m.put32(node + 0x10, k)
            m.put32(node + 0x14, r)
            m.put32(node, rec(items[: len(items) // 2], node))
            m.put32(node + 8, rec(items[len(items) // 2 + 1 :], node))
            return node

        root = rec(sorted(rows.items()), head)
        m.put32(head + 4, root)
        m.put32(head, root)
        m.put32(head + 8, root)
        m.put32(ptr, head)
        m.put32(ptr + 4, len(rows))

    def setup(self, c):
        self.c = c
        m = self.m
        m.reset()
        self.trace = []
        self.requests = []
        self.vectors = {}
        self.item = m.alloc(0x12C, True)
        m.write(self.item, b"\0" * 0x12C)
        self.record = m.alloc(0x2C4, True)
        m.write(self.record, b"\0" * 0x2C4)
        self.char = m.alloc(0x400, True)
        m.write(self.char, b"\0" * 0x400)
        self.special = m.alloc(0x30, True)
        m.write(self.special, b"\0" * 0x30)
        self.manager = m.alloc(0x300, True)
        m.write(self.manager, b"\0" * 0x300)
        m.put32(self.item, self.record)
        m.put32(self.item + 0x10, c["code"])
        m.put32(self.item + 0x14, c["level_word"])
        m.write(self.item + 0x3B, bytes([c["ancient"]]))
        m.write(self.item + 0x60, struct.pack("<H", c["skill_initial"]))
        m.write(
            self.item + 0x98,
            bytes(
                [c["excellent_initial"]] + c["ex_initial"][:6] + c["extra"] + c["cache"]
            ),
        )
        m.write(self.record + 0x250, bytes([c["a"], c["b"], c["g"]]))
        m.write(self.record + 0x254, struct.pack("<H", c.get("record_level", 77)))
        m.write(self.record + 0x258, struct.pack("<H", c["record_skill"]))
        m.put32(self.record + 4, c.get("row_key", 42) << 16)
        m.write(self.char + 0x187, bytes([c["class_byte"]]))
        m.write(self.char + 0x18C, struct.pack("<H", c["char_stat"]))
        m.put32(0x1D1DF1C, self.char)
        m.write(self.special + 0x10, struct.pack("<H", c["special_level"]))
        self.tree(self.manager + 0x2D0, self.rows(c, 1))
        self.tree(self.manager + 0x2D8, self.rows(c, 2))

    def rows(self, c, t):
        m = self.m
        rows = {}
        # All categories used by synthetic records are included, maps have distinct pointers.
        cat = classify(c["a"], c["b"], c["cache"])[1]
        for opt in c.get("present_common" if t == 1 else "present_wing", c["present"]):
            r = m.alloc(0x78, True)
            m.write(r, b"\0" * 0x78)
            m.write(r, bytes([cat, opt]))
            rows[(cat << 8) + opt] = r
        return rows

    def run(self, c):
        self.setup(c)
        m = self.m
        m.call(0xCCC993, [c["L"], c["E"], c["N"]], ecx=self.item, limit=100000)
        n = m.read(self.item + 0x3D, 1)[0]
        assert n <= 8, n
        result = {
            "options": [
                [
                    struct.unpack("<H", m.read(self.item + 0x3E + 2 * i, 2))[0],
                    struct.unpack("<H", m.read(self.item + 0x4E + 2 * i, 2))[0],
                ]
                for i in range(n)
            ],
            "rank": struct.unpack("<H", m.read(self.item + 0x5E, 2))[0],
            "skill": struct.unpack("<H", m.read(self.item + 0x60, 2))[0],
            "excellent": m.read(self.item + 0x98, 1)[0],
            "ex": list(m.read(self.item + 0x99, 9)),
            "cache": list(m.read(self.item + 0xA2, 2)),
            "requests": self.requests,
            "formulas": self.trace,
            "special_decoded": self.vectors.get(self.item + 0xA4, []),
            "special_bonus": self.vectors.get(self.item + 0xB0, []),
        }
        return result

    def value(self, c, opt, typ, base):
        self.setup(c)
        m = self.m
        # call cd0d49 and preserve returned x87 binary64 through a synthetic wrapper.
        dst = self.double + 16
        code = (
            b"".join(
                b"\x68" + struct.pack("<I", v & 0xFFFFFFFF) for v in [base, typ, opt]
            )
            + b"\xb9"
            + struct.pack("<I", self.item)
        )
        code += (
            b"\xb8"
            + struct.pack("<I", 0xCD0D49)
            + b"\xff\xd0\xdd\x1d"
            + struct.pack("<I", dst)
            + b"\xc3"
        )
        m.uc.mem_write(self.value_wrapper, code)
        m.uc.ctl_remove_cache(self.value_wrapper, self.value_wrapper + len(code))
        m.call(self.value_wrapper, limit=100000)
        return struct.unpack("<d", m.read(dst, 8))[0], list(self.trace)


def cases():
    yield case(a=6, b=28, E=0x20, present_common=[], present_wing=[0])
    yield case(a=6, b=28, E=0x20, present_common=[0], present_wing=[])
    # Every special immediate code, all selector-bit combinations and rank boundaries.
    codes = sorted(
        set(CODE_GROUP)
        | {
            0x1A03,
            0x1A04,
            0x28F7,
            0x1A14,
            0x1A18,
            0x1A1C,
            0x1908,
            0x191E,
            0x190A,
            0x190C,
            1,
        }
    )
    for code in codes:
        for rank in [0, 1, 3, 4, 7]:
            for e in [0, 0x10, 0x20, 0x30]:
                yield case(
                    code=code,
                    a=2 if code in {0x1A18, 0x1A1C} else 6,
                    b=0x1C if code in {0x1908, 0x191E} else 0,
                    L=(rank & 3) | 4 | 128,
                    E=e | (0x40 if rank & 4 else 0),
                    level_word=3 << 3,
                    extra=[6, 255, 7],
                )
    for a in range(57):
        for b in sorted(PHYS | MAG | ARM | {14, 15, 0, 0x1C}):
            for level in [9, 10, 15]:
                yield case(
                    a=a,
                    b=b,
                    L=135,
                    E=0x7F,
                    level_word=level << 3,
                    ancient=0x33,
                    extra=[6, 7, 254],
                )
    rng = random.Random(993)
    for i in range(800):
        c = case(
            a=rng.randrange(57),
            b=rng.randrange(256),
            g=rng.choice([0, 2, 6, 8]),
            code=rng.choice(codes),
            L=rng.randrange(256),
            E=rng.randrange(256),
            N=rng.randrange(256),
            level_word=rng.getrandbits(32),
            ancient=rng.randrange(256),
            class_byte=rng.choice([5, 0x15, 4, 0x25]),
            char_stat=rng.randrange(65536),
            record_skill=rng.choice([0, 321]),
            skill_initial=99,
            special_level=rng.randrange(20),
            enabled=rng.randrange(2),
            cache=rng.choice([[0, 0], [1, 1], [1, 2], [2, 28], [3, 7]]),
            excellent_initial=rng.choice([0, 1, 2]),
            extra=[rng.choice([255, 6, 7, 8, 254]) for _ in range(3)],
            present=rng.sample([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 254], rng.randrange(12)),
            special_row=rng.randrange(2),
            special_enabled=rng.randrange(2),
            ex_initial=[rng.choice([255, 0, 8, 17, 254]) for _ in range(9)],
        )
        yield c
    # Directed stale state, A19 rewrite, missing rows, suppression, formula truncation.
    for a in [1, 2, 6, 19, 0x2D, 0x2E, 0x2F]:
        for g in [0, 2, 6, 8]:
            for p in [[], [0, 1, 2, 3, 4, 5, 6, 7, 8]]:
                yield case(
                    a=a,
                    g=g,
                    L=0,
                    E=63,
                    extra=[6, 7, 8],
                    present=p,
                    ex_initial=[17, 255, 40, 254, 0, 91, 92, 93, 94],
                )


def run(lib, text, data, limit=None):
    from validate_social2_finalizer import compare_case, compare_value

    oracle = Oracle(text, data)
    reports = {
        "item_finalizer": {"cases": 0, "mismatches": 0},
        "excellent_value": {"cases": 0, "mismatches": 0},
    }

    def check(f, a, b, c):
        r = reports[f]
        r["cases"] += 1
        if a != b:
            r["mismatches"] += 1
            r.setdefault("first", {"input": c, "client": a, "native": b})

    for i, c in enumerate(cases()):
        if limit is not None and i >= limit:
            break
        check("item_finalizer", oracle.run(c), compare_case(lib, c), c)
    for cat in [0, 1, 2, 28]:
        for opt in range(14):
            for typ in [0, 1, 2, 3, 6, 100, 255]:
                for level in [0, 9, 15]:
                    c = case(cache=[1, cat], level_word=level << 3)
                    actual, trace = oracle.value(c, opt, typ, -17)
                    value, native_trace = compare_value(
                        lib, cat, opt, typ, -17, level << 3, 77, 350
                    )
                    check(
                        "excellent_value",
                        [actual, trace],
                        [value, native_trace],
                        [cat, opt, typ, level],
                    )
    return reports
