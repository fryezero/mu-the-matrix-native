"""Production C binding for the whole ccc993 semantic boundary.

The standalone JSON-lines mode is consumed by the original-instruction runner.
All formula values and table availability are explicit synthetic inputs.
"""

import ctypes as C
import json
from pathlib import Path
import sys


I = C.c_int32


class Context(C.Structure):
    _fields_ = (
        [
            (n, I)
            for n in (
                "kind_a",
                "kind_b",
                "grade",
                "skill",
                "base_level",
                "normalized_slot",
            )
        ]
        + [("slot_flags", I * 4)]
        + [
            (n, I)
            for n in (
                "excellent_resolved",
                "can_trade",
                "capability",
                "character_option",
                "character_status",
            )
        ]
    )


class Option(C.Structure):
    _fields_ = [("id", I), ("value", I)]


class Finalized(C.Structure):
    _fields_ = (
        [("count", I), ("options", Option * 8)]
        + [(n, I) for n in ("rank", "skill", "excellent")]
        + [("slots", I * 9)]
        + [(n, I) for n in ("family", "category", "special_count")]
        + [
            ("special", (I * 3) * 5),
            ("bonus_count", I),
            ("bonus", (I * 3) * 3),
            ("unresolved", I),
        ]
    )


FORMULA = C.CFUNCTYPE(I, C.c_void_p, I, I, I, I, C.POINTER(C.c_double))
ROW = C.CFUNCTYPE(I, C.c_void_p, I, I, I, I)


class Environment(C.Structure):
    _fields_ = (
        [("context", C.c_void_p), ("formula", FORMULA), ("excellent_row", ROW)]
        + [
            (n, I)
            for n in (
                "level_word",
                "ancient",
                "enabled",
                "class_byte",
                "character_stat",
                "state_level",
                "special_tag",
                "special_row",
                "special_enabled",
            )
        ]
        + [("special_bonus", I * 3), ("special_lows", I * 3), ("state_known", I)]
    )


def compare_case(lib, c):
    from validate_social2 import Wire

    w = Wire()
    w.code = c["code"]
    w.level_word = c["L"]
    w.excellent = c["E"]
    w.ancient = c["N"]
    context = Context()
    context.kind_a = c["a"]
    context.kind_b = c["b"]
    context.grade = c["g"]
    context.skill = c["record_skill"]
    state = Finalized()
    state.skill = c["skill_initial"]
    state.excellent = c["excellent_initial"]
    state.family, state.category = c["cache"]
    state.slots[:] = c["ex_initial"]
    state.slots[6:9] = c["extra"]
    formulas = []
    requests = []

    @FORMULA
    def formula(_, family, index, a, b, out):
        formulas.append([family, index, a, b])
        out[0] = ((family * 13 + index * 7 + a * 3 - b * 5) % 101 - 50) / 4 + 0.125
        return 1

    @ROW
    def row(_, family, category, ident, slot):
        requests.append([ident, slot])
        present = (
            c.get("present_common", c["present"])
            if family == 1
            else c.get("present_wing", c["present"]) if family == 2 else []
        )
        return ident in present

    env = Environment()
    env.state_known = 1
    env.formula = formula
    env.excellent_row = row
    for field, key in [
        ("level_word", "level_word"),
        ("ancient", "ancient"),
        ("enabled", "enabled"),
        ("class_byte", "class_byte"),
        ("character_stat", "char_stat"),
        ("state_level", "special_level"),
        ("special_tag", "special_tag"),
        ("special_row", "special_row"),
        ("special_enabled", "special_enabled"),
    ]:
        setattr(env, field, c[key])
    env.special_bonus[:] = c["special_bonus"]
    env.special_lows[:] = c["special_lows"]
    lib.mu_social_item_finalize.argtypes = [
        C.POINTER(Wire),
        C.POINTER(Context),
        C.POINTER(Environment),
        C.POINTER(Finalized),
    ]
    lib.mu_social_item_finalize(
        C.byref(w), C.byref(context), C.byref(env), C.byref(state)
    )
    return {
        "options": [[x.id, x.value] for x in state.options[: state.count]],
        "rank": state.rank,
        "skill": state.skill,
        "excellent": state.excellent,
        "ex": list(state.slots),
        "cache": [state.family, state.category],
        "requests": requests,
        "formulas": formulas,
        "special_decoded": [list(x) for x in state.special[: state.special_count]],
        "special_bonus": [list(x) for x in state.bonus[: state.bonus_count]],
    }


def compare_value(
    lib, category, ident, value_type, base, level_word, record_level, hero_level
):
    trace = []

    @FORMULA
    def formula(_, family, index, a, b, out):
        trace.append([family, index, a, b])
        out[0] = ((family * 13 + index * 7 + a * 3 - b * 5) % 101 - 50) / 4 + 0.125
        return 1

    env = Environment()
    env.state_known = 1
    env.formula = formula
    lib.mu_social_item_excellent_value.argtypes = [
        I,
        I,
        I,
        I,
        I,
        I,
        I,
        C.POINTER(Environment),
        C.POINTER(C.c_double),
    ]
    value = C.c_double()
    assert lib.mu_social_item_excellent_value(
        category,
        ident,
        value_type,
        base,
        level_word,
        record_level,
        hero_level,
        C.byref(env),
        C.byref(value),
    )
    return value.value, trace


def main():
    lib = C.CDLL(
        sys.argv[1]
        if len(sys.argv) > 1
        else str(
            Path(__file__).resolve().parents[1] / "reconstructed/social/libsocial.dylib"
        )
    )
    for line in sys.stdin:
        c = json.loads(line)
        print(json.dumps(compare_case(lib, c)), flush=True)


if __name__ == "__main__":
    main()
