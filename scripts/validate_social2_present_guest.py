"""Bounded original-instruction presenter oracle. No captured bytes embedded.

Import from any working directory. The validator supplies hash-pinned captures. String and CRT operations are modeled. Public methods return ordinary dicts for
a parent-owned ctypes/JSON comparison against the production C presenter.
Table keys are signed integers, Guardian value keys are (selector, base_level).
formula_returns=None runs the original evaluator over formula_rows; a sequence
or callback supplies doubles at the evaluator boundary and records the real ABI.
"""

import collections, hashlib, math, re, struct
from validate_social2_formula_guest import FormulaMachine, cm, cstring, s32, H, HV
from unicorn import UC_HOOK_CODE, UC_PROT_ALL
from unicorn.x86_const import (
    UC_X86_REG_EBP,
    UC_X86_REG_ESP,
    UC_X86_REG_EIP,
    UC_X86_REG_FPCW,
    UC_X86_REG_FPSW,
    UC_X86_REG_FPTAG,
    UC_X86_REG_MXCSR,
)

RANGES = [
    (0xF097E1, 0xF0999E),
    (0xF0D812, 0xF0DC23),
    (0x9627BE, 0x962888),
    (0x10C9C2D, 0x10C9C7E),
    (0x962E2F, 0x962F9B),
    (0xF0DC38, 0xF0DD5A),
    (0x995231, 0x995246),
    (0x191C5E0, 0x191C6A0),
]
LINE_BASE, COLOR_BASE = 0x10C76988, 0x10C7B938
API_VERSION = 1
# Return addresses, types of ALL supplied variadic arguments, independent of
# whether a synthetic/localized template consumes those arguments.
PRINTF_ARGS = {
    0xF0D910: ("i32",),
    0xF0D977: ("i32", "f64"),
    0xF0D9A8: (),
    0xF0D9D5: (),
    0xF0DA00: (),
    0xF0DA3B: (),
    0xF0DA6D: (),
    0xF0DAFB: (),
    0xF0DB61: ("i32",),
    0xF0DB95: (),
    0xF0DBC7: (),
    0xF0DC0C: (),
    0x962EC3: ("str",),
    0x962EEB: ("str", "i32"),
    0x962F13: ("str", "i32"),
    0x962F5E: ("i32", "str"),
    0xF0DC86: (),
    0xF0DD08: (),
}


class PresenterOracle(FormulaMachine):
    """Reusable serial oracle. Tables/strings are synthetic caller-owned inputs.

    Guardian ordinary row: id,index,aux and optional unused.
    Guardian bonus row: pairs of (id,index,unused), exactly two.
    Name row: template, optional id; artifact names also require format.
    Artifact value row: text_id,pairs (10 pairs),formula_index,threshold,divisor.
    Missing map key means absent; a present template='' remains present-empty.
    """

    def __init__(self, text, data, formula_rows=None):
        self.formula_table_known = formula_rows is not None
        super().__init__(
            text,
            data,
            [
                {"group": k[0], "index": k[1], "expr": v}
                for k, v in (formula_rows or {}).items()
            ],
        )
        self.allow(*RANGES)
        self.allow(*[(a, a + 1) for a in (0xF0999E, 0xF099F0, 0xF0DC23, 0xF0DD5A)])
        self.uc.mem_map(0x10C76000, 0x15000, UC_PROT_ALL)
        self.mode = ""
        self.table_ptrs = {}
        self.refs = {}
        self.trace = {}
        self.st(0x95FC2E, lambda m: int(m.enabled), 4)
        self.st(0xCCC591, lambda m: m.item_record)
        self.st(0x111454D, lambda m: m.lookup("guardian_values", m.args(2)[::-1]), 8)
        self.st(
            0x1114601, lambda m: m.lookup("guardian_bonus_values", m.args(2)[::-1]), 8
        )
        self.st(0x11144FE, lambda m: m.lookup("guardian_names", m.args(1)), 4)
        self.st(0x11145B2, lambda m: m.lookup("guardian_bonus_names", m.args(1)), 4)
        self.st(0xCA8E45, lambda m: m.new_guardian(False))
        self.st(0xCA8CC1, lambda m: m.new_guardian(True))
        self.st(0xBC7D65, lambda m: 0)
        self.st(0xBC7D50, lambda m: 0)
        self.st(0xCA95BD, lambda m: m.append_guardian(False), 4)
        self.st(0xCA95A6, lambda m: m.append_guardian(True), 4)
        self.st(0x9954E9, lambda m: len(m.ordinary_ptrs))
        self.st(0x99513E, lambda m: m.ordinary_ptrs[m.args(1)[0]], 4)
        self.st(0xF16FB5, lambda m: len(m.bonus_ptrs))
        self.st(0xF15F51, lambda m: m.bonus_ptrs[m.args(1)[0]], 4)
        self.st(0x10C9BDE, lambda m: m.lookup("artifact_values", m.args(1)), 4)
        self.st(0x10C9B8F, lambda m: m.lookup("artifact_names", m.args(1)), 4)
        self.st(0x962888, lambda m: m.append_artifact(), 4)
        self.st(0x95F027, lambda m: m.global_text(m.args(1)[0]), 4)
        self.st(0x9619DD, lambda m: m.sprintf())
        self.st(0x96BACA, lambda m: m.item)
        self.st(0x97F855, lambda m: m.item)
        self.st(0x96BB93, lambda m: len(m.artifact_ptrs))
        self.st(0x966D46, lambda m: (m.put32(m.args(1)[0], 0) or m.args(1)[0]), 4)
        self.st(0x966DAB, lambda m: int(m.u32(m.this()) < len(m.artifact_ptrs)))
        self.st(0x966C33, lambda m: m.artifact_ptrs[m.u32(m.this())])
        self.st(0x966ADB, lambda m: m.this())
        self.st(
            0x966DC6, lambda m: (m.put32(m.this(), m.u32(m.this()) + 1) or m.this())
        )
        self.uc.hook_add(
            UC_HOOK_CODE, self.formula_seen, begin=0x117B5EB, end=0x117B5EB
        )
        for end in (0xF0999E, 0xF099F0, 0xF0DC23, 0xF0DD5A):
            self.uc.hook_add(
                UC_HOOK_CODE,
                lambda u, a, z, d: u.reg_write(UC_X86_REG_EIP, cm.RETURN_SENTINEL),
                begin=end,
                end=end,
            )

    def prepare(self, formula_returns=None, global_text=None):
        self.reset()
        self.vectors, self.stacks, self.savedkey = {}, {}, [0]
        self.formatted, self.postfix = [], []
        self.boundaries = collections.Counter()
        self.trace = {"lookups": [], "formulas": [], "formats": []}
        self.table_ptrs, self.refs = {}, {}
        self.global_rows = global_text or {}
        self.ordinary, self.bonus, self.artifacts = [], [], []
        self.ordinary_ptrs, self.bonus_ptrs, self.artifact_ptrs = [], [], []
        self.formula_returns = formula_returns
        self.formula_cursor = 0
        self.enabled = True
        self.put32(0x300F0004, 0x300F0100)
        self.put32(0xBDCB280, 0)
        self.uc.mem_write(H, b"\xdd\x05" + struct.pack("<I", HV) + b"\xc3")
        for reg, value in [
            (UC_X86_REG_FPCW, 0x27F),
            (UC_X86_REG_FPSW, 0),
            (UC_X86_REG_FPTAG, 0xFFFF),
            (UC_X86_REG_MXCSR, 0x1F80),
        ]:
            self.uc.reg_write(reg, value)
        self.item = self.alloc(0x12C)
        self.write(self.item, b"\0" * 0x12C)
        self.item_record = self.alloc(0x2C4)
        self.write(self.item_record, b"\0" * 0x2C4)
        self.frame = cm.STACK_BASE + 0x8000
        self.write(self.frame - 0x1000, b"\0" * 0x1100)
        self.put32(self.frame + 0x10, self.item)
        self.put32(self.frame - 0x10, 0)
        for i in range(64):
            self.put32(COLOR_BASE + 4 * i, 0xFFFFFFFF)

    def raw(self, text, ref=None):
        b = text.encode("latin1")
        if len(b) >= 255 or b"\0" in b:
            raise ValueError(
                "oracle supports bounded Latin-1 C strings under 255 bytes"
            )
        p = self.alloc(len(b) + 1)
        self.write(p, b + b"\0")
        if ref is not None:
            self.refs[p] = ref
        return p

    def _stub_hit(self, uc, address, size, user):
        entry = self.stubs.get(address)
        if entry is not None and entry[0] == "import":
            self.fail("unmodeled import reached by presenter oracle")
            return
        return super()._stub_hit(uc, address, size, user)

    def name(self, row, ref):
        p = self.alloc(32)
        self.write(p, b"\0" * 32)
        self.put32(p, row.get("id", 0))
        self.sets(p + 4, row["template"])
        self.refs[self.u32(p + 4)] = ref
        self.put32(p + 28, row.get("format", 0))
        return p

    def lookup(self, table, words):
        keys = tuple(map(s32, words))
        key = keys if len(keys) > 1 else keys[0]
        p = self.table_ptrs.get(table, {}).get(key, 0)
        self.trace["lookups"].append(
            {"table": table, "key": list(keys), "present": bool(p)}
        )
        return p

    def global_text(self, key):
        key = s32(key)
        present = key in self.global_rows
        ref = {"table": "global_text", "key": [key], "present": present}
        self.trace["lookups"].append(dict(ref))
        # Explicit text-lookup boundary. Missing and present-empty stay distinct
        # in the request even though this boundary supplies an empty C string.
        return self.raw(self.global_rows.get(key, ""), ref)

    def formula_seen(self, uc, address, size, data):
        _, family, index = self.args(3)
        family, index = s32(family), s32(index)
        count = {8: 1, 11: 4}[family]
        request = {
            "family": family,
            "index": index,
            "args": list(map(s32, self.args(3 + count)[3:])),
            "present": (
                ((family, index) in self.rows)
                if self.formula_table_known or self.formula_returns is None
                else None
            ),
            "source": "instructions" if self.formula_returns is None else "supplied",
        }
        self.trace["formulas"].append(request)
        if self.formula_returns is not None:
            if callable(self.formula_returns):
                value = self.formula_returns(dict(request))
            else:
                if self.formula_cursor >= len(self.formula_returns):
                    raise ValueError("too few supplied formula results")
                value = self.formula_returns[self.formula_cursor]
            self.formula_cursor += 1
            request["return_bits"] = struct.pack("<d", value).hex()
            self.boundaries["supplied_formula_return"] += 1
            self.retfp(value)

    def sprintf(self):
        ret = self.u32(self.uc.reg_read(UC_X86_REG_ESP))
        if ret not in PRINTF_ARGS:
            raise cm.CaseError(f"unclassified printf call {ret:#x}")
        out, fp = self.args(2)
        ap = self.uc.reg_read(UC_X86_REG_ESP) + 12
        args, values = [], []
        for kind in PRINTF_ARGS[ret]:
            n = 8 if kind == "f64" else 4
            raw = self.read(ap, n)
            words = list(struct.unpack("<" + "I" * (n // 4), raw))
            value = (
                struct.unpack("<d", raw)[0]
                if kind == "f64"
                else cstring(self, words[0]) if kind == "str" else s32(words[0])
            )
            arg = {"type": kind, "value": value}
            if kind == "f64":
                arg["bits"] = raw.hex()
            args.append(arg)
            values.append(value)
            ap += n
        fmt = cstring(self, fp)
        # Model only the CRT text operation. Selection and all supplied varargs
        # above came from the original caller, including unused arguments.
        specs = re.findall(r"%(?:[-+ #0]*\d*(?:\.\d+)?)?([diufs%])", fmt)
        consumed = sum(x != "%" for x in specs)
        if consumed > len(values):
            raise ValueError("template consumes unavailable original arguments")
        # The outer Artifact UI call uses already-formatted text as printf's
        # format with zero varargs, including a possible literal percent. Record
        # that actual unsafe call; model its visual copy explicitly, without
        # pretending to establish CRT behavior for a malformed format string.
        literal_copy = ret == 0xF0DD08
        rendered = fmt if literal_copy else fmt % tuple(values[:consumed])
        if len(rendered.encode("latin1")) >= 255:
            raise ValueError("out-of-domain formatted output")
        ref = (
            {"table": "preformatted", "key": [], "present": True}
            if literal_copy
            else self.refs.get(fp, {"table": "fixed", "key": [fp], "present": True})
        )
        event = {
            "call": hex(ret - 5),
            "format": dict(ref),
            "args": args,
            "template": fmt,
            "text": rendered,
        }
        if literal_copy:
            event["text_model"] = "preformatted_copy_original_CRT_unverified"
        if LINE_BASE <= out < LINE_BASE + 64 * 255 and (out - LINE_BASE) % 255 == 0:
            event["line"] = (out - LINE_BASE) // 255
        self.trace["formats"].append(event)
        self.write(out, rendered.encode("latin1") + b"\0")
        return len(rendered)

    def new_guardian(self, bonus):
        p = self.this()
        self.write(p, b"\0" * (32 if bonus else 36))
        self.sets(p + (8 if bonus else 12), "")
        return p

    def append_guardian(self, bonus):
        p = self.args(1)[0]
        table = "guardian_bonus_names" if bonus else "guardian_names"
        last = next(x for x in reversed(self.trace["lookups"]) if x["table"] == table)
        r = {
            "id": s32(self.u32(p)),
            "index": s32(self.u32(p + 4)),
            "template": self.string(p + (8 if bonus else 12)),
            "template_present": last["present"],
            "template_key": last["key"][0],
        }
        if not bonus:
            r["aux"] = s32(self.u32(p + 8))
        (self.bonus if bonus else self.ordinary).append(r)
        return 0

    def append_artifact(self):
        p = self.args(1)[0]
        r = dict(
            zip(
                (
                    "selector",
                    "text_id",
                    "display_value",
                    "raw_value",
                    "position",
                    "position_percent",
                ),
                (s32(self.u32(p + o)) for o in (0, 4, 8, 16, 20, 24)),
            )
        )
        r["threshold_flag"] = self.read(p + 12, 1)[0]
        self.artifacts.append(r)
        return 0

    def slice(self, start):
        self.uc.reg_write(UC_X86_REG_EBP, self.frame)
        self.uc.reg_write(UC_X86_REG_ESP, self.frame - 0x900)
        self.uc.ctl_flush_tb()
        self.uc.emu_start(start, cm.RETURN_SENTINEL, count=500000)
        if self.errors or self.uc.reg_read(UC_X86_REG_EIP) != cm.RETURN_SENTINEL:
            raise cm.CaseError("; ".join(self.errors) or "instruction limit")

    def result(self, **fields):
        if (
            self.formula_returns is not None
            and not callable(self.formula_returns)
            and self.formula_cursor != len(self.formula_returns)
        ):
            raise ValueError("unused supplied formula results")
        return dict(fields, **self.trace)

    def guardian_construct(
        self,
        base_level,
        selectors,
        ordinary_values,
        ordinary_names,
        bonus_values,
        bonus_names,
        enabled=True,
    ):
        if len(selectors) != 5 or any(not 0 <= x <= 255 for x in selectors):
            raise ValueError("five wire selector bytes required")
        self.prepare([])
        self.enabled = enabled
        self.put32(self.frame - 0x10, self.item)
        self.write(self.item_record + 0x254, struct.pack("<H", base_level))
        p = self.alloc(5)
        self.write(p, bytes(selectors))
        self.put32(self.frame + 0x28, p)
        for table, rows in [
            ("guardian_names", ordinary_names),
            ("guardian_bonus_names", bonus_names),
        ]:
            self.table_ptrs[table] = {
                k: self.name(v, {"table": table, "key": [k], "present": True})
                for k, v in rows.items()
            }
        for table, rows in [
            ("guardian_values", ordinary_values),
            ("guardian_bonus_values", bonus_values),
        ]:
            self.table_ptrs[table] = {}
            for (selector, base), row in rows.items():
                words = (
                    [base, selector] + [x for pair in row["pairs"] for x in pair]
                    if table == "guardian_bonus_values"
                    else [
                        base,
                        row["id"],
                        row["index"],
                        row.get("unused", 0),
                        row["aux"],
                    ]
                )
                if len(words) != (8 if table == "guardian_bonus_values" else 5):
                    raise ValueError("Guardian bonus row requires two triples")
                p = self.alloc(4 * len(words))
                self.write(
                    p,
                    struct.pack(
                        "<" + "I" * len(words), *(x & 0xFFFFFFFF for x in words)
                    ),
                )
                self.table_ptrs[table][selector, base] = p
        self.slice(0xF097E1)
        return self.result(ordinary=self.ordinary, bonus=self.bonus)

    def guardian_present(
        self,
        level_word,
        ordinary,
        bonus,
        formula_returns=None,
        global_text=None,
        enabled=True,
        durability=100,
    ):
        if len(ordinary) > 16 or len(bonus) > 16:
            raise ValueError("bounded presenter supports at most 16 entries per vector")
        self.prepare(formula_returns, global_text)
        self.enabled = enabled
        self.put32(self.item + 20, level_word)
        self.write(self.item + 0x38, bytes([durability]))
        for isbonus, rows in [(False, ordinary), (True, bonus)]:
            table = "guardian_bonus_names" if isbonus else "guardian_names"
            for row in rows:
                p = self.alloc(32 if isbonus else 36)
                self.write(p, b"\0" * (32 if isbonus else 36))
                self.put32(p, row["id"])
                self.put32(p + 4, row["index"])
                if not isbonus:
                    self.put32(p + 8, row["aux"])
                self.sets(p + (8 if isbonus else 12), row["template"])
                self.refs[self.u32(p + (8 if isbonus else 12))] = {
                    "table": table,
                    "key": [row.get("template_key", row["id"])],
                    "present": row.get("template_present", True),
                }
                (self.bonus_ptrs if isbonus else self.ordinary_ptrs).append(p)
        self.slice(0xF0D812)
        return self.result(**self.line_result())

    def artifact_construct(
        self, selector, raw_value, level, rows, formula_returns=None
    ):
        self.prepare(formula_returns)
        self.table_ptrs["artifact_values"] = {}
        for key, row in rows.items():
            if len(row["pairs"]) != 10 or any(len(p) != 2 for p in row["pairs"]):
                raise ValueError("artifact rows require ten ordered pairs")
            p = self.alloc(132)
            self.write(p, b"\0" * 132)
            for off, val in [
                (0, row.get("selector", key)),
                (4, row["text_id"]),
                (116, row["formula_index"]),
                (124, row["threshold"]),
                (128, row["divisor"]),
            ]:
                self.put32(p + off, val)
            for i, pair in enumerate(row["pairs"]):
                for j, val in enumerate(pair):
                    self.put32(p + 32 + 8 * i + 4 * j, val)
            self.table_ptrs["artifact_values"][key] = p
        self.call(0x9627BE, [selector, raw_value, level], ecx=self.item, limit=500000)
        return self.result(entries=self.artifacts)

    def entry_ptr(self, entry):
        p = self.alloc(28)
        self.write(p, b"\0" * 28)
        for off, key in [
            (0, "selector"),
            (4, "text_id"),
            (8, "display_value"),
            (16, "raw_value"),
            (20, "position"),
            (24, "position_percent"),
        ]:
            self.put32(p + off, entry[key])
        self.write(p + 12, bytes([entry["threshold_flag"]]))
        return p

    def artifact_texts(self, texts):
        self.table_ptrs["artifact_names"] = {
            k: self.name(v, {"table": "artifact_names", "key": [k], "present": True})
            for k, v in texts.items()
        }

    def artifact_format(self, entry, texts, global_text=None):
        self.prepare([], global_text)
        self.artifact_texts(texts)
        p, out = self.entry_ptr(entry), self.alloc(24)
        self.sets(out, "UNCHANGED")
        ret = self.call(0x962E2F, [out, p], limit=500000)
        assert ret == out
        return self.result(text=self.string(out))

    def artifact_present(self, entries, texts, global_text=None):
        if len(entries) > 16:
            raise ValueError("bounded artifact presenter supports at most 16 entries")
        self.prepare([], global_text)
        self.artifact_texts(texts)
        self.artifact_ptrs = [self.entry_ptr(row) for row in entries]
        self.slice(0xF0DC38)
        return self.result(**self.line_result())

    def line_result(self):
        count = self.u32(self.frame - 0x10)
        if count > 64:
            raise cm.CaseError("line capacity exceeded")
        return {
            "line_count": count,
            "spacing_count": self.u32(self.frame - 0x14),
            "lines": [
                {
                    "text": cstring(self, LINE_BASE + i * 255),
                    "color": (
                        None
                        if self.u32(COLOR_BASE + 4 * i) == 0xFFFFFFFF
                        else self.u32(COLOR_BASE + 4 * i)
                    ),
                }
                for i in range(count)
            ],
        }


def provenance(TEXT, DATA):
    return {
        "api_version": API_VERSION,
        "text_sha256": hashlib.sha256(TEXT).hexdigest(),
        "data_sha256": hashlib.sha256(DATA).hexdigest(),
        "ranges": [
            {
                "start": hex(a),
                "end": hex(b),
                "file_offset": hex(a - 0x401000),
                "sha256": hashlib.sha256(TEXT[a - 0x401000 : b - 0x401000]).hexdigest(),
            }
            for a, b in RANGES
        ],
        "boundary": "Synthetic table lookup/string/container/CRT models; supplied formula returns optional; original decisions/varargs/conversions execute. No production C equivalence claimed.",
    }


def decode_corpus(value):
    """Restore strict-JSON numeric table keys, composite keys and FP bits."""
    if isinstance(value, dict):
        if set(value) == {"float64_bits"}:
            return struct.unpack("<d", bytes.fromhex(value["float64_bits"]))[0]
        if set(value) == {"tuple_key_rows"}:
            return {tuple(k): decode_corpus(v) for k, v in value["tuple_key_rows"]}
        return {
            (
                int(k) if isinstance(k, str) and re.fullmatch(r"-?\d+", k) else k
            ): decode_corpus(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [decode_corpus(v) for v in value]
    return value


def replay_case(oracle, record):
    """Execute one JSONL record. Parent can compare the same input with C."""
    record = decode_corpus(record)
    if record["method"] not in {
        "guardian_construct",
        "guardian_present",
        "artifact_construct",
        "artifact_format",
        "artifact_present",
    }:
        raise ValueError("unsupported oracle method")
    old_rows, old_known = oracle.rows, oracle.formula_table_known
    if "formula_rows" in record:
        oracle.rows = {
            (x["family"], x["index"]): x["expression"] for x in record["formula_rows"]
        }
        oracle.formula_table_known = record.get("formula_table_known", True)
    try:
        return getattr(oracle, record["method"])(*record["args"], **record["kwargs"])
    finally:
        oracle.rows, oracle.formula_table_known = old_rows, old_known
