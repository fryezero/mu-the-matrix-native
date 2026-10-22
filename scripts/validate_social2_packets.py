"""Original social instructions versus production C. Imported by validate_social2.

Packet builders are compared before transport transformation. The original
length placeholder is normalized to the observed builder count, explicitly
modelling header finalization; no final-send body is entered.
"""

import ctypes as C
import random
import struct
import client_ui_machine as cm

I = C.c_int32
U = C.c_uint32


class Packet(C.Structure):
    _fields_ = [
        ("size", I),
        ("channel", I),
        ("send0", I),
        ("send1", I),
        ("data", C.c_uint8 * 1100),
    ]


class User(C.Structure):
    _fields_ = [("name", C.c_char * 11), ("serial", C.c_uint8), ("server", C.c_uint8)]


class Event(C.Structure):
    _fields_ = [("event", I), ("user", User)]


class Message(C.Structure):
    _fields_ = [("serial", C.c_uint8), ("text", C.c_char * 101)]


class Letter(C.Structure):
    _fields_ = [
        ("id", U),
        ("sender", C.c_char * 11),
        ("title", C.c_char * 33),
        ("date", C.c_char * 11),
        ("time", C.c_char * 9),
        ("read", I),
        ("arrived", I),
    ]


class Body(C.Structure):
    _fields_ = [("id", U), ("text", C.c_char * 1001)]


def bind(lib):
    signatures = {
        "party_invite": [C.POINTER(Packet), C.c_uint16, I, I],
        "party_answer": [C.POINTER(Packet), C.c_uint16, C.c_uint8],
        "party_popup": [I, I, C.POINTER(I)],
        "party_remove": [C.POINTER(Packet), C.c_uint8, C.c_char_p, I, I],
        "party_permission": [I, I, I, I, I, I, I, C.POINTER(I)],
        "party_autoaccept": [I, I, I, I, I, I, I],
        "party_notice": [C.c_uint8],
        "room_text": [C.c_char_p, C.c_size_t, C.c_char_p, C.POINTER(Message)],
        "room_event_read": [C.c_char_p, C.c_size_t, C.POINTER(Event)],
        "mail_header": [C.c_char_p, C.c_size_t, C.POINTER(Letter)],
        "mail_body": [C.c_char_p, C.c_size_t, C.POINTER(Body)],
        "mail_write": [
            C.POINTER(Packet),
            U,
            C.c_char_p,
            C.c_char_p,
            C.c_char_p,
            C.c_size_t,
        ],
        "room_send": [C.POINTER(Packet), C.c_char_p, C.c_size_t, C.c_char_p],
    }
    for name, args in signatures.items():
        getattr(lib, "mu_social_" + name).argtypes = args


def ptr(m):
    return m.uc.reg_read(cm.UC_X86_REG_ECX)


def cstr(m, p, n=2048):
    return m.read(p, n).split(b"\0", 1)[0]


def ssread(m, p):
    return m.read(m.u32(p) if m.u32(p + 20) >= 16 else p, m.u32(p + 16))


def sswrite(m, p, b):
    m.write(p, bytes(24))
    if len(b) < 16:
        m.write(p, b + b"\0")
        cap = 15
    else:
        q = m.alloc(len(b) + 1, True)
        m.write(q, b + b"\0")
        m.put32(p, q)
        cap = len(b)
    m.put32(p + 16, len(b))
    m.put32(p + 20, cap)
    return p


def reset(m):
    m.reset()
    m.allowed = []
    for a in [a for a, v in m.stubs.items() if v[0] == "client"]:
        del m.stubs[a]

    def copy(q):
        d, s, n = q.args(3)
        q.write(d, q.read(s, n))
        return d

    def zero(q):
        d, v, n = q.args(3)
        q.write(d, bytes([v & 255]) * n)
        return d

    for a in (0x19898A0, 0x194C200):
        m.stub(a, copy)
    m.stub(0x194CD00, zero)
    m.stub(0x8E6D00, lambda q: sswrite(q, ptr(q), b""))
    m.stub(0x94997E, lambda q: sswrite(q, ptr(q), cstr(q, q.args(1)[0])), 4)
    m.stub(0x8E83A0, lambda q: 0)
    m.stub(0x94F183, lambda q: 0)
    m.stub(0x8E80E0, lambda q: sswrite(q, ptr(q), ssread(q, q.args(1)[0])), 4)
    m.stub(0x94AF7D, lambda q: sswrite(q, ptr(q), ssread(q, q.args(1)[0])), 4)
    m.allow((0x8E7940, 0x8E794C), (0x950D4D, 0x950D5C), (0x191C5A0, 0x191C5CB))


def ui(m):
    host = m.alloc(0x300, True)
    win = m.alloc(0x300, True)
    m.put32(host + 0x230, win)
    m.put32(host + 0x234, win)
    m.put32(0x1D22C6C, win)
    m.stub(0xAC3BF7, lambda q: host)
    m.stub(0x95F635, lambda q: win)
    return host, win


def handle(m, win):
    def get(q):
        out = q.args(1)[0]
        q.put32(out, win)
        q.put32(out + 4, 0)
        return out

    m.stub(0x95C595, get, 4)
    m.stub(0x9617C6, lambda q: 0)
    m.stub(0x95EBBB, lambda q: 0)


def packet_native(p):
    return [p.size, list(bytes(p.data[: p.size])), [p.send0, p.send1]]


def packet_transport(m, events):
    m.allow((0xD51B91, 0xD51D10), (0xD52133, 0xD52159), (0x95C204, 0x95C222))
    m.stub(0xD52055, lambda q: 0, 12)

    def send(q):
        address = ptr(q)
        n = struct.unpack("<H", q.read(address, 2))[0]
        b = bytearray(q.read(address + 2, n))
        # Original generic builder leaves 1. Final transport is an opaque
        # boundary; normalize only this header field using observed count.
        if b[0] == 0xC1:
            b[1] = n & 255
        elif b[0] == 0xC2:
            b[1:3] = bytes([n >> 8, n & 255])
        events.append([n, list(b), q.args(2)])
        return 1

    m.stub(0xD51D4F, send, 8)


def append_transport(m, events):
    def append(q):
        p, n, flag = q.args(3)
        n &= 65535
        events.append([n, flag, list(q.read(p, n))])
        return 0

    m.stub(0xD51C9B, append, 12)
    m.stub(0xD51D4F, lambda q: events.append(["send", *q.args(2)]) or 0, 8)
    m.stub(0xD52133, lambda q: q.write(ptr(q), bytes(0x145C)) or ptr(q))
    for a in (0xD51B91, 0xD51BA6, 0xD51BAF, 0xD51D10, 0x95C204, 0x9EB249, 0x9C06DD):
        m.allow((a, cm.function_extent(m.text, a)))


def run(m, lib, n):
    bind(lib)
    rng = random.Random(22)
    report = {}

    def check(f, a, b):
        r = report.setdefault(f, {"cases": 0, "mismatches": 0})
        r["cases"] += 1
        if a != b:
            r["mismatches"] += 1
            r.setdefault("first", {"client": a, "native": b})

    for k in range(n):
        reset(m)
        events = []
        packet_transport(m, events)
        key = rng.randrange(65536)
        exists = k % 5 != 0
        enabled = k % 4
        obj = m.alloc(0x100, True)
        m.stub(0x137C724, lambda q: 9)
        m.stub(0x95F6DB, lambda q: 0)
        m.stub(0x9A13F4, lambda q: obj if exists else 0, 4)
        m.stub(0x129DEAA, lambda q: 0x1234)
        m.write(0xBDC5EB8, bytes([enabled]))
        m.stub(0x95F027, lambda q: 0x1234, 4)
        m.stub(0x11753C3, lambda q: 0x1234, 4)
        m.stub(0x8E7F90, lambda q: 0x1234)
        m.stub(0x9619DD, lambda q: 0)
        m.stub(0x95F4EC, lambda q: 0, 4)
        m.stub(0x95F547, lambda q: 0, 4)
        m.put32(0x1D22C6C, obj)
        m.allow((0x16B6771, 0x16B68D5))
        m.call(0x16B6771, [key], limit=100000)
        p = Packet()
        ok = lib.mu_social_party_invite(C.byref(p), key, exists, enabled)
        check("party_invite", events, [packet_native(p)] if ok else [])
        reset(m)
        events = []
        packet_transport(m, events)
        win = m.alloc(0x80, True)
        m.put32(win + 0x3C, key)
        handle(m, win)
        reply = rng.randrange(256)
        m.allow((0x9602CC, 0x9603A5), (0x95F16E, 0x95F17C), (0x95FB6D, 0x95FB7C))
        m.call(0x9602CC, [reply], limit=100000)
        lib.mu_social_party_answer(C.byref(p), key, reply)
        check("party_answer", events, [packet_native(p)])
        reset(m)
        events = []
        popup = [0, 12, 13, 14, 55][k % 5]
        result = [-1, 0, 1, 2][k % 4]
        m.stub(0x9602CC, lambda q: events.append(q.args(1)[0]) or 0)
        m.allow((0xC0A5C0, 0xC0A5F8))
        m.call(0xC0A5C0, [popup, result, 0, 0], ecx=m.alloc(16, True))
        answer = I()
        ok = lib.mu_social_party_popup(popup, result, C.byref(answer))
        check("party_popup", events, [answer.value] if ok else [])
        reset(m)
        events = []
        packet_transport(m, events)
        win = m.alloc(0x100, True)
        rec = m.alloc(0x80, True)
        slot = rng.randrange(256)
        found = k % 5 != 0
        empty = k % 7 == 0
        m.write(rec + 4, bytes([slot]))
        node = m.alloc(0x30, True)
        m.put32(node + 0x18, rec)

        def find(q):
            o = q.args(2)[0]
            q.put32(o, node if found else 0)
            return o

        def end(q):
            o = q.args(1)[0]
            q.put32(o, 0)
            return o

        m.stub(0xC7FC5E, find, 8)
        m.stub(0xC7FB90, end, 4)
        m.stub(0x95EE27, lambda q: int(q.u32(ptr(q)) == q.u32(q.args(1)[0])), 4)
        m.stub(0x95F0E0, lambda q: q.u32(ptr(q)))
        m.stub(
            0x95E3BF, lambda q: q.write(ptr(q), q.read(q.args(1)[0], 8)) or ptr(q), 4
        )
        m.stub(0x95F128, lambda q: q.u32(ptr(q)))
        m.stub(0x95EB67, lambda q: 0)
        m.stub(0x8E53E0, lambda q: int(empty))
        name = m.alloc(16, True)
        m.write(name, b"0123456789TAIL!!\0")
        m.stub(0x8E7940, lambda q: name)
        m.stub(0x95FBDC, lambda q: 0)
        m.stub(0x970914, lambda q: 0)
        m.allow((0xC79B05, 0xC79D17))
        m.call(0xC79B05, ecx=win, limit=100000)
        ok = lib.mu_social_party_remove(
            C.byref(p), slot, b"0123456789TAIL", found, empty
        )
        check("party_remove", events, [packet_native(p)] if ok else [])
        reset(m)
        ui(m)
        events = []
        m.write(0x6FC9BDC, b"\0")
        value = [*range(18), 127, 255][k % 20]
        b = bytes([0xC1, 5, 0x41, value, 0x99])
        packet = m.alloc(5, True)
        m.write(packet, b)
        m.stub(0x11753C3, lambda q: events.append(q.args(1)[0]) or 0x1234, 4)
        m.stub(0x8E7F90, lambda q: 0x1234)
        m.stub(0x94997E, lambda q: ptr(q), 4)
        m.stub(0x95F547, lambda q: 0, 4)
        m.stub(0x95F4EC, lambda q: 0, 4)
        m.allow((0x127373E, 0x1273D07))
        m.call(0x127373E, [packet], limit=100000)
        notice = lib.mu_social_party_notice(value)
        check("party_result", events, [notice] if notice else [])
    for k in range(n):
        reset(m)
        events = []
        calls = []
        blocked, worldblocked, hasparty, leader = [rng.randrange(3) for _ in range(4)]
        targetpk, heropk = [rng.randrange(7) for _ in range(2)]
        exists = k % 9 != 0
        hero = m.alloc(0x80, True)
        target = m.alloc(0x80, True)
        party = m.alloc(0x100, True)
        m.put32(0xA39D754, hero)
        m.put32(0x1CF15FC, 9)
        m.write(target + 0x1F, bytes([targetpk]))
        m.write(hero + 0x1F, bytes([heropk]))
        m.write(target + 0x3E, b"\x34\x92")
        handle(m, party)
        m.stub(0x9DACB8, lambda q: blocked)
        m.stub(0xC7DFCC, lambda q: party)
        m.stub(0x9D3E63, lambda q: worldblocked, 4)
        m.stub(0x95FC81, lambda q: hasparty)
        m.stub(0x129DEAA, lambda q: party)
        m.stub(0xC79662, lambda q: leader, 4)
        m.stub(0x16B6771, lambda q: calls.append(q.args(1)[0]) or 0)
        m.stub(0x95F027, lambda q: events.append(q.args(1)[0]) or 0x1234, 4)
        m.stub(0x11753C3, lambda q: events.append(q.args(1)[0]) or 0x1234, 4)
        m.stub(0x94997E, lambda q: ptr(q), 4)
        m.stub(0x8E7F90, lambda q: 0x1234)
        m.stub(0x95F4EC, lambda q: 0, 4)
        m.stub(0x95F547, lambda q: 0, 4)
        m.put32(0x1D22C6C, party)
        m.allow((0x16A6775, 0x16A6A91), (0x95FC71, 0x95FC81))
        m.call(0x16A6775, [target if exists else 0], limit=100000)
        notice = I()
        ok = lib.mu_social_party_permission(
            exists,
            blocked,
            worldblocked,
            hasparty,
            leader,
            targetpk,
            heropk,
            C.byref(notice),
        )
        check(
            "party_permission",
            [calls, events],
            [[0xFFFF9234] if ok else [], [notice.value] if notice.value else []],
        )
        reset(m)
        win = m.alloc(0x80, True)
        handle(m, win)
        pref = m.alloc(0x460, True)
        hero = m.alloc(0x80, True)
        other = m.alloc(0x80, True)
        mgr = m.alloc(0x100, True)
        active, friends, guild, isfriend, exists = [rng.randrange(2) for _ in range(5)]
        hg, og = rng.choice([-1, 7]), rng.choice([-1, 7, 9])
        key = rng.randrange(65536)
        m.put32(mgr + 0xD8, win)
        m.put32(pref + 4, hero)
        m.write(pref + 8, bytes([active]))
        m.write(pref + 0x45C, bytes([friends, guild]))
        m.write(hero + 0x3C, struct.pack("<h", hg))
        m.write(other + 0x3C, struct.pack("<h", og))
        packet = m.alloc(5, True)
        m.write(packet, bytes([0xC1, 5, 0x40, key >> 8, key & 255]))
        m.stub(0x95F659, lambda q: pref)
        m.stub(0xAC3BF7, lambda q: mgr)
        m.stub(0x95F635, lambda q: pref)
        m.stub(0xB707B2, lambda q: isfriend, 4)
        m.stub(0x137C724, lambda q: 5)
        m.stub(0x95F6DB, lambda q: 0)
        m.stub(0x9A13F4, lambda q: other if exists else 0, 4)
        m.stub(0xA6AC96, lambda q: 0)
        calls = []
        prompts = []
        m.stub(0x9602CC, lambda q: calls.append(q.args(1)[0]) or 0)
        m.stub(0xC0A9C8, lambda q: prompts.append(1) or 0)
        m.allow((0x1270D06, 0x1270D9E), (0x95BD05, 0x95BDF3), (0x95FC71, 0x95FC81))
        m.call(0x1270D06, [packet], limit=100000)
        auto = lib.mu_social_party_autoaccept(
            active, friends, guild, isfriend, exists, hg, og
        )
        check(
            "party_autoaccept",
            [calls, prompts, m.u32(win + 0x3C)],
            [[1] if auto else [], [] if auto else [1], key],
        )
    for k in range(n):
        reset(m)
        ui(m)
        events = []
        visible = k & 1
        found = (k >> 1) & 1
        room = m.alloc(0x9C, True)
        m.stub(0xAAE6F9, lambda q: visible)
        m.stub(0x9C47C2, lambda q: 0x33330000)
        m.stub(0x9C4B1E, lambda q: room if found else 0, 4)
        m.stub(
            0xB76701,
            lambda q: events.append([q.args(3)[1], list(cstr(q, q.args(3)[2], 101))])
            or 0,
            12,
        )
        m.stub(
            0x9CC7E0,
            lambda q: events.append(
                [q.args(1)[0], list(ssread(q, q.uc.reg_read(cm.UC_X86_REG_ESP) + 8))]
            )
            or 0,
            28,
        )
        key = bytes([3, 5, 7])
        m.write(0x1CF0448, key)
        length = [0, 1, 99, 100, 101, 255][k % 6] if k < 12 else rng.randrange(256)
        serial = rng.randrange(256)
        plain = bytes(rng.randrange(32, 127) for _ in range(length))
        encoded = bytes(v ^ key[j % 3] for j, v in enumerate(plain))
        b = bytes([0xC1, 0, 4, serial, length]) + encoded
        packet = m.alloc(300, True)
        m.write(packet, b + bytes(300 - len(b)))
        m.allow((0xB772AF, 0xB77382), (0x976855, 0x976895))
        m.call(0xB772AF, [73, packet], ecx=room, limit=100000)
        out = Message()
        ok = lib.mu_social_room_text(b, len(b), key, C.byref(out))
        check(
            "room_text",
            events,
            [[out.serial, list(out.text)]] if ok and (visible or found) else [],
        )
        reset(m)
        ui(m)
        events = []
        event = k % 4
        serial = rng.randrange(256)
        name = bytes(rng.randrange(65, 91) for _ in range(10))
        b = bytes([0xC1, 15, 1, event, serial]) + name
        packet = m.alloc(15, True)
        m.write(packet, b)
        m.stub(
            0xB77382,
            lambda q: events.append([0, q.args(4)[2], list(cstr(q, q.args(4)[1], 11))])
            or 0,
            16,
        )
        m.stub(
            0xB774EC,
            lambda q: events.append([1, q.args(3)[2], list(cstr(q, q.args(3)[1], 11))])
            or 0,
            12,
        )
        m.stub(0xB785F6, lambda q: 0, 4)
        m.allow((0x122AA7E, 0x122AB8E))
        m.call(0x122AA7E, [73, packet], limit=100000)
        out = Event()
        ok = lib.mu_social_room_event_read(b, len(b), C.byref(out))
        check(
            "room_membership",
            events,
            [[out.event, out.user.serial, list(out.user.name)]] if ok else [],
        )
        reset(m)
        ui(m)
        events = []
        length = (
            [0, 1, 999, 1000, 1001, 65535][k % 6] if k < 12 else rng.randrange(1100)
        )
        ident = rng.randrange(65536)
        b = bytearray(b"Z" * 1100)
        struct.pack_into("<HH", b, 4, ident, length)
        packet = m.alloc(1100, True)
        m.write(packet, b)
        hdr = m.alloc(0x138, True)
        m.stub(0x9C47C2, lambda q: 0x33330000)
        m.stub(0x9C499B, lambda q: 0, 8)
        m.stub(0x9C48D6, lambda q: hdr, 4)
        m.stub(0xB72991, lambda q: 0, 8)
        m.stub(
            0xB76049, lambda q: events.append(list(cstr(q, q.args(2)[1], 1001))) or 0, 8
        )
        m.stub(0x1206598, lambda q: 0)
        m.allow((0x12509E3, 0x1250B05))
        m.call(0x12509E3, [packet], limit=100000)
        out = Body()
        ok = lib.mu_social_mail_body(bytes(b), len(b), C.byref(out))
        # The original manager gets the ID before its UI body boundary.
        got = [
            m.u32(hdr + 0x134),
            events,
            struct.unpack("<H", m.read(packet + 4, 2))[0],
        ]
        check("mail_body", got, [1, [list(out.text)], out.id] if ok else [0, [], ident])
        reset(m)
        ui(m)
        events = []
        read = k % 4
        ident = rng.randrange(65536)
        name = bytes(rng.randrange(65, 91) for _ in range(10))
        b = bytearray(80)
        struct.pack_into("<H", b, 4, ident)
        b[6:16] = name
        b[16:26] = b"2026-10-22"
        b[27:35] = b"12:34:56"
        b[46:78] = b"T" * 32
        b[78] = read
        packet = m.alloc(80, True)
        m.write(packet, b)
        m.put32(0x6FCA2C8, 255)
        m.stub(0x9C47C2, lambda q: 0x33330000)
        m.stub(0x9C49EE, lambda q: 0)
        m.stub(
            0xB70D64,
            lambda q: events.append(
                [
                    q.args(6)[0],
                    list(cstr(q, q.args(6)[1], 11)),
                    list(cstr(q, q.args(6)[2], 33)),
                    list(cstr(q, q.args(6)[3], 11)),
                    list(cstr(q, q.args(6)[4], 9)),
                    q.args(6)[5],
                ]
            )
            or 0,
            24,
        )
        m.stub(0xB70CB1, lambda q: 0)
        m.stub(0xB70BFF, lambda q: 0, 4)
        m.stub(0xA6AC96, lambda q: 0)
        label = m.alloc(24, True)
        sswrite(m, label, b"L")
        m.stub(0x11753C3, lambda q: label, 4)
        m.stub(0x8E7F90, lambda q: ptr(q))
        m.stub(0x95F547, lambda q: 0, 4)
        m.allow((0x12506CD, 0x1250995))
        m.call(0x12506CD, [packet], limit=100000)
        out = Letter()
        ok = lib.mu_social_mail_header(bytes(b), len(b), C.byref(out))
        check(
            "mail_header",
            events,
            (
                [
                    [
                        out.id,
                        list(out.sender),
                        list(out.title),
                        list(out.date),
                        list(out.time),
                        out.read,
                    ]
                ]
                if ok
                else []
            ),
        )
    for k in range(n):
        reset(m)
        events = []
        append_transport(m, events)
        bp = cm.STACK_BASE + cm.STACK_SIZE - 0x1000
        ident = rng.randrange(2**32)
        name = b"0123456789"
        title = b"T" * 32
        body = b"B" * [1, 255, 1000][k % 3]
        m.put32(bp + 8, ident)
        sswrite(m, bp + 12, name)
        sswrite(m, bp + 36, title)
        sswrite(m, bp + 60, body)
        m.allow((0xB75E3B, 0xB75EF9))
        m.slice(0xB75E3B, 0xB75EF9, bp)
        p = Packet()
        ok = lib.mu_social_mail_write(C.byref(p), ident, name, title, body, len(body))
        assert ok
        data = bytes(p.data[: p.size])
        ranges = [(4, 4), (8, 10), (18, 32), (50, 1), (51, 1), (52, 2), (54, len(body))]
        want = [[size, 1, list(data[off : off + size])] for off, size in ranges] + [
            ["send", p.send0, p.send1]
        ]
        check("mail_write", events[3:], want)
        reset(m)
        events = []
        append_transport(m, events)
        bp = cm.STACK_BASE + cm.STACK_SIZE - 0x1000
        length = [0, 1, 99, 100, 101, 255, 256, 1000][k % 8]
        body = bytes(rng.randrange(32, 127) for _ in range(length))
        key = bytes([3, 5, 7])
        m.write(0x1CF0448, key)
        sswrite(m, bp - 0x34, body)
        m.put32(bp - 0x14, 0x31313131)
        m.allow((0x976855, 0x976895), (0x9CCD44, 0x9CCDF9))
        m.slice(0x9CCD44, 0x9CCDF9, bp)
        ok = lib.mu_social_room_send(C.byref(p), body, len(body), key)
        assert ok
        data = bytes(p.data[: p.size])
        want = [
            [1, 1, [data[3]]],
            [1, 1, [data[4]]],
            [len(body), 1, list(data[5:])],
            ["send", p.send0, p.send1],
        ]
        check("room_send", events[3:], want)
    return report
