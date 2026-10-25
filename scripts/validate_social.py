#!/usr/bin/env python3
"""Compare bounded social instructions with reconstructed/social, private inputs only.

party_fields, party_bars and friends run named instruction slices. The party
bars count loop/name matching are covered by synthetic tests, not Unicorn here.
Other families run whole routines. STL handles, GFx, strings, block/options and display boundaries are
explicit models. No packet encryption, sockets, login or protection routines.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import client_ui_machine as cm
import validate_names as vn
import validate_map as vm
import pins

I = C.c_int32


class Member(C.Structure):
    _fields_ = (
        [("name", C.c_char * 11)]
        + [
            (s, I)
            for s in (
                "slot",
                "number",
                "server",
                "world",
                "x",
                "y",
                "hp",
                "mp",
                "max_hp",
                "max_mp",
                "hp_percent",
                "mp_percent",
            )
        ]
        + [(s, C.c_uint8) for s in ("control", "special", "in_view")]
    )


class Party(C.Structure):
    _fields_ = [("count", I), ("members", Member * 5)]


class Marker(C.Structure):
    _fields_ = [("key", I), ("x", C.c_float), ("y", C.c_float), ("name", C.c_char * 11)]


class Item(C.Structure):
    _fields_ = [("present", C.c_uint8), ("bytes", C.c_uint8 * 15)]


class Trade(C.Structure):
    _fields_ = [
        (s, I)
        for s in (
            "open",
            "result",
            "notice",
            "zen0",
            "zen1",
            "proposed",
            "level",
            "guild",
        )
    ] + [
        ("ok", C.c_uint8 * 2),
        ("warned", C.c_uint8),
        ("wait", I),
        ("name", C.c_char * 11),
        ("items", (Item * 32) * 2),
    ]


class Friend(C.Structure):
    _fields_ = [("name", C.c_char * 11), ("server", I)]


class Friends(C.Structure):
    _fields_ = [("count", I), ("list", Friend * 50)]


class Machine(cm.Machine):
    def cstr(self, p):
        out = bytearray()
        for i in range(1024):
            b = self.read(p + i, 1)
            if b == b"\0":
                return bytes(out)
            out += b
        raise cm.CaseError("unterminated case string")

    def slice(self, a, end, setup):
        self.uc.reg_write(cm.UC_X86_REG_EBP, setup)
        self.uc.reg_write(cm.UC_X86_REG_ESP, setup - 0x2000)
        self.uc.emu_start(a, end, count=100000)
        if self.errors or self.uc.reg_read(cm.UC_X86_REG_EIP) != end:
            raise cm.CaseError(str(self.errors))


def ptr(m):
    return m.uc.reg_read(cm.UC_X86_REG_ECX)


def setstubs(m):
    m.stub(0x95F128, lambda q: q.u32(ptr(q)))
    m.stub(0x95EB67, lambda q: 0)

    def copy(q):
        dst, src, n = q.args(3)
        q.write(dst, q.read(src, n))
        return dst

    m.stub(0x19898A0, copy)
    m.stub(0x194C200, copy)

    def zero(q):
        dst, v, n = q.args(3)
        q.write(dst, bytes([v & 255]) * n)
        return dst

    m.stub(0x194CD00, zero)


def native(path):
    l = C.CDLL(str(path))
    l.mu_social_party_state.argtypes = [I, I]
    l.mu_social_party_request.argtypes = [C.c_char_p, C.c_size_t, I, C.POINTER(I)]
    l.mu_social_party_member.argtypes = [C.c_char_p, I, C.POINTER(Member)]
    l.mu_social_party_receive.argtypes = [C.POINTER(Party), C.c_char_p, C.c_size_t]
    l.mu_social_party_markers.argtypes = [
        C.POINTER(Party),
        C.c_char_p,
        I,
        I,
        C.POINTER(Marker),
    ]
    l.mu_social_trade_receive.argtypes = [C.POINTER(Trade), C.c_char_p, C.c_size_t]
    l.mu_social_trade_result.argtypes = [C.POINTER(Trade), C.c_uint8]
    l.mu_social_trade_lock.argtypes = [C.POINTER(Trade), C.c_uint8]
    l.mu_social_whisper.argtypes = [
        C.c_char_p,
        C.c_size_t,
        I,
        I,
        C.c_void_p,
        C.c_void_p,
    ]
    l.mu_social_friends_receive.argtypes = [C.POINTER(Friends), C.c_char_p, C.c_size_t]
    return l


def run(m, l, rng, n):
    report = {}

    def check(f, a, b):
        v = report.setdefault(f, {"cases": 0, "mismatches": 0})
        v["cases"] += 1
        if a != b:
            v["mismatches"] += 1
            if "first" not in v:
                v["first"] = {"client": a, "native": b}

    for k in range(n):
        m.reset()
        setstubs(m)
        # Whole party request receive, the real key assembly and blocked/prompt branch.
        payload = bytes([0xC1, 5, 0x40, rng.randrange(256), rng.randrange(256)])
        packet = m.alloc(5)
        m.write(packet, payload)
        window = m.alloc(0x100, True)
        mgr = m.alloc(0x100, True)
        m.put32(mgr + 0xD8, window)
        blocked = k & 1
        events = []
        m.stub(0x95C595, lambda z: z.put32(z.args(1)[0], window) or z.args(1)[0], 4)
        m.stub(0x9617C6, lambda z: 0)
        m.stub(0x95F659, lambda z: window)
        m.stub(0x95BD05, lambda z: blocked)
        m.stub(0xAC3BF7, lambda z: mgr)
        m.stub(0xC0A9C8, lambda z: events.append("prompt") or 0)
        m.call(0x1270D06, [packet])
        key = I()
        show = l.mu_social_party_request(payload, len(payload), blocked, C.byref(key))
        check(
            "party_request",
            [m.u32(window + 0x3C), events],
            [key.value, ["prompt"] if show else []],
        )
        m.reset()
        setstubs(m)
        # Exact field/math block of the 44-byte party record, no UI decisions stubbed.
        r = bytearray(rng.randbytes(44))
        vals = [rng.randrange(-2000000, 2000000) for _ in range(4)]
        for off, v in zip((20, 24, 32, 36), vals):
            struct.pack_into("<i", r, off, v)
        slot = rng.randrange(5)
        rec = m.alloc(44, True)
        m.write(rec, r)
        out = m.alloc(124, True)
        h = m.alloc(8, True)
        m.put32(h, out)
        bp = cm.STACK_BASE + cm.STACK_SIZE - 0x1000
        m.put32(bp - 0x14, out)
        m.put32(bp - 0x1C, rec)
        m.put32(bp - 0x24, slot)
        # The smart-handle local contains the raw member pointer.
        m.slice(0xC77C65, 0xC77E23, bp)
        got = [
            vn.s32(m.u32(out + x))
            for x in (0, 4, 8, 0x10, 0x30, 0x34, 0x20, 0x24, 0x28, 0x2C, 0x18, 0x1C)
        ]
        got += list(m.read(out + 0x16, 1) + m.read(out + 0x14, 1))
        v = Member()
        l.mu_social_party_member(bytes(r), slot, C.byref(v))
        want = [
            getattr(v, s)
            for s in (
                "slot",
                "number",
                "server",
                "world",
                "x",
                "y",
                "hp",
                "mp",
                "max_hp",
                "max_mp",
                "hp_percent",
                "mp_percent",
                "control",
                "special",
            )
        ]
        check("party_fields", got, want)
        # Whole state routine, shared_ptr acquire/release are the only models.
        m.reset()
        setstubs(m)
        q = m.alloc(124, True)
        server = rng.choice([0, 1, 200, 201, 204, 65535])
        view = rng.randrange(3)
        m.put32(q + 8, server)
        m.write(q + 0x15, bytes([view]))
        got = m.call(0xC7A7A2, [q, 0])
        check("party_state", got, l.mu_social_party_state(server, view))
        # Exact byte clamp block from the full HP/MP receive loop.
        m.reset()
        bp = cm.STACK_BASE + cm.STACK_SIZE - 0x1000
        q = m.alloc(13, True)
        hp, mp = rng.randrange(256), rng.randrange(256)
        m.write(q, bytes([hp, mp]) + b"Aeris\0\0\0\0\0\0")
        m.put32(bp - 0x10, q)
        m.slice(0xC789E2, 0xC78A80, bp)
        got = [m.u32(bp - 0x3C), m.u32(bp - 0x40)]
        p = Party()
        p.count = 1
        p.members[0].name = b"Aeris"
        b = bytes([0xC1, 17, 0x44, 1, hp, mp]) + b"Aeris\0\0\0\0\0\0"
        l.mu_social_party_receive(C.byref(p), b, len(b))
        check("party_bars", got, [p.members[0].hp_percent, p.members[0].mp_percent])
        # Whole partner-lock method. Record game state setters and warning, sound opaque.
        m.reset()
        setstubs(m)
        m.stubs.pop(0xC45B3E, None)
        q = m.alloc(0x100, True)
        state = rng.randrange(4)
        mine, other, warn = [rng.randrange(2) for _ in range(3)]
        wait = rng.randrange(50)
        m.write(q + 0xE0, bytes([warn]))
        m.put32(q + 0xDC, wait)
        got = [mine, other, warn, wait]
        m.stub(0xC449BF, lambda z: got.__setitem__(0, z.args(1)[0]) or 0, 4)
        m.stub(0xC44A78, lambda z: got.__setitem__(1, z.args(1)[0]) or 0, 4)
        for a in (0xAC3BF7, 0x95F5D7):
            m.stub(a, lambda z: q)
        m.stub(0x95F027, lambda z: 0, 4)
        m.stub(0xB3967C, lambda z: 0, 28)
        m.stub(0xA6AC96, lambda z: 0)
        m.call(0xC45B3E, [state], q)
        got[2] = m.read(q + 0xE0, 1)[0]
        got[3] = m.u32(q + 0xDC)
        t = Trade()
        t.ok[0] = mine
        t.ok[1] = other
        t.warned = warn
        t.wait = wait
        l.mu_social_trade_lock(C.byref(t), state)
        check("trade_lock", got, [t.ok[0], t.ok[1], t.warned, t.wait])
        # Full receive wrappers: parse offsets and dispatch, with the trade manager as boundary.
        m.reset()
        setstubs(m)
        mgr = m.alloc(0x300, True)
        q = m.alloc(0x100, True)
        m.put32(mgr + 0xE4, q)
        m.stub(0xAC3BF7, lambda z: mgr)
        data = bytes(rng.randrange(256) for _ in range(32))
        b = m.alloc(32, True)
        m.write(b, data)
        events = []
        for a, arity in (
            (0xC4599F, 1),
            (0xC459E8, 2),
            (0xC45F72, 1),
            (0xC45A19, 1),
            (0xC45B3E, 1),
        ):

            def capture(z, a=a, arity=arity):
                x = list(z.args(arity))
                events.append(
                    [a, x[0], z.read(x[1], 15).hex()] if arity == 2 else [a, x[0]]
                )
                return 0

            m.stub(a, capture, arity * 4)
        for a, opcode in (
            (0x1282BB0, 0x38),
            (0x1282B76, 0x39),
            (0x1282B45, 0x3B),
            (0x1282AE4, 0x73),
            (0x1282BE3, 0x3E),
        ):
            payload = bytearray(data)
            payload[0] = 0xC1
            payload[2] = opcode
            payload[3] = (
                rng.randrange(32) if opcode in (0x38, 0x39) else rng.randrange(2)
            )
            m.write(b, payload)
            events.clear()
            m.call(a, [b])
            t = Trade()
            t.proposed = 12345
            t.items[1][payload[3] % 32].present = 1
            l.mu_social_trade_receive(C.byref(t), bytes(payload), len(payload))
            if opcode == 0x38:
                want = (
                    [0xC4599F, payload[3]] if not t.items[1][payload[3]].present else []
                )
            elif opcode == 0x39:
                want = [0xC459E8, payload[3], bytes(t.items[1][payload[3]].bytes).hex()]
            elif opcode == 0x3B:
                want = [0xC45F72, t.zen1 & 0xFFFFFFFF]
            elif opcode == 0x73:
                want = [0xC45A19, int(t.zen0 == 12345)]
            else:
                want = [0xC45B3E, t.ok[1]]
            check("trade_packets", events, [want])
        # Whole trade result method, notice texts and close callback recorded.
        m.reset()
        setstubs(m)
        q = m.alloc(0x100, True)
        vt = m.alloc(0x100, True)
        m.put32(q, vt)
        events = []
        close = m._new_stub()
        m.stub(close, lambda z: events.append("close") or 0)
        m.put32(vt + 0x44, close)
        for a in (0xAC3BF7, 0x95FB15, 0x95F136, 0x95F5D7):
            m.stub(a, lambda z: q)
        for a in (0xC08654, 0xC081AA, 0xAAE6F9):
            m.stub(a, lambda z: 0)
        m.stub(0x95F027, lambda z: events.append(z.args(1)[0]) or 0, 4)
        m.stub(0x94997E, lambda z: ptr(z), 4)
        m.stub(0x8E83A0, lambda z: 0)
        m.stub(0x95F4EC, lambda z: 0, 4)
        state = k % 10
        m.call(0xC45C09, [state], q)
        t = Trade()
        t.open = 1
        l.mu_social_trade_result(C.byref(t), state)
        check(
            "trade_result",
            events,
            ([t.notice] if t.notice else []) + (["close"] if not t.open else []),
        )
        # Friend list's exact decode loop (UI/manager insertion is the recording boundary).
        m.reset()
        setstubs(m)
        bp = cm.STACK_BASE + cm.STACK_SIZE - 0x1000
        count = rng.randrange(8)
        data = bytearray(7 + 11 * count)
        data[6] = count
        for i in range(count):
            data[7 + i * 11 : 17 + i * 11] = (
                (f"Friend{i:04}"[:10]).encode().ljust(10, b"X")
            )
            data[17 + i * 11] = rng.randrange(256)
        b = m.alloc(len(data), True)
        m.write(b, data)
        m.put32(bp + 8, b)
        mgr = m.alloc(0x300, True)
        m.put32(mgr + 0x230, mgr)
        m.stub(0xAC3BF7, lambda z: mgr)
        events = []
        m.stub(
            0xB70604,
            lambda z: events.append([m.cstr(z.args(3)[0]).decode(), z.args(3)[2]]) or 0,
            12,
        )
        m.slice(0x124123E, 0x12412C8, bp)
        f = Friends()
        l.mu_social_friends_receive(C.byref(f), bytes(data), len(data))
        check(
            "friends",
            events,
            [[x.name.decode(), x.server] for x in list(f.list)[: f.count]],
        )
        # Whole whisper receiver: block/options, strings and AddChatInfo as explicit models.
        m.reset()
        setstubs(m)
        q = m.alloc(0x200, True)
        b = m.alloc(73, True)
        payload = (
            b"\xc1\x49\x02"
            + b"Aeris\0\0\0\0\0"
            + b"hello private channel".ljust(60, b"\0")
        )
        m.write(b, payload)
        ph = m.alloc(4, True)
        m.put32(ph, b)
        bypass, blocked = rng.randrange(2), rng.randrange(2)
        for a in (0x95F75D, 0xAC3BF7, 0xBBFE04):
            m.stub(a, lambda z: q)
        m.stub(0x95FB99, lambda z: bypass)
        m.stub(0xB30FFE, lambda z: blocked, 4)
        for a in (0x98BB60,):
            m.stub(a, lambda z: m.put32(z.args(1)[0], q) or z.args(1)[0], 4)
        m.stub(0x95F160, lambda z: q)
        m.stub(0x95F602, lambda z: q)
        m.stub(0x98C49E, lambda z: 0)
        m.stub(0xA6AC96, lambda z: 0)
        m.stub(0x94997E, lambda z: m.put32(ptr(z), z.args(1)[0]) or ptr(z), 4)
        m.stub(0x8E83A0, lambda z: 0)
        events = []
        m.stub(
            0xC617A2,
            lambda z: events.append(
                [
                    z.args(3)[0],
                    m.cstr(m.u32(z.args(3)[1])).decode(),
                    m.cstr(m.u32(z.args(3)[2])).decode(),
                ]
            )
            or 0,
            12,
        )
        m.call(0xC609B5, [ph], q)
        name = C.create_string_buffer(11)
        text = C.create_string_buffer(61)
        ok = l.mu_social_whisper(payload, len(payload), bypass, blocked, name, text)
        check(
            "whisper",
            events,
            [[2, name.value.decode(), text.value.decode()]] if ok else [],
        )
    return report


def run_markers(m, l, rng, n):
    vm.install_common(m)
    result = {"cases": 0, "mismatches": 0}
    for k in range(n):
        m.reset()
        vm.W.reset()
        party = Party()
        party.count = rng.randrange(6)
        server = rng.randrange(3)
        world = rng.randrange(3)
        win = m.alloc(0x100, True)
        mgr = m.alloc(0x100, True)
        hero = m.alloc(11, True)
        m.write(hero, b"Hero\0" + bytes(6))
        m.put32(0xA39D754, win)
        m.put32(0x1CF15FC, world)
        nodes = []
        for i in range(party.count):
            q = party.members[i]
            q.name = b"Hero" if i == 0 else f"Member{i}".encode()
            q.slot = i
            q.server = rng.randrange(3)
            q.world = rng.randrange(3)
            q.x = rng.randrange(256)
            q.y = rng.randrange(256)
            raw = m.alloc(124, True)
            m.put32(raw, i)
            m.put32(raw + 8, q.server)
            m.put32(raw + 16, q.world)
            m.put32(raw + 48, q.x)
            m.put32(raw + 52, q.y)
            vm.write_std_string(m, raw + 60, q.name)
            node = m.alloc(32, True)
            m.put32(node + 24, raw)
            nodes.append(node)

        def begin(z):
            out = z.args(1)[0]
            z.put32(out, nodes[0] if nodes else 0)
            return out

        def end(z):
            out = z.args(1)[0]
            z.put32(out, 0)
            return out

        def nxt(z):
            out = z.args(2)[0]
            cur = z.u32(ptr(z))
            i = nodes.index(cur)
            z.put32(out, cur)
            z.put32(ptr(z), nodes[i + 1] if i + 1 < len(nodes) else 0)
            return out

        def cp(z):
            out, src = z.args(1)[0], z.args(1)[0]
            z.write(ptr(z), z.read(src, 8))
            return ptr(z)

        m.stub(0xA05D02, lambda z: 1)
        m.stub(0x95C595, lambda z: z.put32(z.args(1)[0], mgr) or z.args(1)[0], 4)
        m.stub(0x95F16E, lambda z: mgr)
        m.stub(0x95F9BE, lambda z: mgr)
        m.stub(0x95EBBB, lambda z: 0)
        m.stub(0x9610F8, begin, 4)
        m.stub(0x9612FE, end, 4)
        m.stub(0x95F1D6, nxt, 8)
        m.stub(0x95EEE4, lambda z: int(z.u32(ptr(z)) != z.u32(z.args(1)[0])), 4)
        m.stub(0x95F0E0, lambda z: z.u32(ptr(z)))
        m.stub(0x95E3BF, cp, 4)
        m.stub(0x95F128, lambda z: z.u32(ptr(z)))
        m.stub(0x95EB67, lambda z: 0)
        m.stub(0x129DEAA, lambda z: hero)
        m.stub(
            0x90EDB0,
            lambda z: int(vm.std_string_at(z, z.args(2)[0]) == z.cstr(z.args(2)[1])),
        )
        m.stub(0x1072152, lambda z: mgr)
        m.stub(0x10729D2, lambda z: server)
        m.stub(0x8E7940, lambda z: ptr(z) if z.u32(ptr(z) + 20) < 16 else z.u32(ptr(z)))

        def append(z):
            value = z.args(1)[0]
            vm.W.values[z.u32(ptr(z))][1][len(vm.W.values[z.u32(ptr(z))][1])] = (
                vm.render(z.u32(value))
            )
            return 0

        m.stub(0xAE495F, append, 4)
        m.call(0xC6B2CC, [], win)
        got = vm.W.log[-1][2]
        out = (Marker * 5)()
        count = l.mu_social_party_markers(C.byref(party), b"Hero", server, world, out)
        want = [
            (
                ("type", ("i", 10)),
                ("key", ("i", x.key)),
                ("text", ("s", x.name.decode())),
                ("x", ("f", cm.fbits(x.x))),
                ("y", ("f", cm.fbits(x.y))),
            )
            for x in list(out)[:count]
        ]
        # vm.render returns object member lists and arrays in insertion order.
        want = [list(x) for x in want]
        result["cases"] += 1
        if json.loads(json.dumps(got)) != json.loads(json.dumps(want)):
            result["mismatches"] += 1
            if "first" not in result:
                result["first"] = {"client": got, "native": want}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--text", default=pins.TEXT.default_str())
    p.add_argument("--data", default=pins.DATA.default_str())
    p.add_argument("--cases", type=int, default=500)
    p.add_argument("--mutations", action="store_true")
    p.add_argument("--output")
    a = p.parse_args()
    text, data = pins.TEXT.read(a.text), pins.DATA.read(a.data)
    m = Machine(text, data)
    for lo, hi in (
        (0xC77C65, 0xC77E23),
        (0x1270D06, 0x1270D9E),
        (0xC7A7A2, 0xC7A7FA),
        (0xC789E2, 0xC78A80),
        (0xC45B3E, 0xC45C07),
        (0xC45C09, 0xC45EFB),
        (0x1282AE4, 0x1282C16),
        (0x124123E, 0x12412C8),
        (0xC609B5, 0xC60B25),
        (0xC6B2CC, 0xC6B550),
        (0xC6BA5C, 0xC6BAA6),
    ):
        m.allow((lo, hi))
    lib = ROOT / "reconstructed/social/libsocial.dylib"
    subprocess.run(["make", "-C", str(lib.parent)], check=True, capture_output=True)
    result = {
        "text_sha256": vn.TEXT_SHA256,
        "data_sha256": vn.DATA_SHA256,
        "seed": 1,
        "families": run(m, native(lib), random.Random(1), a.cases),
    }
    result["families"]["markers"] = run_markers(
        m, native(lib), random.Random(2), a.cases
    )
    result["cases"] = sum(x["cases"] for x in result["families"].values())
    result["mismatches"] = sum(x["mismatches"] for x in result["families"].values())
    if a.mutations:
        result["mutations"] = {}
        with tempfile.TemporaryDirectory() as tmp:
            for mutation, family in enumerate(
                (
                    "party_state",
                    "party_bars",
                    "markers",
                    "trade_lock",
                    "whisper",
                    "party_fields",
                    "trade_packets",
                    "trade_result",
                    "friends",
                    "party_request",
                ),
                1,
            ):
                if family == "markers":
                    rr = None
                dst = Path(tmp) / f"{mutation}.dylib"
                subprocess.run(
                    [
                        "clang",
                        "-shared",
                        "-fPIC",
                        "-O2",
                        "-ffp-contract=off",
                        f"-DMU_SOCIAL_MUTATION={mutation}",
                        str(lib.parent / "social.c"),
                        "-o",
                        str(dst),
                    ],
                    check=True,
                )
                rr = (
                    run_markers(m, native(dst), random.Random(2), 60)
                    if family == "markers"
                    else run(m, native(dst), random.Random(1), 30)[family]
                )
                result["mutations"][family] = rr["mismatches"] > 0
        if not all(result["mutations"].values()):
            result["mismatches"] += 1
    if a.output:
        Path(a.output).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return bool(result["mismatches"])


if __name__ == "__main__":
    sys.exit(main())
