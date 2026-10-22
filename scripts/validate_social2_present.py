"""Compiled production option presenters versus bounded original consumers.

Table lookup, formula varargs and typed formatting arguments are compared before
host CRT/string models. All fixture tables below are authored synthetic rows.
"""

import ctypes as C
import itertools
import math
from pathlib import Path
import struct
import subprocess
import tempfile
from validate_social2_formula import Arg
from validate_social2_present_guest import PresenterOracle
from validate_social2_present_extra_guest import (
    OriginalPresenterOracle,
    synthetic_tables,
    c_rows,
)
from validate_social2_present_cases import cases as extra_cases

ROOT = Path(__file__).resolve().parents[1]
I = C.c_int32
P = C.POINTER(I)
FORM = C.CFUNCTYPE(C.c_int, C.c_void_p, I, I, P, C.c_size_t, C.POINTER(C.c_double))
LOOK = C.CFUNCTYPE(C.c_int, C.c_void_p, I, I, I, P)


class Env(C.Structure):
    _fields_ = [("context", C.c_void_p), ("formula", FORM)]


class Args(C.Structure):
    _fields_ = [
        ("mode", I),
        ("count", I),
        ("global_text", I * 2),
        ("kind", I * 3),
        ("integer", I * 3),
        ("real", C.c_double * 3),
    ]


class Guardian(C.Structure):
    _fields_ = [
        (n, I) for n in ("id", "index", "auxiliary", "name_key", "name_present")
    ]


class ArtifactRow(C.Structure):
    _fields_ = [
        ("selector", I),
        ("text_id", I),
        ("pairs", (I * 2) * 10),
        ("tail", I * 5),
        ("name", C.c_char_p),
    ]


class ArtifactOption(C.Structure):
    _fields_ = [
        ("selector", I),
        ("text_id", I),
        ("pairs", (I * 2) * 10),
        ("formula_index", I),
        ("threshold", I),
        ("divisor", I),
    ]


class ArtifactEntry(C.Structure):
    _fields_ = [
        (n, I)
        for n in (
            "selector",
            "text_id",
            "display_value",
            "threshold_flag",
            "raw_value",
            "position",
            "position_percent",
        )
    ]


class Errtel(C.Structure):
    _fields_ = [(n, I) for n in ("physical", "ordinal", "level", "option")]


def bind(lib):
    lib.mu_social_guardian_construct.argtypes = [
        I,
        C.c_void_p,
        I,
        LOOK,
        C.c_void_p,
        C.POINTER(Guardian),
        P,
        C.POINTER(Guardian),
        P,
    ]
    lib.mu_social_guardian_present.argtypes = [
        I,
        I,
        I,
        I,
        I,
        C.POINTER(Env),
        C.POINTER(Args),
    ]
    lib.mu_social_artifact_construct.argtypes = [
        C.POINTER(ArtifactOption),
        I,
        I,
        I,
        C.POINTER(Env),
        C.POINTER(ArtifactEntry),
    ]
    lib.mu_social_artifact_present.argtypes = [
        C.POINTER(ArtifactEntry),
        I,
        I,
        C.POINTER(Args),
    ]
    lib.mu_social_earring_present.argtypes = [
        I,
        I,
        I,
        I,
        I,
        I,
        I,
        C.POINTER(Env),
        C.POINTER(Args),
    ]
    lib.mu_social_pentagram_present.argtypes = [I, P, C.POINTER(Env), C.POINTER(Args)]
    lib.mu_social_errtel_plan.argtypes = [I, C.c_void_p, I, C.POINTER(Errtel)]
    lib.mu_social_errtel_request.argtypes = [C.c_uint8, I, P]
    lib.mu_social_errtel_present.argtypes = [P, I, C.POINTER(Args)]
    lib.mu_social_advanced_present.argtypes = [I, I, C.POINTER(Args)]
    lib.mu_social_advanced_threshold.argtypes = [P, I]
    lib.mu_social_present_literal.argtypes = [
        C.c_void_p,
        C.c_size_t,
        C.c_char_p,
        I,
        I,
        I,
    ]
    lib.mu_social_formula_evaluate.argtypes = [
        C.c_char_p,
        C.POINTER(Arg),
        C.c_size_t,
        C.POINTER(C.c_double),
    ]


class Tables:
    """Exercise the production strict typed-row loader and exact composite getter."""

    def __init__(self, path):
        sources = [
            "native/core/mu_social_item_tables.c",
            "native/core/mu_data.c",
            "native/core/mu_lang.c",
            "reconstructed/items/item_sets.c",
            "reconstructed/social/item_formula.c",
            "reconstructed/data/data_tables.c",
            "reconstructed/data/data_codec.c",
            "reconstructed/data/item_attributes.c",
            "reconstructed/data/table_layouts.c",
        ]
        subprocess.run(
            [
                "clang",
                "-shared",
                "-fPIC",
                "-std=c11",
                "-O2",
                *[str(ROOT / s) for s in sources],
                "-o",
                str(path),
            ],
            check=True,
            capture_output=True,
        )
        self.lib = C.CDLL(str(path))
        l = self.lib
        l.mu_social_item_tables_load.argtypes = [C.c_char_p, C.c_char_p, C.c_void_p]
        l.mu_social_item_tables_load.restype = C.c_void_p
        l.mu_social_item_tables_free.argtypes = [C.c_void_p]
        l.mu_social_option_find.argtypes = [
            C.c_void_p,
            C.c_char_p,
            P,
            C.c_size_t,
            P,
            C.POINTER(C.c_char_p),
        ]
        l.mu_social_guardian_lookup_row.argtypes = [C.c_void_p, I, I, I, P]
        l.mu_social_artifact_get.argtypes = [C.c_void_p, I, C.POINTER(ArtifactRow)]
        self.tmp = Path(path).parent
        self.handle = None

    def load(self, rows):
        if self.handle:
            self.lib.mu_social_item_tables_free(self.handle)

        def esc(s):
            return (
                s.replace("\\", "\\\\")
                .replace("\t", "\\t")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
            )

        (self.tmp / "social-options.tsv").write_text(
            "".join(
                "\t".join([kind, *map(str, values), esc(text)]) + "\n"
                for kind, values, text in rows
            ),
            encoding="latin1",
        )
        self.handle = self.lib.mu_social_item_tables_load(
            None, str(self.tmp).encode(), None
        )
        if not self.handle:
            raise MemoryError("table fixture allocation")

    def find(self, kind, *keys):
        out = (I * 40)()
        text = C.c_char_p()
        n = self.lib.mu_social_option_find(
            self.handle,
            kind.encode(),
            (I * len(keys))(*keys),
            len(keys),
            out,
            C.byref(text),
        )
        return (
            (
                list(out[:n]),
                text.value.decode("latin1") if text.value is not None else None,
            )
            if n
            else (None, None)
        )

    def close(self):
        if self.handle:
            self.lib.mu_social_item_tables_free(self.handle)
            self.handle = None


def run(lib, text, data, cases=500):
    bind(lib)
    reports = {}

    def check(f, a, b):
        r = reports.setdefault(f, dict(cases=0, mismatches=0))
        r["cases"] += 1
        if a != b:
            r["mismatches"] += 1
            r.setdefault("first", dict(client=repr(a), native=repr(b)))

    def bits(v):
        return "nan" if math.isnan(v) else struct.pack("<d", v).hex()

    def typed(a):
        return [
            ("f64", bits(a.real[i])) if a.kind[i] == 1 else ("i32", a.integer[i])
            for i in range(a.count)
        ]

    def literal(name, value, prefix=False, percents=0):
        out = C.create_string_buffer(256)
        lib.mu_social_present_literal(
            out, 256, name.encode("latin1"), value, int(prefix), percents
        )
        return out.value.decode("latin1")

    calls = []
    returns = []
    formula_rows = {}

    @FORM
    def formula(user, family, index, args, count, out):
        values = list(args[:count])
        calls.append(dict(family=family, index=index, args=values))
        if returns:
            out[0] = returns.pop(0)
            return 1
        pattern = formula_rows.get((family, index))
        av = (Arg * count)(*[Arg(0, v, 0) for v in values])
        return int(
            lib.mu_social_formula_evaluate(
                pattern.encode() if pattern is not None else None, av, count, out
            )
            > 0
        )

    env = Env(None, formula)
    with tempfile.TemporaryDirectory() as tmp:
        t = Tables(Path(tmp) / "tables.dylib")
        m = PresenterOracle(text, data)
        # Exact Guardian constructor key order, duplicate selectors and 0xff.
        for base, sels, enabled, mode in itertools.product(
            [0, 1, 65535], [[9, 4, 9, 255, 11], [255] * 5, [4] * 5], [0, 1], range(3)
        ):
            values = {
                (9, base): dict(id=2, index=77, aux=-17),
                (255, base): dict(id=1001, index=-1, aux=123),
                (4, base + 1): dict(id=4, index=99, aux=66),
            }
            names = (
                {}
                if mode == 2
                else {
                    9: dict(template="A%d/%.9f" if mode == 0 else ""),
                    255: dict(template="SPECIAL"),
                }
            )
            bonuses = {(11, base): dict(pairs=[(4, 77, 123), (-1, -99, -777)])}
            bn = {4: dict(template="B%d"), -1: dict(template="")}
            rows = [
                ("guardian_value", [k, b, v["id"], v["index"], 0, v["aux"]], "")
                for (k, b), v in values.items()
            ]
            rows += [("guardian_name", [k], v["template"]) for k, v in names.items()]
            rows += [
                ("guardian_bonus", [k, b, k, *[x for p in v["pairs"] for x in p]], "")
                for (k, b), v in bonuses.items()
            ]
            rows += [("guardian_bonus_name", [k], v["template"]) for k, v in bn.items()]
            t.load(rows)
            original = m.guardian_construct(
                base, sels, values, names, bonuses, bn, enabled=bool(enabled)
            )
            lookups = []

            @LOOK
            def lookup(user, kind, key, base, out):
                ret = t.lib.mu_social_guardian_lookup_row(
                    t.handle, kind, key, base, out
                )
                lookups.append(
                    dict(
                        table=[
                            "guardian_values",
                            "guardian_names",
                            "guardian_bonus_values",
                            "guardian_bonus_names",
                        ][kind],
                        key=[key, base] if kind in (0, 2) else [key],
                        present=bool(ret),
                    )
                )
                return ret

            ordinary = (Guardian * 4)()
            bonus = (Guardian * 2)()
            n = I()
            nb = I()
            lib.mu_social_guardian_construct(
                base,
                (C.c_uint8 * 5)(*sels),
                enabled,
                lookup,
                None,
                ordinary,
                C.byref(n),
                bonus,
                C.byref(nb),
            )

            def entries(entries, n, b):
                result = []
                for e in entries[:n]:
                    _, name = t.find(
                        "guardian_bonus_name" if b else "guardian_name", e.name_key
                    )
                    row = dict(
                        id=e.id,
                        index=e.index,
                        template=name or "",
                        template_present=bool(e.name_present),
                        template_key=e.name_key,
                    )
                    if not b:
                        row["aux"] = e.auxiliary
                    result.append(row)
                return result

            check(
                "guardian_constructor",
                (original["ordinary"], original["bonus"], original["lookups"]),
                (
                    entries(ordinary, n.value, False),
                    entries(bonus, nb.value, True),
                    lookups,
                ),
            )
        # Typed original printf arguments, including FSTP binary32 rounding.
        floats = [
            -17.875,
            -0.0,
            0.99,
            1.234567891,
            16777217.0,
            2147483647.75,
            2147483648.0,
            -2147483649.0,
            float("inf"),
            float("nan"),
        ]
        for bonus, id, L, value in itertools.product(
            [0, 1],
            [-1, 0, 1, 2, 3, 4, 5, 1000, 1001],
            [0, 8, 0x80000038, 0xFFFFFFFF],
            floats,
        ):
            row = dict(
                id=id,
                index=77,
                aux=-37,
                template="A%d/%.9f" if not bonus and id in (2, 3) else "I%d",
                template_key=201,
            )
            active = bonus and id != -1 or not bonus and 0 <= id <= 4
            original = m.guardian_present(
                L,
                [] if bonus else [row],
                [row] if bonus else [],
                [value] if active else [],
                {
                    0x15A6: "SPECIAL",
                    0x1654: "EXTRA",
                    0x15A7: "ABSENT",
                    0xC34: "FOOTER",
                    0x1573: "BONUS",
                },
            )
            calls.clear()
            returns[:] = [value] if active else []
            args = Args()
            ret = lib.mu_social_guardian_present(
                bonus, id, 77, -37, I(L).value, C.byref(env), C.byref(args)
            )
            actualformats = [
                f
                for f in original["formats"]
                if f["format"]["table"] in ("guardian_names", "guardian_bonus_names")
            ]
            actualargs = [
                (a["type"], bits(a["value"]) if a["type"] == "f64" else a["value"])
                for f in actualformats
                for a in f["args"]
            ]
            expectedcalls = [
                {k: f[k] for k in ("family", "index", "args")}
                for f in original["formulas"]
            ]
            actualglobals = [
                f["format"]["key"][0]
                for f in original["formats"]
                if f["format"]["table"] == "global_text"
                and f["format"]["key"][0] in (0x15A6, 0x1654, 0x15A7)
            ]
            check(
                "guardian_presenter",
                (expectedcalls, actualargs, actualglobals),
                (
                    calls,
                    typed(args) if args.mode == 1 and ret > 0 else [],
                    list(args.global_text[: args.count]) if args.mode == 2 else [],
                ),
            )
        # Artifact construction and text-ID formatting; first duplicate pair wins.
        for raw, level, divisor in itertools.product(
            [-5, 0, 1, 3, 7, 2147483647], [-1, 0, 1, 15], [-3, 1, 10]
        ):
            row = dict(
                text_id=201,
                pairs=[(j // 2, j * 9) for j in range(10)],
                formula_index=88,
                threshold=3,
                divisor=divisor,
            )
            original = m.artifact_construct(
                7, raw, level, {7: row}, [17.875] if level > 0 else []
            )
            t.load(
                [
                    (
                        "artifact",
                        [
                            7,
                            201,
                            *[x for pair in row["pairs"] for x in pair],
                            0,
                            88,
                            0,
                            3,
                            divisor,
                        ],
                        "",
                    )
                ]
            )
            selected = ArtifactRow()
            found = t.lib.mu_social_artifact_get(t.handle, 7, C.byref(selected))
            native = ArtifactOption(
                selector=selected.selector,
                text_id=selected.text_id,
                formula_index=selected.tail[1],
                threshold=selected.tail[3],
                divisor=selected.tail[4],
            )
            for i, pair in enumerate(selected.pairs):
                native.pairs[i][:] = pair
            check(
                "artifact_selection",
                (original["lookups"][0]["key"], original["lookups"][0]["present"]),
                ([7], bool(found)),
            )
            calls.clear()
            returns[:] = [17.875] if level > 0 else []
            entry = ArtifactEntry()
            ret = lib.mu_social_artifact_construct(
                C.byref(native), 7, raw, level, C.byref(env), C.byref(entry)
            )
            check(
                "artifact_constructor",
                (
                    original["entries"],
                    [
                        {k: f[k] for k in ("family", "index", "args")}
                        for f in original["formulas"]
                    ],
                ),
                (
                    [{n: getattr(entry, n) for n, _ in entry._fields_}] if ret else [],
                    calls,
                ),
            )
            for present, fmt in itertools.product([0, 1], [-1, 0, 1, 2, 3]):
                er = original["entries"][0]
                texts = (
                    {201: dict(template="Artifact%literal", format=fmt)}
                    if present
                    else {}
                )
                originalformat = m.artifact_format(er, texts, {0x19F8: "R%d[%s]"})
                args = Args()
                ret = lib.mu_social_artifact_present(
                    C.byref(entry), present, fmt, C.byref(args)
                )
                core = (
                    ""
                    if not ret or not args.count
                    else (
                        "Artifact%literal"
                        if args.count == 1
                        else literal(
                            "Artifact%literal", args.integer[1], percents=int(fmt == 2)
                        )
                    )
                )
                rendered = (
                    ("R%d[%s]" % (args.global_text[1], core))
                    if args.global_text[0]
                    else core
                )
                check("artifact_presenter", originalformat["text"], rendered)
        # Remaining original consumers use the real C table loader for row/key selection.
        extra = synthetic_tables()
        t.load(c_rows(extra))
        oracle = OriginalPresenterOracle(text, data, extra)
        formula_rows = {(x["group"], x["index"]): x["expr"] for x in extra["formulas"]}
        returns.clear()
        for kind, c in extra_cases():
            original = oracle.run_case(kind, **c)
            calls.clear()
            args = Args()
            selection = []
            state = "present"
            native = {}

            def find(kind, *keys):
                v, name = t.find(kind, *keys)
                selection.append((kind, list(keys), v is not None))
                return v, name

            if kind.startswith("earring"):
                oid, tag, selector = (c[n] & 255 for n in ("option", "tag", "selector"))
                name_row, name = find("earring_name", oid)
                tag_row, _ = find("earring_value", tag)
                row, _ = (
                    find("earring_value", tag, selector) if tag_row else (None, None)
                )
                state = (
                    "missing_option"
                    if not name_row
                    else (
                        "missing_tag"
                        if not tag_row
                        else "selector_out_of_range" if row is None else "present"
                    )
                )
                expectedkeys = [("earring_name", [oid]), ("earring_value", [tag])]
                actualkeys = [
                    (
                        (
                            "earring_name"
                            if q["table"] == "earring_option"
                            else "earring_value"
                        ),
                        [q["key"]],
                    )
                    for q in original["selection"][:2]
                ]
                check(
                    "earring_selection",
                    (original["row_state"], actualkeys),
                    (state, expectedkeys),
                )
                if kind == "earring_numeric":
                    check(
                        "earring_numeric",
                        original["numeric"],
                        row[2:5] if state == "present" else [0, 0, 0],
                    )
                    continue
                if state in ("missing_option", "missing_tag"):
                    rendered = ""
                else:
                    ret = lib.mu_social_earring_present(
                        oid,
                        name_row[1],
                        row[3] if row else 0,
                        int(row is not None),
                        c.get("enhancement_level", 0),
                        int(
                            c.get("other_full_l") is not None and not c.get("self_only")
                        ),
                        ((c.get("other_full_l") or 0) >> 3) & 15,
                        C.byref(env),
                        C.byref(args),
                    )
                    rendered = (
                        literal(
                            name,
                            args.integer[1],
                            prefix=args.count == 1,
                            percents=2 if name_row[1] == 2 and args.count == 2 else 0,
                        )
                        if ret > 0
                        else None
                    )
                check(
                    "earring_presenter",
                    (
                        original["text"],
                        [
                            {k: f[k] for k in ("family", "index", "args")}
                            for f in original["formula_calls"]
                        ],
                    ),
                    (rendered, calls),
                )
            elif kind == "errtel_text":
                row, name = find("jewel", c["code"], c["physical_rank"], c["option"])
                ret = 0
                if (c["level"] & 0xFFFFFFFF) < 11 and row:
                    ret = lib.mu_social_errtel_present(
                        (I * 11)(*row[6:17]), c["level"], C.byref(args)
                    )
                observed = [f["args"] for f in original["formats"]]
                check(
                    "errtel_presenter",
                    (original["success"], observed),
                    (ret, [[args.integer[0]]] if ret else []),
                )
            elif kind == "standalone_errtel":
                plan = (Errtel * 5)()
                n = lib.mu_social_errtel_plan(
                    c["socket_count"], (C.c_uint8 * 5)(*c["slots"]), 0, plan
                )
                enabled = 1 <= c["socket_count"] <= 5
                expected = [
                    (q["key"][1], q["level"], q["key"][2])
                    for q in original["selection"]
                    if q["table"] == "jewel_values"
                ]
                actual = [(p.physical, p.level, p.option) for p in plan[:n]]
                check(
                    "errtel_plan",
                    (expected, original["next_line"], original["global_line_count"]),
                    (
                        actual,
                        c.get("line", 0) + (1 + 2 * n if enabled else 0),
                        1 + n if enabled else 0,
                    ),
                )
            elif kind == "pentagram_rank":
                ret = lib.mu_social_pentagram_present(
                    c["required_level"],
                    (I * 4)(c["type"], c["level"], c["defense_flag"], 0),
                    C.byref(env),
                    C.byref(args),
                )
                observed = original["formats"][0]
                check(
                    "pentagram_presenter",
                    (
                        [
                            {k: f[k] for k in ("family", "index", "args")}
                            for f in original["formula_calls"]
                        ],
                        observed["template"][1],
                        observed["args"],
                    ),
                    (
                        calls,
                        args.global_text[0],
                        (
                            [
                                extra["globaltext"].get(args.integer[0], ""),
                                args.integer[1],
                                args.integer[2],
                            ]
                            if ret > 0
                            else []
                        ),
                    ),
                )
            else:
                row, name = find("advanced", c["group"], c["option"])
                state = "present" if row else "missing_row"
                check("advanced_selection", original["row_state"], state)
                if kind == "advanced_threshold":
                    check(
                        "advanced_threshold",
                        original["threshold"],
                        (
                            lib.mu_social_advanced_threshold(
                                (I * 4)(*row[2:6]), c["value"]
                            )
                            if row
                            else 0
                        ),
                    )
                else:
                    ret = (
                        lib.mu_social_advanced_present(
                            row[6], c["value"], C.byref(args)
                        )
                        if row
                        else 0
                    )
                    check(
                        "advanced_presenter",
                        original["text"],
                        (
                            literal(name, args.integer[1], percents=args.global_text[0])
                            if ret
                            else ""
                        ),
                    )
        t.close()
    return reports
