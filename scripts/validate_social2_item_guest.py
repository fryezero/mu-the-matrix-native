#!/usr/bin/env python3
"""Bounded instruction observations for NATIVE-SOCIAL-001 round 2.

The C comparison driver is validate_social2_items. This file models the named
external boundaries; private captures are loaded locally and hash checked.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import gc
import hashlib
import importlib.util
from pathlib import Path
import struct

DEFAULT_REPO = Path(__file__).resolve().parents[1]
DEFAULT_TEXT = (
    Path.home()
    / "Documents/main-exe-study/evidence/x86-text-capture-09/client-text.bin"
)
DEFAULT_DATA = (
    Path.home()
    / "Documents/main-exe-study/evidence/image-data-run10/data-capture-10/client-image-data.bin"
)
TEXT_SHA256 = "2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724"
DATA_SHA256 = "c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f"


def _load_machine(repo):
    path = Path(repo) / "scripts/client_ui_machine.py"
    spec = importlib.util.spec_from_file_location(
        "_social_harness_client_ui_machine", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _byte(v):
    if not isinstance(v, int) or not 0 <= v <= 255:
        raise ValueError(f"expected byte, got {v!r}")
    return v


@dataclass(frozen=True)
class Wire:
    code: int = 0
    level_word: int = 0
    durability: int = 0
    excellent: int = 0
    ancient: int = 0
    flags: int = 0
    harmony: int = 0
    sockets: tuple[int, ...] = (255,) * 5
    extra: tuple[int, ...] | None = (255,) * 3

    def __post_init__(self):
        if not isinstance(self.code, int) or not 0 <= self.code <= 65535:
            raise ValueError("converter code must fit u16")
        for name in (
            "level_word",
            "durability",
            "excellent",
            "ancient",
            "flags",
            "harmony",
        ):
            _byte(getattr(self, name))
        if len(self.sockets) != 5 or (self.extra is not None and len(self.extra) != 3):
            raise ValueError(
                "sockets must have 5 bytes; extra must have 3 bytes or be None"
            )
        for v in (*self.sockets, *(self.extra or ())):
            _byte(v)

    @classmethod
    def from_packet(cls, packet):
        """Authored convenience unpack, NOT instruction proof. run_wrapper proves it."""
        b = bytes(packet)
        if len(b) != 15:
            raise ValueError("exactly 15 item bytes required")
        code = b[0] | ((b[3] & 128) << 1) | ((b[5] & 240) << 5) | ((b[5] & 1) << 13)
        return cls(
            code,
            b[1],
            b[2],
            b[3] & 127,
            b[4],
            b[5] & 15,
            b[6],
            tuple(b[7:12]),
            tuple(b[12:15]),
        )


@dataclass(frozen=True)
class Record:
    kind_a: int = 0
    kind_b: int = 0
    grade: int = 0
    skill: int = 0
    base_level: int = 0
    slot: int = 0
    slot_flags: tuple[int, ...] = (0, 0, 0, 0)  # +2a8..2ab, +2a9 is can_trade

    def __post_init__(self):
        for v in (self.kind_a, self.kind_b, self.grade, self.slot, *self.slot_flags):
            _byte(v)
        if (
            len(self.slot_flags) != 4
            or not 0 <= self.skill <= 65535
            or not 0 <= self.base_level <= 65535
        ):
            raise ValueError("record word fields/slot flags out of range")


@dataclass(frozen=True)
class ItemState:
    """Already finalized ITEM inputs for standalone predicates, no packet inference."""

    code: int = 0
    level_word: int = 0
    durability: int = 0
    ancient: int = 0
    excellent_resolved: int = 0
    period: int = 0
    expired: int = 0

    def __post_init__(self):
        if not -(1 << 31) <= self.code < (1 << 31) or not -(
            1 << 31
        ) <= self.level_word < (1 << 31):
            raise ValueError("state words must fit i32")
        for name in (
            "durability",
            "ancient",
            "excellent_resolved",
            "period",
            "expired",
        ):
            _byte(getattr(self, name))


@dataclass
class Boundaries:
    """Explicit external outputs. Synthetic keys/rows only, no installed tables."""

    normalized_slot: int = 15
    finalizer_excellent: int = 0
    artifact_present: bool = True
    guardian_options: dict = field(
        default_factory=dict
    )  # (base, key) -> (i32@4, i32@8, i32@10)
    guardian_bonus: dict = field(
        default_factory=dict
    )  # (base, key) -> ((id,value),(id,value))
    guardian_option_text: dict = field(
        default_factory=dict
    )  # key -> authored string label
    guardian_bonus_text: dict = field(
        default_factory=dict
    )  # id -> authored string label
    capability: bool | None = (
        None  # None executes real 16b823e, stable record early path only
    )
    character_option: bool = False
    character_status: int = 0
    advanced_eligible: bool | None = None  # None executes real cd248c
    advanced_group: int | None = None  # None executes real cd25ec
    record_present: bool = (
        True  # converter only; absent lookup must remain safe until null check
    )
    item_id: int = 1

    def __post_init__(self):
        for v in (
            self.normalized_slot,
            self.finalizer_excellent,
            self.character_status,
        ):
            _byte(v)
        for values in self.guardian_options.values():
            if len(values) != 3:
                raise ValueError("guardian option requires three fields")
        for values in self.guardian_bonus.values():
            if len(values) != 2 or any(len(pair) != 2 for pair in values):
                raise ValueError("guardian bonus requires two pairs")


# Only these simple bodies may execute in addition to each selected entry point.
# cd1dfc and its three helpers execute their own category tests, never an authored answer.
HELPERS = (
    (0x95FC2E, 0x95FC71),
    (0x987982, 0x9879C5),
    (0x95FBEB, 0x95FC2E),
    (0xCD0995, 0xCD0A10),
    (0xCD1DFC, 0xCD1E38),
    (0xCD1E65, 0xCD1E85),
    (0xCD1E85, 0xCD1ED8),
    (0xCD1ED8, 0xCD1EF8),
    (0x995231, 0x995246),
    (0x9B48EB, 0x9B492E),
    (0x10A9E31, 0x10A9E62),
    (0xADAB29, 0xADAB46),
    (0xF0A424, 0xF0A437),
    (0xF0A437, 0xF0A44B),
    (0xCBC25A, 0xCBC282),
    (0xF08C10, 0xF08CFC),
    (0xCCFFF3, 0xCD0033),
    (0xCD2386, 0xCD241F),
    (0xCD248C, 0xCD25EC),
    (0xCD25EC, 0xCD269A),
    (0xCD40E3, 0xCD410A),
    (0xCBE21C, 0xCBE240),
    # Only the early stable-record branches of capability may execute.
    (0x16B823E, 0x16B8312),
    (0x16B8504, 0x16B8506),
)

STUB_ARG_COUNTS = {
    0x191BA7B: 1,
    0x185CB38: 1,
    0x194C200: 3,
    0xCD248C: 1,
    0xB647C0: 1,
    0x97F8CF: 1,
    0x9627BE: 3,
    0x111454D: 2,
    0x1114601: 2,
    0x11144FE: 1,
    0x11145B2: 1,
    0x94AF7D: 1,
    0xCA95BD: 1,
    0xCA95A6: 1,
    0xF09F1A: 4,
    0xF0A7B1: 1,
    0x16B823E: 1,
    0x1295ADE: 1,
    0xF08FB2: 10,
}


class SocialHarness:
    def __init__(
        self, repo=DEFAULT_REPO, text_path=DEFAULT_TEXT, data_path=DEFAULT_DATA
    ):
        self.repo = Path(repo)
        text, data = Path(text_path).read_bytes(), Path(data_path).read_bytes()
        for name, payload, expected in (
            ("text", text, TEXT_SHA256),
            ("data", data, DATA_SHA256),
        ):
            actual = hashlib.sha256(payload).hexdigest()
            if actual != expected:
                raise ValueError(
                    f"{name} SHA-256 mismatch: {actual}, expected {expected}"
                )
        self.cm = cm = _load_machine(repo)
        from unicorn.x86_const import UC_X86_REG_EFLAGS

        self.flags_reg = UC_X86_REG_EFLAGS

        class AuditedMachine(cm.Machine):
            # Host stub reads bypass Unicorn's memory hooks. Audit those too.
            def read(q, address, size):
                for start, end in (
                    (cm.HEAP_BASE, cm.HEAP_BASE + cm.HEAP_SIZE),
                    (cm.BSS_BASE, cm.BSS_END),
                ):
                    lo, hi = max(address, start), min(address + size, end)
                    if any(a not in q.defined for a in range(lo, hi)):
                        raise cm.CaseError(
                            f"host read of undefined memory at {address:#x}, size {size}"
                        )
                return super().read(address, size)

            def _stub_hit(q, uc, address, size, user):
                entry = q.stubs.get(address)
                if entry and entry[0] == "import" and entry[1][0] not in q.handlers:
                    q.fail(f"unmodelled import {entry[1][0]}")
                    return
                return super()._stub_hit(uc, address, size, user)

        self.m = AuditedMachine(text, data)
        self.closed = False
        self.events = []
        self.hits = set()
        # Branch visits prove execution without storing original instructions.
        self.branch_addresses = {
            "grade3": 0xF092C3,
            "sockets": 0xF09302,
            "elemental": 0xF094B1,
            "rank": 0xF09570,
            "artifact": 0xF096FF,
            "guardian": 0xF097F6,
            "extra_word": 0xF099B5,
            "advanced": 0xF09B59,
            "fallback_extra": 0xF09BF0,
        }
        self._stop_at = None
        self.m.uc.hook_add(cm.UC_HOOK_CODE, self._instruction)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        """Release emulator and all per-case references. No files/processes opened."""
        self.m = None
        self.events = []
        self.hits = set()
        self.closed = True
        # Unicorn hooks retain bound methods; collect those now, not at exit.
        gc.collect()

    def _instruction(self, uc, address, size, user):
        if self.cm.TEXT_BASE <= address < self.cm.TEXT_BASE + len(self.m.text):
            if address not in self.m.stubs and not any(
                a <= address and address + size <= b for a, b in self.m.allowed
            ):
                self.m.fail(f"instruction left the allowlist at {address:#x}")
                return
        if address in self.branch_addresses.values():
            self.hits.add(address)
        if address == self._stop_at:
            uc.emu_stop()

    def _reset(self):
        if self.closed:
            raise RuntimeError("harness is closed")
        m, cm = self.m, self.cm
        m.reset()
        # Machine.reset preserves registered stubs and allowlist by design.
        # This harness removes case-dependent replacements before each case.
        m.stubs = {a: s for a, s in m.stubs.items() if s[0] == "import"}
        m.allowed = list(HELPERS)
        # Machine audits heap/BSS; stack remains explicitly synthetic scratch.
        m.uc.mem_write(cm.STACK_BASE, bytes(cm.STACK_SIZE))
        m.uc.reg_write(self.flags_reg, 2)
        self.events, self.hits, self._stop_at = [], set(), None
        self.guardian_text = {}
        self._artifacts, self._guardian_lookups = [], []
        self._guardian_options, self._guardian_bonus = [], []
        self._finalizer, self._maxdur, self._registry = [], [], []
        self._stub_counts = {}
        self.boundary_calls = []
        self.item = None

    def _stub(self, address, name, callback, cleanup=0):
        def wrapped(m):
            self._stub_counts[name] = self._stub_counts.get(name, 0) + 1
            esp = m.uc.reg_read(self.cm.UC_X86_REG_ESP)
            call = {
                "address": address,
                "return_address": m.u32(esp),
                "ecx": self._ecx(),
                "entry_esp": esp,
                "args": m.args(STUB_ARG_COUNTS.get(address, 0)),
                "cleanup": cleanup,
            }
            self.boundary_calls.append(call)
            result = callback(m)
            call["result"] = result or 0
            return result

        self.m.stub(address, wrapped, cleanup)

    def _ecx(self):
        return self.m.uc.reg_read(self.cm.UC_X86_REG_ECX)

    def _expect(self, condition, message):
        if not condition:
            raise self.cm.CaseError(message)

    def _put16(self, address, value):
        self.m.write(address, struct.pack("<H", value & 65535))

    def _u16(self, address):
        return struct.unpack("<H", self.m.read(address, 2))[0]

    def _i32(self, address):
        return struct.unpack("<i", self.m.read(address, 4))[0]

    def _record(self, r):
        m = self.m
        # Define only the fields consumed by permitted instructions.
        p = m.alloc(0x2B0)
        m.write(p + 0x250, bytes((r.kind_a, r.kind_b, r.grade)))
        self._put16(p + 0x254, r.base_level)
        m.write(p + 0x256, bytes((r.slot,)))
        self._put16(p + 0x258, r.skill)
        m.write(p + 0x2A8, bytes(r.slot_flags))
        self.record = p
        return p

    def _init_item(self, p):
        """Selected known ctor defaults, no blanket 'defined zero' object."""
        m = self.m
        m.put32(p, 0)
        for off in (0x10, 0x84, 0x88, 0xEC):
            m.put32(p + off, -1)
        for off in (0x14, 0x64, 0xE0, 0xF0, 0xF4, 0xF8, 0x104, 0x120):
            m.put32(p + off, 0)
        for off, size in (
            (0x38, 6),
            (0x3E, 32),
            (0x5E, 4),
            (0x6E, 5),
            (0x73, 17),
            (0x90, 4),
            (0x98, 1),
        ):
            m.write(p + off, bytes(size))
        m.write(p + 0x99, bytes((255,)) * 9)
        m.write(p + 0x124, bytes((255,)) * 5)
        rank = m.alloc(64)
        m.write(rank, struct.pack("<16i", *([-1] * 16)))
        m.put32(p + 0xD4, rank)
        m.put32(p + 0xD8, rank + 64)
        m.put32(p + 0xDC, rank + 64)
        self.item = p
        return p

    def _state_item(self, s):
        p = self._init_item(self.m.alloc(0x12C))
        self.m.put32(p + 0x10, s.code)
        self.m.put32(p + 0x14, s.level_word)
        for off, value in (
            (0x38, s.durability),
            (0x3B, s.ancient),
            (0x98, s.excellent_resolved),
            (0x92, s.period),
            (0x93, s.expired),
        ):
            self.m.write(p + off, bytes((value,)))
        return p

    def _common(self, r, b):
        m = self.m
        self._record(r)
        self._stub(0xCCC591, "record_lookup", lambda q: self.record)

        def normalize(q):
            args = q.args(1)
            self._expect(args == [r.slot], "slot-normalizer ABI")
            self.events.append(("normalize_slot", args))
            return b.normalized_slot

        self._stub(0x185CB38, "normalize_slot", normalize)

        def copy(q):
            dst, src, n = q.args(3)
            q.write(dst, q.read(src, n))
            return dst

        self._stub(0x194C200, "memcpy", copy)
        if b.advanced_eligible is not None:
            self._stub(
                0xCD248C, "supplied_eligibility", lambda q: int(b.advanced_eligible), 4
            )
        if b.advanced_group is not None:
            self._stub(0xCD25EC, "supplied_group", lambda q: b.advanced_group)

    def _call(self, address, args=(), ecx=None, cleanup=0):
        m, cm = self.m, self.cm
        result = m.call(address, args, ecx, limit=100000)
        top = cm.STACK_BASE + cm.STACK_SIZE - 0x1000
        expected = top - 4 * len(args) + cleanup
        self._expect(
            m.uc.reg_read(cm.UC_X86_REG_ESP) == expected,
            f"stack cleanup mismatch for {address:#x}",
        )
        self._expect(m.u32(cm.TEB_BASE) == 0xFFFFFFFF, "SEH chain not restored")
        return result

    def _audit(self):
        return {
            "undefined_reads": len(self.m.errors),
            "heap_checks": bool(self.m._heap_hooks),
            "stubs": dict(self._stub_counts),
            "branch_visits": [
                k for k, v in self.branch_addresses.items() if v in self.hits
            ],
        }

    def snapshot(self, p=None):
        """Semantic scalar fields read from executed ITEM memory; no byte dumps."""
        p = self.item if p is None else p
        m = self.m
        out = {
            name: self._i32(p + off)
            for name, off in (
                ("code", 0x10),
                ("level_word", 0x14),
                ("item_id", 0x64),
                ("element", 0x84),
                ("element_aux", 0x88),
                ("advanced_group", 0xE0),
                ("advanced_slot", 0xEC),
                ("advanced_option", 0xF0),
                ("saved_group", 0xF8),
                ("advanced_level", 0x104),
                ("extra_word", 0x120),
            )
        }
        out.update(
            {
                name: m.read(p + off, 1)[0]
                for name, off in (
                    ("durability", 0x38),
                    ("excellent", 0x3A),
                    ("ancient", 0x3B),
                    ("socket_subtype", 0x3C),
                    ("prefix_count", 0x3D),
                    ("flag_72", 0x72),
                    ("socket_count", 0x78),
                    ("socket_bonus", 0x83),
                    ("field_91", 0x91),
                    ("period", 0x92),
                    ("expired", 0x93),
                    ("excellent_resolved", 0x98),
                )
            }
        )
        out.update(
            {
                name: self._u16(p + off)
                for name, off in (
                    ("add_rank", 0x5E),
                    ("skill", 0x60),
                    ("harmony_kind", 0x6E),
                    ("harmony_level", 0x70),
                )
            }
        )
        out.update(
            {
                name: list(m.read(p + off, n))
                for name, off, n in (
                    ("socket_raw", 0x73, 5),
                    ("seed_index", 0x79, 5),
                    ("seed_level", 0x7E, 5),
                    ("special_raw", 0x99, 5),
                    ("extra_excellent", 0x9F, 3),
                    ("extra_124", 0x124, 5),
                )
            }
        )
        count = out["prefix_count"]
        self._expect(count <= 8, "option list exceeded 8-slot observed layout")
        out["prefix"] = [
            [self._u16(p + 0x3E + 2 * i), self._u16(p + 0x4E + 2 * i)]
            for i in range(count)
        ]
        rank = m.u32(p + 0xD4)
        out["rank"] = [
            [self._i32(rank + 16 * i + 4 * j) for j in range(4)] for i in range(4)
        ]
        return out

    def run_converter(self, wire, record, boundaries=None):
        """Whole f08fb2, with option/stat finalizers and C++ boundaries modelled."""
        b = boundaries or Boundaries()
        self._reset()
        m = self.m
        self._common(record, b)
        m.allow((0xF08FB2, 0xF09C51))
        owner = m.alloc(0x10)
        artifact_manager, artifact_object = m.alloc(4), m.alloc(4)
        sockets = m.alloc(5)
        m.write(sockets, bytes(wire.sockets))
        extra = 0
        if wire.extra is not None:
            extra = m.alloc(3)
            m.write(extra, bytes(wire.extra))

        def allocate(q):
            self._expect(q.args(1) == [0x12C], "allocator size")
            return q.alloc(0x12C)

        self._stub(0x191BA7B, "allocate", allocate)
        self._stub(0xCCBAA2, "constructor", lambda q: self._init_item(self._ecx()))
        self._stub(0xF09E41, "allocate_id", lambda q: b.item_id)
        if not b.record_present:
            # Real category helpers dereference the lookup result before the
            # converter's null check for valid codes. Reject this unsafe model.
            if wire.code <= 0x2C00:
                raise ValueError(
                    "null record converter probe requires out-of-range code; valid-code predicates dereference it first"
                )
            self._stub(0xCCC591, "record_lookup", lambda q: 0)
        self._stub(
            0xB647C0,
            "delete_item",
            lambda q: self.events.append(("delete_item", q.args(1))) or 0,
            4,
        )

        def artifact_accessor(q):
            self._expect(
                q.args(1) == [self.item]
                and q.u32(q.uc.reg_read(self.cm.UC_X86_REG_ESP)) == 0xF09707,
                "artifact accessor must preserve pending ITEM argument",
            )
            return artifact_manager

        self._stub(0x96BACA, "artifact_manager", artifact_accessor)

        def artifact_lookup(q):
            self._expect(
                self._ecx() == artifact_manager and q.args(1) == [self.item],
                "artifact accessor ABI",
            )
            self.events.append(("artifact_lookup", ["item"]))
            return artifact_object if b.artifact_present else 0

        self._stub(0x97F8CF, "artifact_lookup", artifact_lookup, 4)

        def artifact_add(q):
            self._expect(self._ecx() == artifact_object, "artifact object this")
            args = q.args(3)
            self._artifacts.append(args)
            self.events.append(("artifact_add", args))
            return 0

        self._stub(0x9627BE, "artifact_add", artifact_add, 12)

        def guardian_row(q, bonus=False):
            keys = q.args(2)
            self._expect(self._ecx() == 0x6FBBF24, "guardian manager this")
            self._guardian_lookups.append(["bonus" if bonus else "option", *keys])
            values = (b.guardian_bonus if bonus else b.guardian_options).get(
                tuple(keys)
            )
            if values is None:
                return 0
            p = q.alloc(0x24)
            if bonus:
                for i, pair in enumerate(values):
                    q.put32(p + 8 + 12 * i, pair[0])
                    q.put32(p + 12 + 12 * i, pair[1])
            else:
                for off, value in zip((4, 8, 0x10), values):
                    q.put32(p + off, value)
            return p

        self._stub(0x111454D, "guardian_option_lookup", lambda q: guardian_row(q), 8)
        self._stub(
            0x1114601, "guardian_bonus_lookup", lambda q: guardian_row(q, True), 8
        )

        def text_row(q, bonus=False):
            key = q.args(1)[0]
            self._guardian_lookups.append(
                ["bonus_text" if bonus else "option_text", key]
            )
            label = (b.guardian_bonus_text if bonus else b.guardian_option_text).get(
                key
            )
            if label is None:
                return 0
            if not isinstance(label, str):
                raise ValueError("guardian text labels must be authored strings")
            p = q.alloc(8)
            self.guardian_text[p + 4] = label
            return p

        self._stub(0x11144FE, "guardian_option_text", lambda q: text_row(q), 4)
        self._stub(0x11145B2, "guardian_bonus_text", lambda q: text_row(q, True), 4)

        def temp_ctor(q, bonus=False):
            p = self._ecx()
            self.guardian_text[p + (8 if bonus else 12)] = ""
            return p

        self._stub(0xCA8E45, "guardian_option_ctor", lambda q: temp_ctor(q))
        self._stub(0xCA8CC1, "guardian_bonus_ctor", lambda q: temp_ctor(q, True))

        def string_copy(q):
            src = q.args(1)[0]
            self._expect(src in self.guardian_text, "unknown synthetic string source")
            self.guardian_text[self._ecx()] = self.guardian_text[src]
            return self._ecx()

        self._stub(0x94AF7D, "string_copy", string_copy, 4)

        def append(q, bonus=False):
            p = q.args(1)[0]
            self._expect(
                self._ecx() == self.item + (0xC8 if bonus else 0xBC),
                "guardian append this",
            )
            count = 2 if bonus else 3
            values = [self._i32(p + 4 * i) for i in range(count)]
            text = self.guardian_text[p + 4 * count]
            (self._guardian_bonus if bonus else self._guardian_options).append(
                {"fields": values, "text": text}
            )
            return 0

        self._stub(0xCA95BD, "guardian_option_append", lambda q: append(q), 4)
        self._stub(0xCA95A6, "guardian_bonus_append", lambda q: append(q, True), 4)

        def destroy_temp(q, bonus=False):
            self.guardian_text.pop(self._ecx() + (8 if bonus else 12))
            return 0

        self._stub(0xBC7D65, "guardian_option_dtor", lambda q: destroy_temp(q))
        self._stub(0xBC7D50, "guardian_bonus_dtor", lambda q: destroy_temp(q, True))

        def finalize(q):
            args = q.args(4)
            self._expect(self._ecx() == owner and args[0] == self.item, "finalizer ABI")
            self._finalizer.append(args[1:])
            self.events.append(("finalizer", args[1:]))
            # Capture inputs before model writes or any advanced handling.
            self.pre_finalizer = self.snapshot()
            q.put32(self.item + 0x14, args[1])
            q.write(self.item + 0x98, bytes((b.finalizer_excellent,)))
            return 0

        self._stub(0xF09F1A, "option_stat_finalizer", finalize, 16)

        def maxdur(q):
            self._expect(self._ecx() == self.item, "max durability this")
            self._maxdur.append("item")
            self.events.append(("max_durability", []))
            return 0

        self._stub(0xCCC5B0, "max_durability", maxdur)

        def registry(q):
            args = q.args(1)
            self._expect(
                self._ecx() == owner + 4 and q.u32(args[0]) == self.item,
                "registry append ABI",
            )
            self._registry.append("item")
            self.events.append(("registry_append", ["item"]))
            return 0

        self._stub(0xF0A7B1, "registry_append", registry, 4)
        args = [
            wire.code >> 9,
            wire.code & 511,
            wire.level_word,
            wire.durability,
            wire.excellent,
            wire.ancient,
            wire.flags,
            wire.harmony,
            sockets,
            extra,
        ]
        returned = self._call(0xF08FB2, args, owner, 40)
        if returned:
            self._expect(returned == self.item, "converter returned unexpected object")
        return {
            "returned_item": bool(returned),
            "item": self.snapshot() if returned else None,
            "pre_finalizer": self.pre_finalizer if self._finalizer else None,
            "artifact_calls": self._artifacts,
            "guardian_lookups": self._guardian_lookups,
            "guardian_options": self._guardian_options,
            "guardian_bonus": self._guardian_bonus,
            "finalizer_args": self._finalizer,
            "max_durability_calls": self._maxdur,
            "registry_calls": self._registry,
            "events": self.events,
            "boundary_calls": self.boundary_calls,
            "audit": self._audit(),
        }

    def run_leaf_defaults(self):
        """Real rank-entry and advanced-slot scalar constructors on undefined heap."""
        self._reset()
        p, q = self.m.alloc(16), self.m.alloc(16)
        self._call(0xCD40E3, ecx=p)
        self._call(0xCBE21C, ecx=q)
        return {
            "rank": [self._i32(p + 4 * i) for i in range(4)],
            "advanced": [self._i32(q + 4 * i) for i in range(4)],
            "audit": self._audit(),
        }

    def run_prefix(
        self, state, record, level_word, excellent, ancient=0, boundaries=None
    ):
        """ccc993 entry through exclusive stop cccaeb; no later option formula path."""
        for value in (level_word, excellent, ancient):
            _byte(value)
        self._reset()
        self._common(record, boundaries or Boundaries())
        p = self._state_item(state)
        m, cm = self.m, self.cm
        m.allow((0xCCC993, 0xCCCAEB))
        self._stop_at = 0xCCCAEB
        # Machine.call normally requires a return. This deliberate slice keeps
        # the real function prologue and arguments, and stops before cmp at end.
        esp = cm.STACK_BASE + cm.STACK_SIZE - 0x1000 - 16
        m.write(
            esp, struct.pack("<4I", cm.RETURN_SENTINEL, level_word, excellent, ancient)
        )
        for reg in (
            cm.UC_X86_REG_EAX,
            cm.UC_X86_REG_EBX,
            cm.UC_X86_REG_EDX,
            cm.UC_X86_REG_ESI,
            cm.UC_X86_REG_EDI,
            cm.UC_X86_REG_EBP,
        ):
            m.uc.reg_write(reg, 0)
        m.uc.reg_write(cm.UC_X86_REG_ESP, esp)
        m.uc.reg_write(cm.UC_X86_REG_ECX, p)
        m.uc.emu_start(0xCCC993, 0xCCCAEB, count=100000)
        self._expect(
            not m.errors and m.uc.reg_read(cm.UC_X86_REG_EIP) == 0xCCCAEB,
            f"prefix failed: {m.errors}",
        )
        self._expect(
            m.uc.reg_read(cm.UC_X86_REG_ESP) == esp - 4 - 0xA4, "prefix stack drift"
        )
        result = {
            "item": self.snapshot(),
            "stop_address": 0xCCCAEB,
            "boundary_calls": self.boundary_calls,
            "audit": self._audit(),
        }
        # No suspended frame is retained for another call.
        self._stop_at = None
        return result

    def run_advanced(self, state, record, check_level=0, boundaries=None):
        """Whole cd2386, cd248c and cd25ec on one explicitly seeded state."""
        b = boundaries or Boundaries()
        if b.advanced_eligible is not None or b.advanced_group is not None:
            raise ValueError("standalone advanced proof must execute its predicates")
        self._reset()
        self._common(record, b)
        p = self._state_item(state)
        restricted = self._call(0xCD2386, ecx=p) & 255
        eligible = self._call(0xCD248C, [_byte(check_level)], p, 4) & 255
        group = self._call(0xCD25EC, ecx=p)
        return {
            "restricted": restricted,
            "eligible": eligible,
            "group": group,
            "events": self.events,
            "boundary_calls": self.boundary_calls,
            "audit": self._audit(),
        }

    def run_tradeban(self, state, record, boundaries=None):
        """Whole 16bed45. state=None tests its explicit null-item branch."""
        b = boundaries or Boundaries()
        self._reset()
        self._common(record, b)
        m = self.m
        m.allow((0x16BED45, 0x16BEE94))
        p = 0 if state is None else self._state_item(state)
        character = m.alloc(0x35B0)
        m.put32(0xA39D754, character)
        m.write(character + 0x14, bytes((b.character_status,)))
        if b.capability is not None:

            def capability(q):
                self._expect(q.args(1) == [p], "capability ABI")
                return int(b.capability)

            self._stub(0x16B823E, "supplied_capability", capability)

        def character_option(q):
            self._expect(
                self._ecx() == character + 0x35AC and q.args(1) == [0x1C],
                "character option ABI",
            )
            self.events.append(("character_option", [0x1C]))
            return int(b.character_option)

        self._stub(0x1295ADE, "character_option", character_option, 4)
        banned = self._call(0x16BED45, [p]) & 255
        return {
            "banned": banned,
            "events": self.events,
            "boundary_calls": self.boundary_calls,
            "audit": self._audit(),
        }

    def run_wrapper(self, packet):
        """Whole f08dca + real f09ddc; record the ten converter arguments."""
        packet = bytes(packet)
        if len(packet) != 15:
            raise ValueError("exactly 15 item bytes required")
        self._reset()
        m = self.m
        m.allow((0xF08DCA, 0xF08F31), (0xF09DDC, 0xF09E41))
        p, owner = m.alloc(15), m.alloc(4)
        m.write(p, packet)
        observations = []

        def badread(q, args):
            self._expect(args == [p, 7], "IsBadReadPtr ABI")
            return 0

        m.handlers["IsBadReadPtr"] = badread

        def convert(q):
            args = q.args(10)
            self._expect(self._ecx() == owner, "wrapper converter this")
            observations.append(
                {
                    "words": args[:8],
                    "sockets": list(q.read(args[8], 5)),
                    "extra": list(q.read(args[9], 3)),
                }
            )
            return 1

        self._stub(0xF08FB2, "converter_recorder", convert, 40)
        self._call(0xF08DCA, [p], owner, 4)
        return {
            "converter_args": observations,
            "imports": m.calls,
            "boundary_calls": self.boundary_calls,
            "audit": self._audit(),
        }


def load(**kwargs):
    return SocialHarness(**kwargs)
