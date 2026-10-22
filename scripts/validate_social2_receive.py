"""Production room/mail transitions versus whole original receive/control handlers.

Window/container effects use the same explicit external model as the guest.
Sentinel-only peer lookup and malformed pre-existing cache packets have no
production representation and are counted separately, never as C comparisons.
"""

import ctypes as C
from pathlib import Path
import subprocess
import tempfile
from validate_social2_receive_guest import ClientOracle, corpus

ROOT = Path(__file__).resolve().parents[1]
KINDS = (
    "room_open",
    "mail_send",
    "mail_delete",
    "mail_read",
    "mail_body",
    "pending_track",
    "pending_close",
    "pending_bind",
    "pending_get",
)


def compile_library(path, mutation=None):
    args = ["clang", "-std=c11", "-O2", "-shared", "-fPIC"]
    if mutation:
        args += ["-DMU_SOCIAL2_MUTATION_" + mutation + "=1"]
    subprocess.run(
        args
        + [
            str(ROOT / x)
            for x in (
                "native/tests/social_receive_probe.c",
                "native/core/mu_social_messages.c",
                "reconstructed/social/social_packets.c",
            )
        ]
        + ["-o", str(path)],
        check=True,
    )
    lib = C.CDLL(str(path))
    lib.mu_social_receive_probe.argtypes = [
        C.POINTER(C.c_uint32),
        C.c_char_p,
        C.c_size_t,
        C.POINTER(C.c_uint32),
        C.c_char_p,
    ]
    return lib


def compare(lib, oracle, c):
    args = [
        KINDS.index(c.kind),
        c.result,
        c.mode,
        c.peer_lookup,
        int(c.visible),
        int(c.fee_exempt),
        int(c.header),
        int(c.cached),
        int(c.tracked),
        c.read_ui,
        int(c.compose_present),
        int(c.pending_peer),
        c.ui,
        c.letter,
        c.room,
        c.ticket,
        c.next_ui,
        c.length,
    ]
    a = (C.c_uint32 * 18)(*args)
    out = (C.c_uint32 * 32)()
    address = C.create_string_buffer(16)
    packet = c.packet()
    lib.mu_social_receive_probe(a, packet, len(packet), out, address)
    observed = oracle.run(c)
    s = observed.state
    effects = observed.effects()
    events = {e.key: e.args for e in effects}
    notice = events.get("notice.modal", events.get("notice.emit", (0,)))[0]
    cache = dict(s.cache)
    cached = cache.get(c.letter)
    cachelen = 0
    if cached is not None:
        declared = int.from_bytes(cached[6:8], "little")
        cachelen = len(cached[30 : 30 + min(declared, 1000)].split(b"\0", 1)[0])
    windows = dict(s.windows)
    pending = dict(s.pending)
    want = [
        s.next_ui,
        notice,
        1000 if "fee.format" in events else 0,
        int(s.pending_peer),
        len(s.rooms),
        len(s.headers),
        dict(s.headers).get(c.letter, 0),
        int(cached is not None),
        cachelen,
        int(c.letter in pending),
        pending.get(c.letter, 0),
        len(windows),
        int(c.ui in windows and windows[c.ui] == 0),
        int(bool(c.read_ui) and c.read_ui in windows),
        int(c.next_ui in windows),
    ]
    native = [out[i] for i in (0, 2, 3, 7, 8, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23)]
    if s.rooms:
        r = next(
            (r for r in s.rooms if len(s.rooms) > 1 and r.ui == c.next_ui), s.rooms[-1]
        )
        want += [r.ui, r.number, r.ticket, r.address]
        native += [out[9], out[10], out[11], address.value]
    if c.kind == "room_open" and c.result == 1 and c.mode in (0, 1, 2):
        reconnect = c.mode == 1 and c.peer_lookup not in (0, 0xFFFFFFFF)
        want += [2 if reconnect else 1, int(c.visible)]
        native += [out[4], out[12]]
        want.append(0)
        native.append(out[29])
    if c.kind == "mail_read":
        requests = sum(e.key == "transport.packet" for e in effects)
        want.append(requests)
        native.append(out[4])
        if c.tracked and c.read_ui:
            want.append(c.read_ui)
            native.append(out[1])
    if c.kind in ("pending_track", "pending_get"):
        want.append(observed.return_value & 0xFFFFFFFF)
        native.append(out[6])
    return want, native


def run(text_path, data_path, lib=None):
    oracle = ClientOracle(text_path, data_path)
    report = {}
    skipped = {}
    with tempfile.TemporaryDirectory() as tmp:
        lib = lib or compile_library(Path(tmp) / "receive.dylib")
        for c in corpus():
            reason = None
            if (
                c.kind == "room_open"
                and c.result == 1
                and c.mode == 1
                and c.peer_lookup == 0xFFFFFFFF
            ):
                reason = "external peer-map sentinel"
            if c.kind == "mail_read" and c.cached and not c.tracked and c.length > 1000:
                reason = "invalid pre-existing cache packet"
            if reason:
                skipped[reason] = skipped.get(reason, 0) + 1
                continue
            expected, native = compare(lib, oracle, c)
            r = report.setdefault("receive_" + c.kind, dict(cases=0, mismatches=0))
            r["cases"] += 1
            if expected != native:
                r["mismatches"] += 1
                r.setdefault(
                    "first",
                    dict(case=repr(c), client=repr(expected), native=repr(native)),
                )
    return report, skipped
