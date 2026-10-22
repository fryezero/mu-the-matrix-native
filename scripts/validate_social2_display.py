"""Original display-selector semantics against production C, with explicit CRT boundaries."""

import ctypes as C
import random
import math
import struct
from validate_social2_display_guest import DisplayMachine
from validate_social2_finalizer import Context
from validate_social2_items import Decoded

I = C.c_int32


class Display(C.Structure):
    _fields_ = [(n, I) for n in ("text", "label", "kind", "integer", "suppressed")] + [
        ("real", C.c_double)
    ]


def run(lib, text, data, cases):
    from validate_social2 import Wire

    ptr = C.POINTER(Display)
    lib.mu_social_ordinary_display.argtypes = [I, I, C.c_uint, I, I, ptr]
    lib.mu_social_excellent_display.argtypes = [
        I,
        I,
        I,
        I,
        I,
        I,
        C.c_double,
        I,
        I,
        I,
        ptr,
    ]
    lib.mu_social_socket_display.argtypes = [I, C.c_float, I, I, I, I, ptr]
    lib.mu_social_harmony_visible.argtypes = [C.POINTER(Wire), C.POINTER(Context)]
    lib.mu_social_item_convert.argtypes = [
        C.POINTER(Wire),
        C.POINTER(Context),
        C.POINTER(Decoded),
    ]
    rng = random.Random(387)
    m = DisplayMachine(text, data)
    reports = {}

    def check(f, a, b):
        r = reports.setdefault(f, dict(cases=0, mismatches=0))
        r["cases"] += 1
        if a != b:
            r["mismatches"] += 1
            r.setdefault("first", dict(client=repr(a), native=repr(b)))

    def fp(x):
        return "nan" if math.isnan(x) else struct.pack("<d", x).hex()

    for k in range(cases):
        d = Display()
        code = rng.choice([1, -1, 0x2C01, 0x1A0D, 0x1A0E, 0x1A12, 0x1A13])
        a = rng.choice([1, 45, 47, 48, 49, 46, 56])
        b = rng.choice([1, 12, 13, 14, 30, 78, 84, 89, 90, 114, 115])
        opt = k % 22
        v = rng.choice([-2147483648, 2147483647, -101, 0, 65535, 123456])
        flag = k % 2
        ret, _, events, lookups = m.ordinary(opt, v, code, flag, a)
        r = lib.mu_social_ordinary_display(code, a, opt, v, flag, C.byref(d))
        observed = (ret, bool(events), lookups, events[0]["values"] if events else [])
        native = (
            r,
            bool(r and not d.suppressed),
            [d.text] if r and not d.suppressed else [],
            (
                []
                if d.suppressed or not r or d.kind == 0
                else [d.real if d.kind == 2 else d.integer]
            ),
        )
        check("ordinary_display", observed, native)
        mode = k % 5
        category = k % 4
        id = k % 13
        value = rng.choice(
            [0.0, -19.5, 1.25, 12.05, 12345.678, float("inf"), float("nan")]
        )
        hero = 1 + rng.randrange(1200)
        base = rng.randrange(65536)
        _, events, _, _, _ = m.excellent(
            mode, value, code, a, b, category, id, hero, 0, 0, base
        )
        r = lib.mu_social_excellent_display(
            code, a, b, category, mode, id, value, 1, hero, base, C.byref(d)
        )
        if mode > 3:
            check("excellent_display", False, bool(r))
        else:
            values = events[0]["values"]
            native = []
            if d.kind in (3, 4):
                native.append("L%x" % d.label)
            if d.kind in (1, 3):
                native.append(d.integer)
            if d.kind in (2, 4):
                native.append(fp(d.real))
                values = [fp(x) if isinstance(x, float) else x for x in values]
            check("excellent_display", values, native)
        typ = k % 7
        input = rng.choice([0.0, 1.0, -3.0, 10.0, 12345.6])
        fields = (120003, 220005, 320007, 420009)
        cl = k % 2 * 32
        value = m.socketvalue(typ, input, cl, fields)
        r = lib.mu_social_socket_display(
            typ, input, 1, fields[0 if cl else 2], 1, fields[1 if cl else 3], C.byref(d)
        )
        _, events, _ = m.socket(typ, input, cl, fields)
        observed = [fp(value)]
        native = [fp(d.real) if r else fp(0.0)]
        if 1 <= typ <= 5:
            observed.append(
                fp(events[0]["values"][0]) if typ == 3 else events[0]["values"][0]
            )
            native.append(fp(d.real) if typ == 3 else d.integer)
        check("socket_display", observed, native)
        w = Wire()
        w.code = code
        w.ancient = rng.randrange(256)
        w.flags = rng.randrange(8)
        w.harmony = rng.randrange(256)
        w.sockets[:] = [255] * 5
        c = Context()
        c.kind_a = a if k % 2 else rng.choice([8, 12, 19, 20, 25, 26, 28, 34])
        c.kind_b = b
        c.grade = k % 9
        c.normalized_slot = k % 17
        c.slot_flags[:] = [k % 2, 0, 0, 0]
        converted = Decoded()
        lib.mu_social_item_convert(C.byref(w), C.byref(c), C.byref(converted))
        case = dict(
            code=code,
            a=c.kind_a,
            b=b,
            g=c.grade,
            h=converted.harmony_kind,
            ancient=converted.ancient,
            period=converted.period,
            slot=c.normalized_slot,
            flags=list(c.slot_flags),
        )
        observed = m.harmony(case)
        native = lib.mu_social_harmony_visible(C.byref(w), C.byref(c))
        check("harmony_gate", observed, native)
    return reports
