"""PRIVATE, synthetic-only receive decision oracle for native-social2.

No production build or imports of production state code. See README.md for the
executed instruction ranges and the modeled manager/UI/transport contracts.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Literal, Union

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "scripts"))
import client_ui_machine as cm
import pins
import validate_social2_packets as helpers

TEXT_SHA256 = pins.TEXT.sha256
DATA_SHA256 = pins.DATA.sha256
Kind = Literal[
    "room_open",
    "mail_send",
    "mail_delete",
    "mail_read",
    "mail_body",
    "pending_track",
    "pending_close",
    "pending_bind",
    "pending_get",
]
Scalar = Union[int, bytes]

# Original instruction addresses observed without replacing any instructions.
DECISIONS = {
    0x122BB7B: "room.result0",
    0x122BBE2: "room.result1",
    0x122BE27: "room.result2",
    0x122BB76: "room.other_result",
    0x122BBF1: "room.mode0",
    0x122BC8D: "room.mode1",
    0x122BCAA: "room.mode1_missing",
    0x122BD35: "room.mode1_sentinel",
    0x122BD37: "room.mode1_reuse",
    0x122BDAE: "room.mode2",
    0xB71A7B: "send.result0",
    0xB71AB3: "send.result1",
    0xB71B80: "send.result2",
    0xB71BB8: "send.result3",
    0xB71BF0: "send.result4",
    0xB71C25: "send.result6",
    0xB71C5A: "send.result7",
    0xB71A76: "send.other_result",
    0xB71ABC: "send.close_nonzero_ui",
    0xB71B0D: "send.fee_format",
    0xB71B46: "send.emit_success",
    0xB71D5E: "delete.result0",
    0xB71D93: "delete.result1",
    0xB71D59: "delete.other_result",
    0xB71DB0: "delete.close_found_ui",
    0x9C4925: "delete.header_missing",
    0x9C4940: "delete.window_missing",
    0x9C4944: "delete.window_found",
    0xB75F8B: "read.transport_request",
    0xB75FE8: "read.cache_replay",
    0xB76000: "read.already_tracked",
    0xB76018: "read.select_ui",
    0x1250A00: "body.reject",
    0x1250A62: "body.header_missing",
    0x1250A67: "body.header_found",
    0x9C4D17: "pending.insert",
    0x9C4D40: "pending.already_present",
    0x9C4D8D: "pending.erase",
    0x9C4DED: "pending.bind_present",
    0x9C4E48: "pending.get_present",
    0x9C4E58: "pending.get_missing",
}


@dataclass(frozen=True)
class Case:
    kind: Kind
    result: int = 1
    mode: int = 0
    peer_lookup: int = 0  # 0 absent, 0xffffffff sentinel, otherwise UI ID
    visible: bool = False
    fee_exempt: bool = False
    header: bool = True
    cached: bool = False
    tracked: bool = False
    read_ui: int = 0
    compose_present: bool = True
    pending_peer: bool = True
    ui: int = 0x12345678
    letter: int = 0x92AB
    room: int = 0x8A91
    ticket: int = 0xF1234567
    next_ui: int = 0x3210
    length: int = 3
    peer: bytes = b"PeerABCDEF"  # exactly ten bytes, never client data
    address: bytes = b"192.0.2.123"
    direct: bool = False  # compare send/delete wrapper and method entry

    def packet(self) -> bytes:
        if self.kind == "room_open":
            b = bytearray(36)
            b[:3] = bytes([0xC1, 36, 0x83])
            b[3:18] = self.address[:15].ljust(15, b"\0")
            struct.pack_into("<HI", b, 18, self.room, self.ticket)
            b[24], b[35] = self.mode, self.result
            b[25:35] = self.peer[:10].ljust(10, b"\0")
            return bytes(b)
        if self.kind == "mail_send":
            return struct.pack("<BBBBI", 0xC1, 8, 0x41, self.result, self.ui)
        if self.kind == "mail_delete":
            return struct.pack("<BBBBH", 0xC1, 6, 0xA2, self.result, self.letter)
        # Original receive copies 1,000 bytes even for a short body.
        b = bytearray(b"Q" * 1100)
        b[:4] = bytes([0xC2, 4, 6, 0xEC])
        struct.pack_into("<HH", b, 4, self.letter, self.length)
        return bytes(b)


@dataclass(frozen=True)
class Event:
    key: str
    args: tuple[Scalar, ...] = ()


@dataclass(frozen=True)
class Room:
    ui: int
    number: int
    ticket: int
    address: bytes
    connected: bool


@dataclass(frozen=True)
class Snapshot:
    next_ui: int
    pending_peer: bool
    rooms: tuple[Room, ...]
    headers: tuple[tuple[int, int], ...]  # letter ID, read flag
    cache: tuple[tuple[int, bytes], ...]  # fixed 1,030-byte normalized packets
    pending: tuple[tuple[int, int], ...]  # absent vs tracked-with-zero are distinct
    windows: tuple[tuple[int, int], ...]  # UI ID, letter ID; compose uses zero
    selected_ui: int


@dataclass(frozen=True)
class Outcome:
    events: tuple[Event, ...]
    state: Snapshot
    packet: bytes
    return_value: int | None = None  # meaningful only for pending_track/get

    def effects(self) -> tuple[Event, ...]:
        """Drop pure queries for C effect comparison, retaining ordered effects."""
        queries = {
            "room.find_peer",
            "room.find_ui",
            "header.find",
            "window.find",
            "cache.find",
            "pending.find",
            "text.lookup",
            "ui.visible",
        }
        return tuple(e for e in self.events if e.key not in queries)


def initial(c: Case) -> Snapshot:
    rooms = ()
    if c.peer_lookup not in (0, 0xFFFFFFFF):
        rooms = (Room(c.peer_lookup, 0x1111, 0x22223333, b"192.0.2.9", True),)
    windows = {}
    if c.compose_present and c.ui:
        windows[c.ui] = 0
    if c.read_ui:
        windows[c.read_ui] = c.letter
    return Snapshot(
        c.next_ui,
        c.pending_peer,
        rooms,
        ((c.letter, 0),) if c.header else (),
        ((c.letter, replace(c, kind="mail_body").packet()[:1030]),) if c.cached else (),
        ((c.letter, c.read_ui),) if c.tracked else (),
        tuple(sorted(windows.items())),
        0,
    )


def expected(c: Case) -> Outcome:
    """Pure typed prediction, independent of the emulated external models."""
    s = initial(c)
    events: list[Event] = []
    b = c.packet()
    ret = None

    def e(key: str, *args: Scalar) -> None:
        events.append(Event(key, args))

    def close(ui: int) -> None:
        nonlocal s
        e("ui.close", ui)
        e("window.remove", ui)
        s = replace(s, windows=tuple(x for x in s.windows if x[0] != ui))

    def notice(ident: int, modal: bool = True) -> None:
        e("text.lookup", ident)
        e("notice.modal" if modal else "notice.emit", ident)

    def body(packet: bytes) -> bytes:
        nonlocal s
        ident, length = struct.unpack_from("<HH", packet, 4)
        if length > 1000:
            e("body.reject", length)
            return packet
        packet = packet[: 30 + length] + b"\0" + packet[31 + length :]
        e("cache.put", ident, packet[:1030])
        cache = dict(s.cache)
        cache[ident] = packet[:1030]
        s = replace(s, cache=tuple(sorted(cache.items())))
        e("header.find", ident, int(c.header))
        if c.header:
            s = replace(s, headers=((ident, 1),))
            e("ui.read_flag", ident, 1)
            text = packet[30:1030].split(b"\0", 1)[0]
            e("ui.read_open", ident, text, s.next_ui)
            pending, windows = dict(s.pending), dict(s.windows)
            # External show-read model binds only an existing pending entry.
            if ident in pending:
                pending[ident] = s.next_ui
            windows[s.next_ui] = ident
            s = replace(
                s,
                next_ui=s.next_ui + 1,
                pending=tuple(sorted(pending.items())),
                windows=tuple(sorted(windows.items())),
            )
        return packet

    if c.kind == "room_open":
        peer = c.peer[:10].split(b"\0", 1)[0]
        address = c.address[:15].split(b"\0", 1)[0]
        if c.result in (0, 2) or (c.result == 1 and c.mode == 0):
            e("room.pending_remove", peer)
            s = replace(s, pending_peer=False)
        if c.result in (0, 2):
            notice(0x42D if c.result == 0 else 0x42E)
        elif c.result == 1 and c.mode in (0, 1, 2):
            if c.mode == 1:
                e("room.find_peer", peer, c.peer_lookup)
            if c.mode == 1 and c.peer_lookup == 0xFFFFFFFF:
                pass
            elif c.mode == 1 and c.peer_lookup:
                ui = c.peer_lookup
                e("room.find_ui", ui)
                e("transport.close", ui)
                e("transport.connect", ui, address, c.room, c.ticket)
                e("ui.room_reconnect", ui, c.room, address, c.ticket)
                s = replace(s, rooms=(Room(ui, c.room, c.ticket, address, True),))
            else:
                ui = s.next_ui
                e("room.create", address, c.room, c.ticket, ui)
                e("ui.visible", int(c.visible))
                e("ui.room_open", ui, peer, c.room, address, c.ticket, int(c.visible))
                s = replace(
                    s,
                    next_ui=ui + 1,
                    rooms=tuple(
                        sorted(
                            (*s.rooms, Room(ui, c.room, c.ticket, address, True)),
                            key=lambda r: r.ui,
                        )
                    ),
                )
    elif c.kind == "mail_send":
        notices = {0: 0x41D, 2: 0x425, 3: 0x428, 4: 0x429, 6: 0x42C, 7: 0x1A7}
        if c.result == 1:
            if c.ui:
                close(c.ui)
            e("text.lookup", 0x416)
            e("fee.exempt", int(c.fee_exempt))
            if not c.fee_exempt:
                e("text.lookup", 0x130F)
                e("fee.format", 1000)
                e("fee.append")
            e("notice.emit", 0x416)
        elif c.result in notices:
            notice(notices[c.result])
    elif c.kind == "mail_delete":
        if c.result == 0:
            notice(0x41F)
        elif c.result == 1:
            e("header.find", c.letter, int(c.header))
            if c.header:
                e("window.find", c.letter, c.read_ui)
                if c.read_ui:
                    close(c.read_ui)
            e("header.remove", c.letter)
            e("cache.remove", c.letter)
            e("ui.mail_clear")
            e("ui.mail_rebuild")
            s = replace(s, headers=(), cache=())
    elif c.kind in (
        "mail_read",
        "pending_track",
        "pending_bind",
        "pending_close",
        "pending_get",
    ):
        e("pending.find", c.letter, int(c.tracked))
        if c.kind == "pending_get":
            ret = c.read_ui if c.tracked else 0
        elif c.kind == "pending_close":
            if c.tracked:
                e("pending.erase", c.letter)
                s = replace(s, pending=())
        elif c.kind == "pending_bind":
            if c.tracked:
                s = replace(s, pending=((c.letter, c.ui),))
        else:
            ret = int(c.tracked) if c.kind == "pending_track" else None
            if not c.tracked:
                e("pending.insert", c.letter, 0)
                s = replace(s, pending=((c.letter, 0),))
            if c.kind == "mail_read":
                if not c.tracked:
                    e("cache.find", c.letter, int(c.cached))
                    if c.cached:
                        e("cache.find", c.letter, 1)
                        body(c.packet())
                    else:
                        e(
                            "transport.packet",
                            bytes([0xC1, 6, 0x30, 0]) + struct.pack("<H", c.letter),
                            0,
                            0,
                        )
                else:
                    e("pending.find", c.letter, 1)
                    if c.read_ui:
                        e("ui.read_select", c.read_ui, 1)
                        e("ui.refresh")
                        s = replace(s, selected_ui=c.read_ui)
    elif c.kind == "mail_body":
        b = body(b)
    else:
        raise ValueError("unknown case kind")
    return Outcome(tuple(events), s, b, ret)


class ClientOracle:
    """Reusable pinned-code executor. Each run resets the full model and machine."""

    def __init__(self, text_path: Path | None = None, data_path: Path | None = None):
        text = pins.TEXT.read(text_path, mismatch=ValueError("private capture hash mismatch"))
        data = pins.DATA.read(data_path, mismatch=ValueError("private capture hash mismatch"))
        self.machine = cm.Machine(text, data)
        self.stub_manifest: dict[int, tuple[int, str]] = {}
        self.decision_hits: set[str] = set()

        def observe(uc, address, size, user):
            if address in DECISIONS:
                self.decision_hits.add(DECISIONS[address])

        self.machine.uc.hook_add(
            cm.UC_HOOK_CODE,
            observe,
            begin=cm.TEXT_BASE,
            end=cm.TEXT_BASE + len(text) - 1,
        )

    def run(self, c: Case) -> Outcome:
        m = self.machine
        helpers.reset(m)
        self.decision_hits = set()
        s = initial(c)
        events: list[Event] = []
        rooms = {r.ui: r for r in s.rooms}
        windows = dict(s.windows)
        headers = dict(s.headers)
        cache = dict(s.cache)
        nodes: dict[int, int] = {}
        next_ui = c.next_ui
        selected = 0
        pending_peer = c.pending_peer
        self.stub_manifest = {}

        def e(key: str, *args: Scalar) -> None:
            events.append(Event(key, args))

        def stub(a: int, n: int, key: str, fn):
            self.stub_manifest[a] = (n, key)
            m.stub(a, fn, n)

        def cstr(p: int, cap: int = 1100) -> bytes:
            # Read through terminator only, never read undefined synthetic heap.
            out = bytearray()
            for off in range(cap):
                byte = m.read(p + off, 1)[0]
                if byte == 0:
                    return bytes(out)
                out.append(byte)
            raise ValueError("unterminated modeled string")

        manager = m.alloc(0x80, True)
        mailbox, window_manager = m.alloc(0x40, True), m.alloc(0x40, True)
        m.put32(manager + 0x18, mailbox)
        m.put32(manager + 0x1C, window_manager)
        host, win = helpers.ui(m)
        m.put32(host + 0x88, win)
        room_obj = m.alloc(0x9C, True)
        header_obj = m.alloc(0x138, True)
        m.put32(header_obj + 4, c.letter)
        read_obj = m.alloc(0x40, True)
        m.put32(read_obj + 0x38, c.read_ui)
        for ident, ui in s.pending:
            node = m.alloc(8, True)
            m.put32(node, ident)
            m.put32(node + 4, ui)
            nodes[ident] = node

        # Execute pending branch/control routines; only the STL primitives are models.
        def find(q):
            out, keyp = q.args(2)
            ident = q.u32(keyp)
            e("pending.find", ident, int(ident in nodes))
            q.put32(out, nodes.get(ident, 0))
            return out

        def end(q):
            (out,) = q.args(1)
            q.put32(out, 0)
            return out

        def pair(q):
            keyp, uip = q.args(2)
            p = helpers.ptr(q)
            q.put32(p, q.u32(keyp))
            q.put32(p + 4, q.u32(uip))
            return p

        def insert(q):
            out, p = q.args(2)
            ident, ui = q.u32(p), q.u32(p + 4)
            node = q.alloc(8, True)
            q.put32(node, ident)
            q.put32(node + 4, ui)
            nodes[ident] = node
            q.put32(out, node)
            e("pending.insert", ident, ui)
            return out

        def erase(q):
            out, node = q.args(2)
            ident = q.u32(node)
            nodes.pop(ident, None)
            q.put32(out, 0)
            e("pending.erase", ident)
            return out

        stub(0x9CBAAB, 8, "stl.find", find)
        stub(0x9CB5CA, 4, "stl.end", end)
        stub(
            0x9C94BE,
            4,
            "stl.equal",
            lambda q: int(q.u32(helpers.ptr(q)) == q.u32(q.args(1)[0])),
        )
        stub(
            0x9C95D2,
            4,
            "stl.not_equal",
            lambda q: int(q.u32(helpers.ptr(q)) != q.u32(q.args(1)[0])),
        )
        stub(0x9C5644, 8, "stl.pair", pair)
        stub(0x9C8580, 8, "stl.insert", insert)
        stub(0x9C8473, 8, "stl.erase", erase)
        stub(0x9C9619, 0, "stl.deref", lambda q: q.u32(helpers.ptr(q)))
        m.allow(
            (0x9C4CD1, 0x9C4D45),
            (0x9C4D47, 0x9C4DA5),
            (0x9C4DA7, 0x9C4E00),
            (0x9C4E02, 0x9C4E5C),
        )

        stub(0x9C47C2, 0, "manager.singleton", lambda q: manager)
        stub(0xB74520, 0, "ui.friend_window", lambda q: win)
        stub(0x95F5D7, 0, "ui.notice_owner", lambda q: win)

        def remove_pending(q):
            nonlocal pending_peer
            e("room.pending_remove", cstr(q.args(1)[0], 11))
            pending_peer = False
            return 0

        def find_peer(q):
            e("room.find_peer", cstr(q.args(1)[0], 11), c.peer_lookup)
            return c.peer_lookup

        def room_create(q):
            nonlocal next_ui
            addressp, number, ticket = q.args(3)
            address = cstr(addressp, 16)
            ui = next_ui
            next_ui += 1
            rooms[ui] = Room(ui, number, ticket, address, True)
            e("room.create", address, number, ticket, ui)
            return ui

        def connect(q):
            addressp, number, ticket = q.args(3)
            ui = c.peer_lookup
            address = cstr(addressp, 16)
            rooms[ui] = Room(ui, number, ticket, address, True)
            e("transport.connect", ui, address, number, ticket)
            return 0

        def room_open(q):
            ui, peer, number, address, ticket, visible = q.args(6)
            e(
                "ui.room_open",
                ui,
                cstr(peer, 11),
                number,
                cstr(address, 16),
                ticket,
                visible,
            )
            return 0

        def room_reconnect(q):
            ui, number, address, ticket = q.args(4)
            e("ui.room_reconnect", ui, number, cstr(address, 16), ticket)
            return 0

        stub(0x9C4B8D, 4, "room.pending_remove", remove_pending)
        stub(0x9C49D5, 4, "room.find_peer", find_peer)
        stub(0x9C4A02, 12, "room.create", room_create)
        stub(
            0x9C4B1E,
            4,
            "room.find_ui",
            lambda q: e("room.find_ui", q.args(1)[0]) or room_obj,
        )
        stub(
            0x9CC5B8,
            0,
            "transport.close",
            lambda q: e("transport.close", c.peer_lookup) or 0,
        )
        stub(0x9CC48A, 12, "transport.connect", connect)
        stub(
            0xAAE6F9,
            0,
            "ui.visible",
            lambda q: e("ui.visible", int(c.visible)) or int(c.visible),
        )
        stub(0xB767EC, 24, "ui.room_open", room_open)
        stub(0xB76935, 16, "ui.room_reconnect", room_reconnect)

        # Localization/formatting substitutes contain synthetic tokens only.
        tokens: dict[int, int] = {}

        def lookup(q):
            (ident,) = q.args(1)
            p = q.alloc(32, True)
            q.write(p, ("N%08x" % ident).encode() + b"\0")
            tokens[p] = ident
            e("text.lookup", ident)
            return p

        def global_text(q):
            p = lookup(q)
            obj = q.alloc(24, True)
            helpers.sswrite(q, obj, cstr(p))
            tokens[obj] = tokens[p]
            return obj

        def format_text(q):
            out, fmt, source = q.args(3)
            ident = tokens.get(fmt, tokens.get(source, 0))
            q.write(out, ("N%08x" % ident).encode() + b"\0")
            if ident == 0x130F:
                e("fee.format", source)
            return 9

        stub(0x95F027, 4, "text.lookup", lookup)
        stub(0x11753C3, 4, "text.global_lookup", global_text)
        stub(0x8E7F90, 0, "string.c_str", lambda q: helpers.ptr(q))
        stub(
            0xB3967C,
            28,
            "notice.modal",
            lambda q: e("notice.modal", tokens[q.args(7)[2]]) or 0,
        )
        stub(0x1072152, 0, "fee.manager", lambda q: manager)
        stub(
            0x1072AD3,
            0,
            "fee.exempt",
            lambda q: e("fee.exempt", int(c.fee_exempt)) or int(c.fee_exempt),
        )
        stub(0x9619DD, 0, "string.format", format_text)
        stub(0x9CE20F, 0, "string.concat", lambda q: e("fee.append") or 0)
        stub(0x95F136, 0, "ui.notice_handle", lambda q: win)

        def notice_emit(q):
            token = helpers.ssread(q, q.args(1)[0])
            e("notice.emit", int(token[1:], 16))
            return 0

        stub(0x95F547, 4, "notice.emit", notice_emit)

        def header_find(q):
            (ident,) = q.args(1)
            e("header.find", ident, int(ident in headers))
            return header_obj if ident in headers else 0

        def window_find(q):
            if q.args(1)[0] != header_obj:
                raise ValueError("header identity lost at window lookup")
            e("window.find", c.letter, c.read_ui)
            return read_obj if c.read_ui else 0

        def header_remove(q):
            (ident,) = q.args(1)
            e("header.remove", ident)
            headers.pop(ident, None)
            return 0

        def cache_remove(q):
            (ident,) = q.args(1)
            e("cache.remove", ident)
            cache.pop(ident, None)
            return 0

        def window_remove(q):
            (ui,) = q.args(1)
            e("window.remove", ui)
            windows.pop(ui, None)
            return 0

        stub(0x9C48D6, 4, "header.find", header_find)
        stub(0x9CD1D2, 4, "window.find", window_find)
        stub(0x9D01A9, 4, "header.remove", header_remove)
        stub(0x9D06FF, 4, "cache.remove", cache_remove)
        stub(0x9C4B37, 4, "window.remove", window_remove)
        stub(0xB71DFD, 0, "ui.mail_rebuild", lambda q: e("ui.mail_rebuild") or 0)
        m.allow(
            (0x9C4908, 0x9C494E),
            (0x9C9D24, 0x9C9D33),
            (0x9C4885, 0x9C48AB),
            (0xB77241, 0xB77272),
        )

        def ui_call(q):
            # These are known call-site arities in the executed routines.
            ret = q.u32(q.uc.reg_read(cm.UC_X86_REG_ESP))
            if ret == 0xB7725D:
                e("ui.close", q.args(4)[3])
            elif ret == 0xB71DED:
                e("ui.mail_clear")
            elif ret == 0xB7602F:
                nonlocal selected
                selected, shown = q.args(5)[3:5]
                e("ui.read_select", selected, shown)
            else:
                raise ValueError("unrecognized UI call site")
            return 0

        stub(0xAAE7E0, 0, "ui.invoke", ui_call)
        stub(0xAAE79E, 0, "ui.refresh", lambda q: e("ui.refresh") or 0)

        def cache_find(q):
            (ident,) = q.args(1)
            e("cache.find", ident, int(ident in cache))
            if ident not in cache:
                return 0
            p = q.alloc(1100, True)
            q.write(p, cache[ident])
            return p

        def cache_put(q):
            ident, p = q.args(2)
            cache[ident] = q.read(p, 1030)
            e("cache.put", ident, cache[ident])
            return 0

        def read_open(q):
            nonlocal next_ui
            headerp, bodyp = q.args(2)
            ident = q.u32(headerp + 4)
            e("ui.read_open", ident, cstr(bodyp, 1001), next_ui)
            windows[next_ui] = ident
            if ident in nodes:
                q.put32(nodes[ident] + 4, next_ui)
            next_ui += 1
            return 0

        stub(0x9C4982, 4, "cache.find", cache_find)
        stub(0x9C499B, 8, "cache.put", cache_put)
        stub(0xB72991, 8, "ui.read_flag", lambda q: e("ui.read_flag", *q.args(2)) or 0)
        stub(0xB76049, 8, "ui.read_open", read_open)
        stub(0x1206598, 0, "body.reject", lambda q: e("body.reject", q.args(3)[2]) or 0)
        helpers.packet_transport(m, [])

        def send(q):
            p = helpers.ptr(q)
            n = struct.unpack("<H", q.read(p, 2))[0]
            b = bytearray(q.read(p + 2, n))
            b[1] = n  # explicit count finalization model, opaque transport
            e("transport.packet", bytes(b), *q.args(2))
            return 1

        stub(0xD52055, 12, "transport.prepare", lambda q: 0)
        stub(0xD51D4F, 8, "transport.packet", send)

        m.allow(
            (0x122BAF8, 0x122BEA4),
            (0x1250995, 0x12509E3),
            (0xB71A08, 0xB71C9B),
            (0xB71D35, 0xB71DFD),
            (0xB75F3C, 0xB76049),
            (0x12509E3, 0x1250B05),
            (0x9C06DD, cm.function_extent(m.text, 0x9C06DD)),
            (0xD51D10, cm.function_extent(m.text, 0xD51D10)),
        )
        packet = c.packet()
        p = m.alloc(len(packet), True)
        m.write(p, packet)
        entries = {
            "room_open": 0x122BAF8,
            "mail_send": 0xB71A08 if c.direct else 0x12509BC,
            "mail_delete": 0xB71D35 if c.direct else 0x1250995,
            "mail_read": 0xB75F3C,
            "mail_body": 0x12509E3,
            "pending_track": 0x9C4CD1,
            "pending_close": 0x9C4D47,
            "pending_bind": 0x9C4DA7,
            "pending_get": 0x9C4E02,
        }
        args = (
            [c.letter, c.ui]
            if c.kind == "pending_bind"
            else (
                [c.letter]
                if c.kind
                in ("mail_read", "pending_track", "pending_close", "pending_get")
                else [p]
            )
        )
        rv = m.call(
            entries[c.kind],
            args,
            ecx=manager if c.kind.startswith("pending_") else win,
            limit=150000,
        )
        cleanup = (
            8
            if c.kind == "pending_bind"
            else (
                0
                if entries[c.kind] in (0x122BAF8, 0x12509BC, 0x1250995, 0x12509E3)
                else 4
            )
        )
        if (
            m.uc.reg_read(cm.UC_X86_REG_ESP)
            != cm.STACK_BASE + cm.STACK_SIZE - 0x1000 - 4 * len(args) + cleanup
        ):
            raise AssertionError(
                "original entry returned with an unbalanced synthetic stack"
            )
        if c.header:
            if c.letter in headers:
                headers[c.letter] = m.u32(header_obj + 0x134)
        state = Snapshot(
            next_ui,
            pending_peer,
            tuple(sorted(rooms.values(), key=lambda r: r.ui)),
            tuple(sorted(headers.items())),
            tuple(sorted(cache.items())),
            tuple(sorted((k, m.u32(v + 4)) for k, v in nodes.items())),
            tuple(sorted(windows.items())),
            selected,
        )
        for a, entry in m.stubs.items():
            if entry[0] == "client" and a not in self.stub_manifest:
                key = {
                    0x19898A0: "crt.memcpy",
                    0x194C200: "crt.copy",
                    0x194CD00: "crt.memset",
                    0x8E6D00: "string.empty",
                    0x94997E: "string.construct",
                    0x8E83A0: "string.destroy",
                    0x94F183: "string.finalize",
                    0x8E80E0: "string.copy",
                    0x94AF7D: "string.assign",
                    0xAC3BF7: "ui.host",
                    0x95F635: "ui.friend",
                }[a]
                self.stub_manifest[a] = (entry[1][1], key)
        return Outcome(
            tuple(events),
            state,
            m.read(p, len(packet)),
            rv if c.kind in ("pending_track", "pending_get") else None,
        )


def corpus() -> list[Case]:
    out = []
    for result in (0, 1, 2, 3, 255):
        for mode in (0, 1, 2, 3, 255):
            for peer in (0, 0xFFFFFFFF, 0x76543210):
                for visible in (False, True):
                    out.append(
                        Case(
                            "room_open",
                            result=result,
                            mode=mode,
                            peer_lookup=peer,
                            visible=visible,
                        )
                    )
    for result in (*range(9), 255):
        for ui in (0, 0x12345678):
            for present in (False, True):
                for fee in (False, True):
                    for direct in (False, True):
                        out.append(
                            Case(
                                "mail_send",
                                result=result,
                                ui=ui,
                                compose_present=present,
                                fee_exempt=fee,
                                direct=direct,
                            )
                        )
    for result in (0, 1, 2, 255):
        for header in (False, True):
            for cached in (False, True):
                for tracked in (False, True):
                    for ui in (0, 0x76543210):
                        for direct in (False, True):
                            out.append(
                                Case(
                                    "mail_delete",
                                    result=result,
                                    header=header,
                                    cached=cached,
                                    tracked=tracked,
                                    read_ui=ui,
                                    direct=direct,
                                )
                            )
    for header in (False, True):
        for cached in (False, True):
            for tracked in (False, True):
                for ui in (0, 0x76543210):
                    for length in (0, 1, 999, 1000, 1001, 65535):
                        out.append(
                            Case(
                                "mail_read",
                                header=header,
                                cached=cached,
                                tracked=tracked,
                                read_ui=ui,
                                length=length,
                            )
                        )
    for header in (False, True):
        for cached in (False, True):
            for tracked in (False, True):
                for length in (0, 1, 999, 1000, 1001, 65535):
                    out.append(
                        Case(
                            "mail_body",
                            header=header,
                            cached=cached,
                            tracked=tracked,
                            length=length,
                        )
                    )
    for kind in ("pending_track", "pending_close", "pending_bind", "pending_get"):
        for tracked in (False, True):
            for ui in (0, 0x76543210):
                out.append(Case(kind, tracked=tracked, read_ui=ui))
    return out
