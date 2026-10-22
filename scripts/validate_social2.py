#!/usr/bin/env python3
"""Private instruction comparisons for NATIVE-SOCIAL-001 round 2.

Uses the same pinned captures and defined-memory machine as validate_social.
The item_unpack family executes all of 0xf08dca and its item-code decoder;
allocation/record-kind conversion begins at the recorded f08fb2 boundary.
No transport, encryption, login or protection body is entered.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile

import validate_social as base
import validate_social2_packets as packets
import validate_social2_lifecycle as lifecycle
import validate_social2_finalizer_guest as finalizer
import validate_social2_items as items
import validate_social2_formula as formulas

ROOT = Path(__file__).resolve().parents[1]


class Wire(C.Structure):
    _fields_ = (
        [("code", C.c_int32)]
        + [
            (n, C.c_uint8)
            for n in (
                "level_word",
                "durability",
                "excellent",
                "ancient",
                "flags",
                "harmony",
            )
        ]
        + [("sockets", C.c_uint8 * 5), ("extra", C.c_uint8 * 3)]
    )


def library(path):
    lib = C.CDLL(str(path))
    lib.mu_social_item_unpack.argtypes = [C.c_char_p, C.POINTER(Wire)]
    lib.mu_social_item_pack.argtypes = [C.POINTER(Wire), C.c_void_p]
    return lib


def run_items(m, lib, cases):
    rng = random.Random(21)
    report = {"cases": 0, "mismatches": 0}
    for k in range(cases):
        m.reset()
        m.allowed = [(0xF08DCA, 0xF08F2F), (0xF09DDC, 0xF09E41)]
        b = rng.randbytes(15)
        packet = m.alloc(15)
        m.write(packet, b)
        manager = m.alloc(32, True)
        m.handlers["IsBadReadPtr"] = lambda q, words: 0
        calls = []

        def convert(q):
            a = q.args(10)
            calls.append(a[:8] + [list(q.read(a[8], 5)), list(q.read(a[9], 3))])
            return 0x12345678

        m.stub(0xF08FB2, convert, 40)
        result = m.call(0xF08DCA, [packet], ecx=manager)
        out = Wire()
        lib.mu_social_item_unpack(b, C.byref(out))
        expected = [
            out.code >> 9,
            out.code & 511,
            out.level_word,
            out.durability,
            out.excellent,
            out.ancient,
            out.flags,
            out.harmony,
            list(out.sockets),
            list(out.extra),
        ]
        packed = C.create_string_buffer(15)
        lib.mu_social_item_pack(C.byref(out), packed)
        actual = [result, calls]
        want = [0x12345678, [expected]]
        report["cases"] += 1
        if actual != want or packed.raw != b:
            report["mismatches"] += 1
            report.setdefault(
                "first",
                {
                    "case": k,
                    "client": actual,
                    "native": want,
                    "roundtrip_equal": packed.raw == b,
                },
            )
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    evidence = Path.home() / "Documents/main-exe-study/evidence"
    p.add_argument(
        "--text", type=Path, default=evidence / "x86-text-capture-09/client-text.bin"
    )
    p.add_argument(
        "--data",
        type=Path,
        default=evidence / "image-data-run10/data-capture-10/client-image-data.bin",
    )
    p.add_argument("--cases", type=int, default=500)
    p.add_argument("--mutations", action="store_true")
    p.add_argument(
        "--finalizer-limit",
        type=int,
        help="debug only: limit the fixed finalizer corpus",
    )
    p.add_argument("--output", type=Path)
    p.add_argument(
        "--game-root", type=Path, help="opt-in installed FormulaData comparisons"
    )
    a = p.parse_args()
    if a.cases <= 0:
        p.error("--cases must be positive")
    text, data = a.text.read_bytes(), a.data.read_bytes()
    if (
        hashlib.sha256(text).hexdigest() != base.vn.TEXT_SHA256
        or hashlib.sha256(data).hexdigest() != base.vn.DATA_SHA256
    ):
        raise ValueError("private capture hash mismatch")
    m = base.Machine(text, data)
    m.allow((0xF08DCA, 0xF08F2F), (0xF09DDC, 0xF09E41))
    subprocess.run(
        ["make", "-C", str(ROOT / "reconstructed/social")],
        check=True,
        capture_output=True,
    )
    result = {
        "text_sha256": base.vn.TEXT_SHA256,
        "data_sha256": base.vn.DATA_SHA256,
        "families": {
            "item_unpack": run_items(
                m, library(ROOT / "reconstructed/social/libsocial.dylib"), a.cases
            )
        },
    }
    result["families"].update(
        packets.run(m, library(ROOT / "reconstructed/social/libsocial.dylib"), a.cases)
    )
    result["families"].update(
        lifecycle.run(
            m, library(ROOT / "reconstructed/social/libsocial.dylib"), a.cases
        )
    )
    result["families"].update(
        finalizer.run(
            library(ROOT / "reconstructed/social/libsocial.dylib"),
            text,
            data,
            a.finalizer_limit,
        )
    )
    result["families"].update(
        items.run(
            library(ROOT / "reconstructed/social/libsocial.dylib"),
            a.text,
            a.data,
            a.cases,
        )
    )
    result["families"].update(
        formulas.run(
            library(ROOT / "reconstructed/social/libsocial.dylib"),
            text,
            data,
            a.cases,
            a.game_root,
        )
    )
    if a.mutations:
        result["mutations"] = {}
        controls = {
            "ITEM": "item_unpack",
            "PARTY": "party_invite",
            "ANSWER": "party_answer",
            "REMOVE": "party_remove",
            "RESULT": "party_result",
            "ROOM": "room_text",
            "MAIL": "mail_body",
            "HEADER": "mail_header",
            "SEND_LENGTH": "room_send",
            "MAIL_WRITE": "mail_write",
            "CONNECT": "room_connect",
            "ROSTER": "room_roster",
            "READ": "mail_read_request",
            "DELETE": "mail_delete_request",
            "FINAL_RANK": "finalizer_rank",
            "FINAL_CONSUME": "finalizer_consumed_bit",
        }
        with tempfile.TemporaryDirectory() as tmp:
            for control, family in controls.items():
                dst = Path(tmp) / (control + ".dylib")
                subprocess.run(
                    [
                        "clang",
                        "-shared",
                        "-fPIC",
                        "-O2",
                        "-DMU_SOCIAL2_MUTATION_" + control + "=1",
                        str(ROOT / "reconstructed/social/item_options.c"),
                        str(ROOT / "reconstructed/social/social_packets.c"),
                        "-o",
                        str(dst),
                    ],
                    check=True,
                )
                lib = library(dst)
                if family == "item_unpack":
                    report = run_items(m, lib, 32)
                elif family in (
                    "room_connect",
                    "room_roster",
                    "mail_read_request",
                    "mail_delete_request",
                ):
                    report = lifecycle.run(m, lib, 32)[family]
                elif family.startswith("finalizer_"):
                    oracle = finalizer.Oracle(text, data)
                    from validate_social2_finalizer import compare_case

                    c = (
                        finalizer.case(L=0, E=0x40)
                        if control == "FINAL_RANK"
                        else finalizer.case(code=0x1824, L=1, E=0x30)
                    )
                    report = {"mismatches": int(oracle.run(c) != compare_case(lib, c))}
                else:
                    report = packets.run(m, lib, 32)[family]
                result["mutations"][family] = report["mismatches"] > 0
    result["cases"] = sum(x["cases"] for x in result["families"].values())
    result["mismatches"] = sum(x["mismatches"] for x in result["families"].values())
    if a.output:
        a.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return bool(result["mismatches"] or not all(result.get("mutations", {}).values()))


if __name__ == "__main__":
    sys.exit(main())
