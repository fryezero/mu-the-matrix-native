"""Native formula parser versus original tokenizer/shunting/evaluation bodies.

Original CRT/string/container functions are named models in the guest adapter.
Optional installed rows are read through the existing verified data decoder.
"""

import ctypes as C
import hashlib
import math
from pathlib import Path
import random
import re
import struct
import subprocess
import validate_data_tables as tables
from validate_social2_formula_guest import FormulaMachine


class Arg(C.Structure):
    _fields_ = [("kind", C.c_int), ("integer", C.c_int), ("real", C.c_double)]


def installed(path):
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        ["make", "-C", str(root / "reconstructed/data")],
        check=True,
        capture_output=True,
    )
    lib = tables.Library(root / "reconstructed/data/libdatatables.dylib")
    raw = path.read_bytes()
    spec = lib.dll.mu_data_find(b"formuladata.bmd")
    status, result, units, data = lib.decode(spec, raw)
    if status:
        raise ValueError("FormulaData did not decode successfully")
    rows = []
    at = 8
    for _ in range(struct.unpack_from("<I", data, 4)[0]):
        group, n = struct.unpack_from("<II", data, at)
        at += 8
        for _ in range(n):
            index = struct.unpack_from("<i", data, at)[0]
            expression = data[at + 4 : at + 260].split(b"\0", 1)[0].decode("ascii")
            rows.append({"group": group, "index": index, "expr": expression})
            at += 260
    return rows, hashlib.sha256(raw).hexdigest()


def run(lib, text, data, cases, game_root=None):
    rows = []
    digest = None
    if game_root:
        rows, digest = installed(game_root / "Data/Local/formuladata.bmd")
    guest = FormulaMachine(text, data, rows)
    lib.mu_social_formula_evaluate.argtypes = [
        C.c_char_p,
        C.POINTER(Arg),
        C.c_size_t,
        C.POINTER(C.c_double),
    ]
    report = {
        "cases": 0,
        "mismatches": 0,
        "crt_boundary": "host atof, pow, printf and ten-significant-digit decimal conversion",
    }
    if digest:
        report["formula_file_sha256"] = digest

    def check(family, index, pattern, values):
        args = (Arg * len(values))()
        words = []
        for k, (kind, value) in enumerate(values):
            args[k].kind = kind
            if kind:
                args[k].real = value
                words.extend(struct.unpack("<II", struct.pack("<d", value)))
            else:
                args[k].integer = value
                words.append(value & 0xFFFFFFFF)
        actual = guest.eval(family, index, words)
        result = C.c_double()
        status = lib.mu_social_formula_evaluate(
            pattern.encode() if pattern is not None else None,
            args,
            len(values),
            C.byref(result),
        )
        same = (math.isnan(actual) and math.isnan(result.value)) or struct.pack(
            "<d", actual
        ) == struct.pack("<d", result.value)
        report["cases"] += 1
        if status <= 0 or not same:
            report["mismatches"] += 1
            report.setdefault(
                "first",
                {
                    "family": family,
                    "index": index,
                    "arguments": values,
                    "client": actual,
                    "native": result.value,
                    "status": status,
                },
            )

    for row in rows:
        if row["group"] not in (1, 2, 8, 9, 11, 16) or not row["expr"]:
            continue
        for base in (1, 7, 15, 127, 400, 1200):
            values = [
                (int(fmt == "f"), base + i + (0.25 if fmt == "f" else 0))
                for i, fmt in enumerate(re.findall("%([df])", row["expr"]))
            ]
            check(row["group"], row["index"], row["expr"], values)
    directed = [
        "2+3*4",
        "8/2^2",
        "2^3^2",
        "1/3*3",
        "-(2+3)",
        "2*-3",
        "2--3",
        "2 3",
        "0.123456789123+0",
        "1/0",
        "0/0",
        "2*-(2+3)",
        "(-2)",
        "2^(-2)",
        "1++2",
    ]
    rng = random.Random(0x501A)

    def expression(depth=0):
        if depth >= 2 or rng.randrange(4) == 0:
            return str(rng.randrange(1, 20))
        return (
            "("
            + expression(depth + 1)
            + rng.choice("+-*/")
            + expression(depth + 1)
            + ")"
        )

    for i in range(cases):
        pattern = directed[i] if i < len(directed) else expression()
        guest.rows[(998, i)] = pattern
        check(998, i, pattern, [])
    for family, index in ((9999, 1), (11, 9999), (-1, -1)):
        check(family, index, None, [])
    return {"formula_evaluation": report}
