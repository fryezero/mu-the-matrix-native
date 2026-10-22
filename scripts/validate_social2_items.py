"""Full item category/prefix/advanced/trade routines against production C."""

import ctypes as C
import random
from validate_social2_finalizer import Context, Option
import validate_social2_item_guest as guest

I = C.c_int32


class Decoded(C.Structure):
    _fields_ = (
        [
            (n, I)
            for n in (
                "code",
                "level_word",
                "level",
                "skill_bit",
                "luck_bit",
                "add_rank",
                "skill",
                "durability",
                "excellent",
                "ancient",
                "period",
                "expired",
                "flag_72",
                "harmony_kind",
                "harmony_level",
                "socket_subtype",
                "socket_count",
            )
        ]
        + [(n, I * 5) for n in ("socket_raw", "seed_index", "seed_level")]
        + [(n, I) for n in ("socket_bonus", "element", "element_aux")]
        + [
            ("rank", (I * 4) * 4),
            ("extra_excellent", I * 3),
            ("special_raw", I * 5),
            ("extra_word", I),
            ("extra_124", I * 5),
        ]
        + [
            (n, I)
            for n in (
                "advanced_group",
                "advanced_level",
                "saved_group",
                "advanced_slot",
                "advanced_option",
                "artifact_count",
            )
        ]
        + [
            ("artifact", (I * 3) * 3),
            ("guardian_base", I),
            ("guardian_keys", I * 5),
            ("prefix_count", I),
            ("prefix", Option * 8),
        ]
    )


def value(v):
    return [value(x) for x in v] if isinstance(v, C.Array) else v


def run(lib, text_path, data_path, cases):
    from validate_social2 import Wire

    lib.mu_social_item_convert.argtypes = [
        C.POINTER(Wire),
        C.POINTER(Context),
        C.POINTER(Decoded),
    ]
    lib.mu_social_item_trade_banned.argtypes = [C.POINTER(Wire), C.POINTER(Context)]
    lib.mu_social_item_advanced_eligible.argtypes = [
        C.POINTER(Wire),
        C.POINTER(Context),
        I,
    ]
    lib.mu_social_item_advanced_group.argtypes = [C.POINTER(Wire), C.POINTER(Context)]
    reports = {}
    rng = random.Random(28)

    def check(f, a, b):
        r = reports.setdefault(f, {"cases": 0, "mismatches": 0})
        r["cases"] += 1
        if a != b:
            r["mismatches"] += 1
            r.setdefault("first", {"client": a, "native": b})

    with guest.load(text_path=text_path, data_path=data_path) as h:
        for k in range(cases):
            wire = Wire()
            wire.code = [
                1,
                0x21FE,
                0x1C34,
                0x1A14,
                0x1C0B,
                0x1C1A,
                0x1C15,
                0x2C00,
                0x2C01,
            ][k % 9]
            for n in (
                "level_word",
                "durability",
                "excellent",
                "ancient",
                "flags",
                "harmony",
            ):
                setattr(wire, n, rng.randrange(256))
            wire.sockets[:] = [
                rng.choice([0, 1, 49, 50, 52, 103, 254, 255]) for _ in range(5)
            ]
            wire.extra[:] = [
                rng.choice([0, 1, 0xFE, 0xFF, rng.randrange(256)]) for _ in range(3)
            ]
            c = Context()
            c.kind_a = [1, 8, 0x19, 0x1A, 0x1C, 0x14, 0x1D, 0x13, 0x22, 0x2D][k % 10]
            c.kind_b = rng.choice([1, 14, 0x2B, 0x2C, 0x4C, 0x6A, 0x72])
            c.grade = [0, 2, 3, 4, 6, 8][k % 6]
            c.skill = rng.randrange(65536)
            c.base_level = rng.randrange(8)
            c.normalized_slot = rng.choice([0, 14, 15, 255])
            c.slot_flags[:] = [rng.randrange(2) for _ in range(4)]
            c.excellent_resolved = rng.randrange(3)
            c.can_trade = c.slot_flags[1]
            c.capability = k % 7 != 0
            c.character_option = k % 3 == 0
            c.character_status = rng.choice([0, 8, 0x20, 1])
            w = guest.Wire(
                wire.code,
                wire.level_word,
                wire.durability,
                wire.excellent,
                wire.ancient,
                wire.flags,
                wire.harmony,
                tuple(wire.sockets),
                tuple(wire.extra),
            )
            r = guest.Record(
                c.kind_a,
                c.kind_b,
                c.grade,
                c.skill,
                c.base_level,
                0,
                tuple(c.slot_flags),
            )
            b = guest.Boundaries(
                normalized_slot=c.normalized_slot,
                finalizer_excellent=c.excellent_resolved,
                capability=bool(c.capability),
                character_option=bool(c.character_option),
                character_status=c.character_status,
            )
            observed = h.run_converter(w, r, b)
            decoded = Decoded()
            lib.mu_social_item_convert(C.byref(wire), C.byref(c), C.byref(decoded))
            skip = {
                "level",
                "skill_bit",
                "luck_bit",
                "add_rank",
                "skill",
                "artifact_count",
                "artifact",
                "guardian_base",
                "guardian_keys",
                "prefix_count",
                "prefix",
            }
            fields = [n for n, _ in Decoded._fields_ if n not in skip]
            check(
                "item_categories",
                {n: observed["item"][n] for n in fields},
                {n: value(getattr(decoded, n)) for n in fields},
            )
            check(
                "artifact_requests",
                observed["artifact_calls"],
                [list(x) for x in decoded.artifact[: decoded.artifact_count]],
            )
            # Request keys include unfiltered ff; successful table rows/strings are external.
            attempted = (
                [
                    ["option", decoded.guardian_base, x]
                    for x in decoded.guardian_keys[:4]
                ]
                + [["bonus", decoded.guardian_base, decoded.guardian_keys[4]]]
                if c.kind_a == 0x14 and c.grade not in (2, 3) and wire.code <= 0x2C00
                else []
            )
            check("guardian_requests", observed["guardian_lookups"], attempted)
            state = guest.ItemState(
                wire.code,
                wire.level_word,
                wire.durability,
                decoded.ancient,
                c.excellent_resolved,
                decoded.period,
                decoded.expired,
            )
            prefix = h.run_prefix(
                state, r, wire.level_word, wire.excellent, wire.ancient
            )["item"]
            check(
                "item_prefix",
                [prefix["add_rank"], prefix["skill"], prefix["prefix"]],
                [
                    decoded.add_rank,
                    decoded.skill,
                    [[x.id, x.value] for x in decoded.prefix[: decoded.prefix_count]],
                ],
            )
            advanced = h.run_advanced(state, r, k % 2, b)
            check(
                "advanced_eligibility",
                [advanced["eligible"], advanced["group"]],
                [
                    lib.mu_social_item_advanced_eligible(
                        C.byref(wire), C.byref(c), k % 2
                    ),
                    lib.mu_social_item_advanced_group(C.byref(wire), C.byref(c)),
                ],
            )
            banned = h.run_tradeban(state, r, b)
            check(
                "trade_ban",
                banned["banned"],
                lib.mu_social_item_trade_banned(C.byref(wire), C.byref(c)),
            )
    return reports
