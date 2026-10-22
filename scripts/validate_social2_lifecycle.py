"""Additional original roster/connect/read/delete boundaries versus production C.

The transport and C++ manager boundaries are recorded; no socket body is run.
Connection ticket transform executes with the offline adapter's zero key.
"""

import ctypes as C
import random
import struct
import client_ui_machine as cm
import validate_social2_packets as common


def run(m, lib, cases):
    common.bind(lib)
    signatures = {
        "room_roster": [C.c_char_p, C.c_size_t, C.POINTER(common.User), C.c_size_t],
        "room_connect": [C.POINTER(common.Packet), C.c_uint16, C.c_uint32],
        "mail_read_request": [C.POINTER(common.Packet), C.c_uint16],
        "mail_delete_request": [C.POINTER(common.Packet), C.c_uint16],
    }
    for name, args in signatures.items():
        getattr(lib, "mu_social_" + name).argtypes = args
    result = {}
    rng = random.Random(27)

    def check(family, actual, expected):
        r = result.setdefault(family, {"cases": 0, "mismatches": 0})
        r["cases"] += 1
        if actual != expected:
            r["mismatches"] += 1
            r.setdefault("first", {"client": actual, "native": expected})

    for k in range(cases):
        common.reset(m)
        bp = cm.STACK_BASE + cm.STACK_SIZE - 0x1000
        count = [0, 1, 2, 29, 30, 31, 50, 255][k % 8]
        ui = rng.randrange(1, 2**32)
        data = bytearray(8)
        data[6] = count
        for j in range(count):
            data += bytes([rng.randrange(256)]) + bytes(
                rng.randrange(65, 91) for _ in range(10)
            )
        p = m.alloc(len(data), True)
        m.write(p, data)
        for off, v in [
            (8, ui),
            (12, p),
            (-0x2C, p),
            (-0x24, 8),
            (-0x20, 0),
            (-0x10, 0x31313131),
        ]:
            m.put32(bp + off, v)
        m.write(bp - 0x5C, bytes(11))
        events = []
        m.stub(0x9C47C2, lambda q: 0x32323232)

        def user(q):
            a = q.args(4)
            events.append([common.cstr(q, a[1], 11).decode("ascii"), a[2], a[3]])
            return 0

        m.stub(0x9C4A21, user, 16)
        for a, clean in [
            (0xA99D93, 0),
            (0xAAD26B, 0),
            (0xAAD299, 0),
            (0xAAF1C5, 4),
            (0xB2CED7, 12),
            (0xB0809D, 12),
            (0xB48B7E, 12),
            (0xB76F1F, 8),
        ]:
            m.stub(a, lambda q: 0, clean)
        m.allow((0xB76A01, 0xB76B62))
        m.slice(0xB76A01, 0xB76B62, bp)
        users = (common.User * 255)()
        size = lib.mu_social_room_roster(bytes(data), len(data), users, 255)
        expected = [[u.name.decode("ascii"), u.serial, u.server] for u in users[:size]]
        check("room_roster", events, expected)

        common.reset(m)
        events = []
        common.packet_transport(m, events)
        m.allow((0xD51D10, cm.function_extent(m.text, 0xD51D10)))
        room = rng.randrange(65536)
        ticket = [0, 1, 9, 10, 999999999, 1000000000, 2147483648, 4294967295][k % 8]
        obj = m.alloc(0x9C, True)
        m.put32(0x6FC9C64, 0x12345678)
        m.stub(0x9C9D24, lambda q: ui)
        m.stub(0x11F0DF8, lambda q: 0x31313131, 12)
        m.stub(0x9CC669, lambda q: 0x32323232)
        m.write(0x1CF0448, bytes(3))
        for a in (0x9CDF31, 0x198C41A, 0x198BF0D, 0x198BC29, 0x9C06DD):
            m.allow((a, cm.function_extent(m.text, a)))
        m.allow((0x9CC48A, 0x9CC5B8), (0x976855, 0x976895))
        m.call(0x9CC48A, [0x11223344, room, ticket], ecx=obj)
        packet = common.Packet()
        lib.mu_social_room_connect(C.byref(packet), room, ticket)
        check(
            "room_connect",
            [events, m.u32(obj + 0x40), m.u32(0x1CF1008)],
            [[common.packet_native(packet)], room, 0x6FCA2D8],
        )

        common.reset(m)
        events = []
        common.packet_transport(m, events)
        m.allow((0xD51D10, cm.function_extent(m.text, 0xD51D10)))
        m.allow((0x9C06DD, cm.function_extent(m.text, 0x9C06DD)), (0xB75F3C, 0xB76049))
        m.stub(0x9C47C2, lambda q: 0x31313131)
        m.stub(0x9C4CD1, lambda q: 0, 4)
        m.stub(0x9C4982, lambda q: 0, 4)
        ident = rng.randrange(65536)
        m.call(0xB75F3C, [ident], ecx=m.alloc(0x300, True))
        lib.mu_social_mail_read_request(C.byref(packet), ident)
        check("mail_read_request", events, [common.packet_native(packet)])

        common.reset(m)
        events = []
        common.packet_transport(m, events)
        m.allow((0xD51D10, cm.function_extent(m.text, 0xD51D10)))
        m.allow((0x9C06DD, cm.function_extent(m.text, 0x9C06DD)), (0xB6FF0A, 0xB6FF68))
        bp = cm.STACK_BASE + cm.STACK_SIZE - 0x1000
        m.put32(bp - 0x28, ident)
        m.slice(0xB6FF0A, 0xB6FF68, bp)
        lib.mu_social_mail_delete_request(C.byref(packet), ident)
        check("mail_delete_request", events, [common.packet_native(packet)])
    return result
