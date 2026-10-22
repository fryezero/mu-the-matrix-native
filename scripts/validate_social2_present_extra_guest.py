"""Private importable original-instruction presenter oracle. No client bytes embedded.

Import by path, instantiate OriginalPresenterOracle, then run_case(kind, **input).
No cases execute on import. Original table selectors and formatter bodies run;
STL lifetime, initialized managers, Boost/printf and text encoding are boundaries.
FormulaMachine supplies the original expression getter/parser/evaluator, not a
second formula reference model. Only explicit synthetic or caller-supplied rows
are loaded. An unavailable table is distinct from an available empty table.
"""

from pathlib import Path
import collections
import copy
import hashlib
import json
import re
import struct
import sys

from validate_social2_formula_guest import FormulaMachine, H, HV, cm, cstring, s32
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

cs = Cs(CS_ARCH_X86, CS_MODE_32)
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.x86_const import (
    UC_X86_REG_EIP,
    UC_X86_REG_FPCW,
    UC_X86_REG_FPSW,
    UC_X86_REG_FPTAG,
    UC_X86_REG_MXCSR,
)

ENTRY = dict(
    earring_numeric=0x10EE6A9,
    earring_text=0x10EE390,
    errtel_text=0xFC7317,
    standalone_errtel=0xFC9714,
    pentagram_rank=0xFCAA9A,
    advanced_text=0xCBC777,
    advanced_threshold=0xCBC6F2,
)
ENDS = {
    0x10EE35B: 0x10EE390,
    0x10EE390: 0x10EE6A9,
    0x10EE6A9: 0x10EE79A,
    0xFC7317: 0xFC74EC,
    0xFC9714: 0xFC99D6,
    0xFCAA9A: 0xFCABD9,
    0xCBC777: 0xCBC8FC,
    0xCBC6F2: 0xCBC741,
    0x995231: 0x995246,
    0xCCC591: 0xCCC5B0,
    0x191C5E0: 0x191C66C,
}


def synthetic_tables():
    """Authored rows intentionally separate outer keys, stored IDs and positions."""
    return dict(
        earring_text=[
            dict(key=i, id=1000 + i, text=f"E{i}% literal", format=f)
            for i, f in [(2, 1), (21, 2), (28, 1), (29, 2), (30, 1), (31, 2)]
        ],
        earring_values=[
            dict(
                tag=3,
                values=[
                    dict(rank=91, value=17, field8=300),
                    dict(rank=-1, value=7, field8=900),
                    dict(rank=0, value=0, field8=3),
                ],
            )
        ],
        jewel_values=[
            dict(
                id=500 + j,
                code=6365,
                rank=r,
                option=o,
                display_values=[base + k for k in range(11)],
                stat_values=[9000 + base + k for k in range(11)],
                text=text,
            )
            for j, (r, o, base, text) in enumerate(
                [
                    (1, 1, 100, "J1=%d%%"),
                    (2, 1, 200, "J2=%d"),
                    (3, 15, 300, "J3=%d"),
                    (5, 2, 400, "J5=%d"),
                    (2, 1, 800, "DUP=%d"),
                ]
            )
        ],
        advanced=[
            dict(group=g, id=i, name=name, values=values, format=f)
            for g, i, name, values, f in [
                (2, 5, "H% literal", [10, 20, 30, 40], 1),
                (2, 6, "P% literal", [-20, -5, 0, 10], 2),
                (3, 5, "Other group", [40, 10, 30, 20], 0),
                (4, 5, "Bad format", [0, 0, 0, 0], 9),
            ]
        ],
        formulas=[
            dict(group=9, index=7, expr="%d*1.75-0.5"),
            dict(group=9, index=17, expr="%d*2+0.75"),
            dict(group=1, index=7, expr="%d/200+%d*1.25"),
            dict(group=1, index=8, expr="%d/200-%d*1.75"),
        ],
        globaltext={
            0xE57: "Ranks=%d",
            0xE58: "Slot=%d,level=%d",
            0xE5A: "Unknown=%d",
            0x1298: "Undesignated",
            **{0xE98 + i: f"Element{i}" for i in range(-1, 8)},
        },
        rank_templates={
            0x4AE: "%s attack=%d level=%d",
            0x4AF: "%s defense=%d level=%d",
        },
    )


def c_rows(tables=None):
    """Yield exact existing social-options.tsv family/columns/text contracts.

    Keep this order: jewel lookups must retain first-match vector semantics.
    This is fixture serialization, not an alternate selection/reference model.
    """
    t = synthetic_tables() if tables is None else tables
    for r in t.get("earring_text") or []:
        yield "earring_name", [r.get("key", r["id"]), r["format"]], r["text"]
    for r in t.get("earring_values") or []:
        for pos, v in enumerate(r["values"]):
            yield "earring_value", [
                r["tag"],
                pos,
                v["rank"],
                v["value"],
                v["field8"],
            ], ""
    for r in t.get("jewel_values") or []:
        yield "jewel", [
            r["code"],
            r["rank"],
            r["option"],
            r["id"],
            r.get("field18", 0),
            r.get("field4c", 0),
            *r["display_values"],
            *r["stat_values"],
        ], r["text"]
    for r in t.get("advanced") or []:
        yield "advanced", [r["group"], r["id"], *r["values"], r["format"]], r["name"]


class OriginalPresenterOracle(FormulaMachine):
    """One reusable guest. Calls are sequential; instances are not thread-safe.

    Tables follow typed-tables-private.json row dictionaries, plus advanced
    rows {group,id,name,values[4],format} and formulas {group,index,expr}.
    None means unavailable; [] means loaded with no rows. Text fixtures use
    Latin-1 so a parent can compare exact bytes without an implicit UTF-8 step.
    """

    def __init__(self, text, data, tables=None):
        self.tables = copy.deepcopy(synthetic_tables() if tables is None else tables)
        self.executed_entries = collections.Counter()
        super().__init__(text, data, self.tables.get("formulas") or [])
        self.TEXT, self.DATA = text, data
        self.uc.mem_map(0x10C76000, 0x6000)
        self.uc.hook_add(UC_HOOK_MEM_READ, self._read, begin=0x10C76000, end=0x10C7BFFF)
        self.uc.hook_add(
            UC_HOOK_MEM_WRITE, self._write, begin=0x10C76000, end=0x10C7BFFF
        )
        self._install_presenter()
        # Reuse prior allowlists, without importing modules that run 25k cases.
        self.allow(
            *[
                (9331248, 9331251),
                (9878065, 9878106),
                (11831446, 11831475),
                (15818550, 15818577),
                (15818918, 15818986),
                (15821914, 15821959),
                (15822740, 15822773),
                (16545004, 16545160),
                (16546149, 16546304),
                (16562091, 16562099),
                (16563812, 16563846),
                (16564992, 16565044),
                (16565279, 16565326),
                (16565326, 16565353),
                (16565524, 16565538),
                (16566641, 16566680),
                (16566680, 16566705),
                (16566810, 16566878),
                (16567170, 16567181),
                (16570888, 16570932),
                (16570932, 16570977),
                (16571471, 16571516),
                (16571814, 16571847),
                (17603471, 17603550),
                (17603550, 17603629),
                (17606859, 17606924),
                (17606924, 17606989),
                (17606989, 17607152),
                (17607152, 17607315),
                (17607655, 17607663),
                (17607663, 17607671),
                (17607671, 17607750),
                (17607750, 17607829),
                (17607829, 17607837),
                (17607837, 17607845),
                (17607845, 17607853),
                (17607853, 17607861),
                (17608706, 17608735),
                (17608735, 17608764),
                (17608968, 17609002),
                (17609002, 17609036),
                (17610390, 17610431),
                (17610431, 17610472),
                (17610472, 17610519),
                (17610519, 17610566),
                (17610566, 17610590),
                (17610590, 17610614),
                (17610614, 17610631),
                (17610631, 17610648),
                (17611127, 17611139),
                (17611139, 17611151),
                (17611217, 17611235),
                (17611253, 17611271),
                (17611339, 17611356),
                (17611356, 17611373),
                (17613221, 17613263),
                (17613263, 17613305),
                (17613305, 17613348),
                (17613348, 17613391),
                (17613519, 17613533),
                (17613533, 17613547),
                (17750517, 17750669),
                (17750669, 17750836),
                (17753769, 17754010),
                (17760499, 17760564),
                (17760694, 17760759),
                (17760922, 17761085),
                (17761411, 17761574),
                (17762492, 17762500),
                (17762516, 17762524),
                (17762603, 17762682),
                (17762840, 17762919),
                (17763372, 17763380),
                (17763396, 17763404),
                (17763444, 17763452),
                (17763460, 17763468),
                (17763476, 17763484),
                (17763492, 17763500),
                (17763500, 17763508),
                (17763508, 17763516),
                (17763524, 17763532),
                (17765723, 17765752),
                (17765752, 17765781),
                (17765781, 17765810),
                (17765839, 17765868),
                (17765868, 17765897),
                (17765897, 17765926),
                (17765926, 17765955),
                (17765984, 17766013),
                (17766378, 17766412),
                (17766412, 17766446),
                (17766446, 17766480),
                (17766514, 17766548),
                (17767496, 17767724),
                (17767724, 17767971),
                (17768309, 17768470),
                (17768470, 17768645),
                (17768645, 17768677),
                (17770366, 17770407),
                (17770407, 17770448),
                (17770448, 17770489),
                (17770530, 17770571),
                (17770571, 17770618),
                (17770618, 17770665),
                (17770665, 17770692),
                (17770716, 17770740),
                (17770764, 17770788),
                (17770812, 17770836),
                (17770836, 17770853),
                (17770870, 17770887),
                (17770904, 17770921),
                (17770921, 17770938),
                (17770955, 17770972),
                (17770989, 17771006),
                (17771006, 17771026),
                (17771026, 17771046),
                (17771046, 17771066),
                (17771066, 17771086),
                (17771086, 17771189),
                (17771189, 17771292),
                (17772705, 17772717),
                (17772741, 17772753),
                (17772897, 17772915),
                (17772933, 17772951),
                (17772951, 17772969),
                (17772969, 17772987),
                (17773041, 17773059),
                (17773059, 17773077),
                (17773298, 17773315),
                (17773349, 17773366),
                (17776686, 17776717),
                (17776717, 17776748),
                (17778057, 17778101),
                (17778101, 17778145),
                (17778497, 17778539),
                (17778539, 17778581),
                (17778581, 17778623),
                (17778665, 17778707),
                (17778707, 17778750),
                (17778836, 17778879),
                (17779263, 17779277),
                (17779291, 17779305),
                (17779319, 17779333),
                (17779378, 17779411),
                (17908990, 17909069),
                (17909069, 17909170),
                (17909170, 17909249),
                (17909249, 17909350),
                (17912892, 17912939),
                (17912987, 17913034),
                (17914430, 17914477),
                (17914477, 17914524),
                (17916288, 17916628),
                (17916633, 17916973),
                (17917454, 17917519),
                (17917519, 17917584),
                (17917584, 17917747),
                (17917747, 17917910),
                (17918916, 17918924),
                (17918924, 17918932),
                (17918932, 17918940),
                (17918940, 17918948),
                (17918948, 17919027),
                (17919027, 17919106),
                (17919106, 17919114),
                (17919114, 17919122),
                (17919122, 17919130),
                (17919130, 17919138),
                (17919138, 17919146),
                (17919146, 17919154),
                (17919154, 17919162),
                (17919162, 17919170),
                (17920066, 17920074),
                (17920082, 17920090),
                (17920258, 17920266),
                (17920266, 17920274),
                (17920910, 17920939),
                (17920939, 17920968),
                (17920968, 17920997),
                (17920997, 17921026),
                (17921434, 17921468),
                (17921468, 17921502),
                (17921502, 17921536),
                (17921536, 17921570),
                (17923366, 17923407),
                (17923407, 17923448),
                (17923448, 17923489),
                (17923489, 17923530),
                (17923530, 17923577),
                (17923577, 17923624),
                (17923624, 17923671),
                (17923671, 17923718),
                (17923718, 17923742),
                (17923742, 17923766),
                (17923766, 17923790),
                (17923790, 17923814),
                (17923814, 17923831),
                (17923831, 17923848),
                (17923848, 17923865),
                (17923865, 17923882),
                (17923882, 17923902),
                (17923902, 17923922),
                (17923922, 17924025),
                (17924025, 17924128),
                (17924854, 17924866),
                (17924866, 17924878),
                (17924878, 17924890),
                (17924890, 17924902),
                (17925016, 17925034),
                (17925052, 17925070),
                (17925088, 17925106),
                (17925124, 17925142),
                (17925278, 17925295),
                (17925295, 17925312),
                (17925312, 17925329),
                (17925329, 17925346),
                (17928002, 17928033),
                (17928033, 17928064),
                (17929092, 17929134),
                (17929134, 17929176),
                (17929176, 17929267),
                (17929267, 17929358),
                (17929358, 17929401),
                (17929401, 17929444),
                (17929700, 17929714),
                (17929714, 17929728),
                (17929728, 17929742),
                (17929742, 17929756),
                (17966059, 17966151),
                (17966177, 17966278),
                (17966372, 17966421),
                (17966421, 17966467),
                (17967187, 17967234),
                (17967569, 17967616),
                (17968866, 17969206),
                (17969886, 17969894),
                (17970064, 17970072),
                (17970072, 17970080),
                (17970533, 17970541),
                (17970597, 17970605),
                (17971074, 17971103),
                (17971205, 17971239),
                (17972307, 17972348),
                (17972389, 17972436),
                (17972483, 17972507),
                (17972507, 17972524),
                (17972553, 17972573),
                (17972573, 17972676),
                (17973242, 17973254),
                (17973308, 17973326),
                (17973377, 17973394),
                (17974058, 17974089),
                (17974668, 17974759),
                (17974939, 17974953),
                (18101948, 18101998),
                (18101998, 18102035),
                (18102727, 18102742),
                (18106284, 18106367),
                (18106367, 18106452),
                (18108196, 18108261),
                (18108261, 18108326),
                (18108326, 18108489),
                (18108489, 18108652),
                (18108662, 18108670),
                (18108670, 18108678),
                (18108678, 18108757),
                (18108757, 18108836),
                (18108996, 18109004),
                (18109004, 18109012),
                (18109012, 18109020),
                (18109020, 18109028),
                (18109827, 18109856),
                (18109856, 18109885),
                (18110089, 18110123),
                (18110123, 18110157),
                (18111683, 18111724),
                (18111724, 18111765),
                (18111765, 18111789),
                (18111789, 18111813),
                (18111813, 18111830),
                (18111830, 18111847),
                (18112231, 18112243),
                (18112243, 18112255),
                (18112321, 18112339),
                (18112357, 18112375),
                (18112443, 18112460),
                (18112460, 18112477),
                (18114279, 18114321),
                (18114321, 18114363),
                (18114363, 18114406),
                (18114406, 18114449),
                (18114577, 18114591),
                (18114591, 18114605),
            ]
        )
        self.allow(*ENDS.items())
        self.allow(
            (0xCD2C33, cm.function_extent(self.TEXT, 0xCD2C33)),
            (0x11224C6, 0x1122524),
            (0x10F28F4, cm.function_extent(self.TEXT, 0x10F28F4)),
        )
        pending = [0x10F28F4]
        seen = set()
        while pending:
            a = pending.pop()
            if a in seen or a in self.stubs:
                continue
            if not 0x10F0000 <= a < 0x10F8000:
                raise ValueError(
                    "new helper outside bounded earring STL region " + hex(a)
                )
            seen.add(a)
            b = cm.function_extent(self.TEXT, a)
            self.allow((a, b))
            for ins in cs.disasm(self.TEXT[a - 0x401000 : b - 0x401000], a):
                if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
                    pending.append(int(ins.op_str, 16))
        self._hooks()

    def rawstr(self, text):
        b = text.encode("latin1")
        p = self.alloc(len(b) + 1)
        self.write(p, b + b"\0")
        return p

    def _install_presenter(self):
        st = self.st
        st(0x986523, self._decimal)
        st(0x95F027, self._global, 4)
        st(0x9619DD, self._printf)
        st(0x95248D, self._printf_n)
        st(0x9D5D27, self._boost_ctor, 4)
        st(0x9D419A, self._boost_arg, 4)
        st(0x97258C, self._boost_string, 4)
        st(0x96F4AE, lambda m: 0)
        # Rank helper leaves arguments pending across zero-argument singletons.
        st(0xF2BB92, lambda m: 0x300E0000)
        st(0xF2C141, lambda m: 0x300E0100)
        st(0xF13A6A, self._rank_template, 4)
        st(0x96E8C7, self._rank_boost_ctor, 4)
        st(0xAAF8CE, self._boost_string_arg, 4)
        st(0xA99D93, self._encoding)
        st(
            0xCCC51E,
            lambda m: m.fail("uninitialized ITEM record is outside this oracle"),
        )
        st(0xFC99D6, lambda m: m.fail("uncaptured mastery branch; body not entered"), 8)
        # Imports must never silently return success in this research adapter.
        for slot, address in self.slot_stub.items():
            name = cm.SLOTS[slot][0]
            self.handlers[name] = lambda m, words, n=name: m.fail(
                "unexpected import " + n
            )

    def _hooks(self):
        def at(a, fn):
            self.uc.hook_add(UC_HOOK_CODE, lambda u, p, z, d: fn(), begin=a, end=a)

        for a in [
            *ENTRY.values(),
            0x10EE35B,
            0x117B5EB,
            0x1200017,
            0x995231,
            0x191C5E0,
        ]:
            at(a, lambda p=a: self.executed_entries.update([hex(p)]))
        for a, state in [
            (0x10EE418, "missing_option"),
            (0x10EE461, "missing_tag"),
            (0x10EE48A, "selector_out_of_range"),
            (0x10EE4CA, "present"),
            (0x10EE713, "missing_option"),
            (0x10EE741, "missing_tag"),
            (0x10EE74F, "selector_out_of_range"),
            (0x10EE769, "present"),
            (0xFC7345, "level_out_of_range"),
            (0xFC74D9, "missing_row"),
            (0xFC73D2, "present"),
            (0xCBC7B0, "missing_row"),
            (0xCBC7CE, "present"),
        ]:
            at(a, lambda s=state, p=a: self._state(s, p))
        for a, name in [(0x10F4813, "earring_option"), (0x10F4894, "earring_tag")]:
            at(
                a,
                lambda n=name: self.selection.append(
                    dict(table=n, key=s32(self.u32(self.args(2)[1])))
                ),
            )
        at(
            0x1122461,
            lambda: self.selection.append(
                dict(table="advanced", key=list(map(s32, self.args(2))))
            ),
        )
        at(
            0x11223EB,
            lambda: self.selection.append(
                dict(table="advanced_exists", key=list(map(s32, self.args(2))))
            ),
        )
        at(0xFC7317, self._jewel_query)
        at(0x117B5EB, self._formula_query)
        at(0xFC74DB, self._jewel_result)
        at(0xCBC707, self._threshold_state)

    def _threshold_state(self):
        from unicorn.x86_const import UC_X86_REG_EAX

        self.row_state = (
            "present" if self.uc.reg_read(UC_X86_REG_EAX) else "missing_row"
        )

    def _state(self, state, address):
        self.row_state = state
        if address in (0xFC7345, 0xFC74D9, 0xFC73D2):
            self.jewel_results[-1]["row_state"] = state

    def _jewel_result(self):
        from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBP

        self.jewel_results[-1]["success"] = self.uc.reg_read(UC_X86_REG_EAX) & 255
        frame = self.uc.reg_read(UC_X86_REG_EBP)
        self.jewel_results[-1]["text"] = self.string(self.u32(frame + 0x18))

    def _jewel_query(self):
        code, level, rank, option, out = self.args(5)
        self.selection.append(
            dict(
                table="jewel_values",
                key=list(map(s32, (code, rank, option))),
                level=level,
            )
        )
        self.jewel_results.append(
            dict(key=list(map(s32, (code, rank, option))), level=level)
        )

    def _formula_query(self):
        ptr, family, index = self.args(3)
        n = 1 if s32(family) == 9 else 2
        words = self.args(3 + n)[3:]
        self.formula_calls.append(
            dict(
                family=s32(family),
                index=s32(index),
                args=list(map(s32, words)),
                present=(s32(family), s32(index)) in self.rows,
            )
        )

    def _decimal(self, m):
        out, word = m.args(2)
        value = s32(word)
        self.formats.append(dict(api="decimal", args=[value], words=[word]))
        return m.sets(out, str(value))

    def _global(self, m):
        key = m.args(1)[0]
        self.selection.append(dict(table="globaltext", key=key))
        texts = self.tables.get("globaltext")
        if texts is None or key not in texts:
            return m.fail("missing GlobalText " + hex(key))
        p = self.rawstr(texts[key])
        self.text_keys[p] = ["globaltext", key]
        return p

    def _format(self, out, fp, words, api):
        fmt = cstring(self, fp)
        vals = []
        raw = []
        kinds = []
        wi = 0
        for mt in re.finditer(r"%(?:[-+ #0]*\d*(?:\.\d+)?)?([dius%])", fmt):
            k = mt.group(1)
            if k == "%":
                continue
            if wi >= len(words):
                raise ValueError("fixture format consumes unavailable argument")
            w = words[wi]
            wi += 1
            raw.append(w)
            kinds.append(k)
            vals.append(cstring(self, w) if k == "s" else w if k == "u" else s32(w))
        tag = self.text_keys.get(fp, ["fixed", hex(fp)])
        self.formats.append(
            dict(
                api=api,
                template=tag,
                kinds=kinds,
                args=vals,
                supplied_args=vals + [s32(w) for w in words[wi:]],
                words=list(words),
                consumed_words=raw,
            )
        )
        rendered = fmt % tuple(vals)
        self.write(out, rendered.encode("latin1") + b"\0")
        return len(rendered)

    def _printf(self, m):
        out, fp = m.args(2)
        # Both advanced fixed patterns supply name and value even if name has '%'.
        return self._format(out, fp, m.args(4)[2:], "sprintf")

    def _printf_n(self, m):
        out, size, fp = m.args(3)
        # This bounded standalone function supplies 1 or 2 words by callsite.
        ret = self.u32(self.uc.reg_read(cm.UC_X86_REG_ESP))
        n = 2 if ret == 0xFC983E else 1
        return self._format(out, fp, m.args(3 + n)[3:], "snprintf")

    def _boost_ctor(self, m):
        text = m.string(m.args(1)[0])
        obj = m.this()
        self.boost[obj] = dict(text=text, args=[], kinds=[], words=[])
        self.boost[obj]["template"] = ["jewel_row", self.active_jewel_key()]
        return obj

    def active_jewel_key(self):
        return next(
            e["key"] for e in reversed(self.selection) if e["table"] == "jewel_values"
        )

    def _boost_arg(self, m):
        obj = self.boost[m.this()]
        ptr = m.args(1)[0]
        w = m.u32(ptr)
        obj["args"].append(s32(w))
        obj["words"].append(w)
        obj["kinds"].append("i32")
        return m.this()

    def _boost_string_arg(self, m):
        obj = self.boost[m.this()]
        w = m.u32(m.args(1)[0])
        obj["args"].append(cstring(m, w))
        obj["words"].append(w)
        obj["kinds"].append("str")
        return m.this()

    def _boost_string(self, m):
        obj = self.boost[m.this()]
        out = m.args(1)[0]
        self.formats.append(
            dict(api="boost", **{k: v for k, v in obj.items() if k != "text"})
        )
        # Synthetic/text rendering boundary. Record all args even for literal rows.
        n = len(
            re.findall(
                r"%(?!%)(?:[-+ #0]*\d*(?:\.\d+)?)?[dis]", obj["text"].replace("%%", "")
            )
        )
        text = obj["text"] % tuple(obj["args"][:n])
        return m.sets(out, text)

    def _rank_template(self, m):
        key = m.args(1)[0] & 65535
        self.selection.append(dict(table="rank_templates", key=key))
        ts = self.tables.get("rank_templates")
        if ts is None or key not in ts:
            return m.fail("missing ItemTooltipText " + hex(key))
        self.rank_key = key
        self.row_state = "present"
        return self.rawstr("xx" + ts[key])

    def _rank_boost_ctor(self, m):
        obj = m.this()
        self.boost[obj] = dict(
            text=cstring(m, m.args(1)[0]),
            args=[],
            kinds=[],
            words=[],
            template=["rank_templates", self.rank_key],
        )
        return obj

    def _encoding(self, m):
        out, source = m.args(2)
        self.encoding_calls.append(m.string(source))
        # Full conversion is a Windows encoding boundary. ASCII fixtures only.
        if not m.string(source).isascii():
            return m.fail("non-ASCII Windows conversion unmodeled")
        return m.sets(out, m.string(source))

    def _prepare(self):
        self.reset()
        self.vectors = {}
        self.stacks = {}
        self.savedkey = [0]
        # Machine.reset clears handlers, so restore the import guard per case.
        for slot in self.slot_stub:
            name = cm.SLOTS[slot][0]
            self.handlers[name] = lambda m, words, n=name: m.fail(
                "unexpected import " + n
            )
        self.formatted = []
        self.postfix = []
        self.formats = []
        self.selection = []
        self.formula_calls = []
        self.boost = {}
        self.text_keys = {}
        self.encoding_calls = []
        self.jewel_results = []
        self.row_state = "unknown"
        self.boundaries = collections.Counter()
        self.write(0x10C76000, b"\0" * 0x6000)
        self.put32(0x300F0004, 0x300F0100)
        self.put32(0xBDCB280, 0)
        self.uc.mem_write(H, b"\xdd\x05" + struct.pack("<I", HV) + b"\xc3")
        self.uc.reg_write(UC_X86_REG_FPCW, 0x27F)
        self.uc.reg_write(UC_X86_REG_FPSW, 0)
        self.uc.reg_write(UC_X86_REG_FPTAG, 0xFFFF)
        self.uc.reg_write(UC_X86_REG_MXCSR, 0x1F80)

    def zero(self, n):
        return self.alloc(n, True)

    def tree(self, items, container):
        # A balanced authored MSVC tree; stable sorting retains duplicate-group order.
        h = self.zero(16)
        self.write(h + 12, b"\1\1")

        def rec(xs, parent):
            if not xs:
                return h
            ix = len(xs) // 2
            key, row = xs[ix]
            p = self.zero(20 + len(row))
            self.put32(p + 4, parent)
            self.put32(p + 16, key)
            self.write(p + 20, row)
            self.put32(p, rec(xs[:ix], p))
            self.put32(p + 8, rec(xs[ix + 1 :], p))
            return p

        rt = rec(sorted(items, key=lambda x: s32(x[0])), h)
        self.put32(h + 4, rt)

        def edge(p, off):
            while p != h and self.u32(p + off) != h:
                p = self.u32(p + off)
            return p

        self.put32(h, edge(rt, 0))
        self.put32(h + 8, edge(rt, 8))
        self.put32(container, h)
        self.put32(container + 4, len(items))

    def vector(self, p, rows):
        raw = b"".join(rows)
        q = self.zero(max(16, len(raw)))
        self.write(q, raw)
        for off, v in [(0, q), (4, q + len(raw)), (8, q + len(raw))]:
            self.put32(p + off, v)

    def _earring_tables(self):
        self.write(0x6FBAA60, b"\0" * 0x100)
        items = []
        for r in self.tables["earring_text"]:
            p = self.zero(0x20)
            self.put32(p, r["id"])
            self.sets(p + 4, r["text"])
            self.put32(p + 0x1C, r["format"])
            items.append((r.get("key", r["id"]), self.read(p, 0x20)))
        self.tree(items, 0x6FBAAC0 + 0x38)
        items = []
        for r in self.tables["earring_values"]:
            p = self.zero(12)
            self.vector(
                p,
                [
                    struct.pack("<iii", v["rank"], v["value"], v["field8"])
                    for v in r["values"]
                ],
            )
            items.append((r["tag"], self.read(p, 12)))
        self.tree(items, 0x6FBAA60 + 0x50)

    def _jewel_tables(self):
        self.write(0x6FBAEFC, b"\0" * 0x80)
        rows = []
        for r in self.tables["jewel_values"]:
            p = self.zero(0x50)
            for off, key in [
                (0, "id"),
                (4, "code"),
                (8, "section"),
                (12, "index"),
                (16, "rank"),
                (20, "option"),
                (24, "field18"),
                (0x4C, "field4c"),
            ]:
                self.put32(p + off, r.get(key, 0))
            for off, key in [(0x1C, "display_values"), (0x28, "stat_values")]:
                if len(r[key]) != 11:
                    raise ValueError("jewel fixture needs exactly eleven values")
                self.vector(p + off, [struct.pack("<i", x) for x in r[key]])
            self.sets(p + 0x34, r["text"])
            rows.append(self.read(p, 0x50))
        self.vector(0x6FBAEFC + 0x3C, rows)

    def _advanced_tables(self):
        self.write(0x6FBBFCC, b"\0" * 0x80)
        rows = []
        for r in self.tables["advanced"]:
            p = self.zero(0x34)
            self.put32(p, r["group"])
            self.put32(p + 4, r["id"])
            self.sets(p + 8, r["name"])
            self.write(p + 0x20, struct.pack("<4i", *r["values"]))
            self.put32(p + 0x30, r["format"])
            rows.append((r["group"], self.read(p, 0x34)))
        self.tree(rows, 0x6FBBFCC + 0x38)

    def _item(self, code=6365, required_level=400, grade=0):
        it = self.zero(0x12C)
        row = self.zero(0x2C4)
        self.put32(it, row)
        self.put32(row, code)
        self.write(row + 0x286, struct.pack("<H", required_level & 65535))
        self.write(row + 0x2B8, bytes([grade & 255]))
        return it

    def run_case(self, kind, **c):
        """Run one complete bounded original body. Returns JSON-ready observations.

        earring_numeric/text: option, selector, tag; text also enhancement_level,
          optional other_full_l; self_only=True enters wrapper 10ee35b.
        errtel_text: code, level, physical_rank, option.
        standalone_errtel: code, socket_count, five raw slots, grade=0, line=0.
        pentagram_rank: type, level, defense_flag, status=0, required_level.
        advanced_text/threshold: group, option, value; text convert=0.
        """
        if kind not in ENTRY:
            raise ValueError(kind)
        required = (
            ["earring_text", "earring_values"]
            if kind.startswith("earring")
            else (
                ["jewel_values"]
                if kind in ("errtel_text", "standalone_errtel")
                else ["advanced"] if kind.startswith("advanced") else ["formulas"]
            )
        )
        if kind == "earring_text" and 28 <= (c["option"] & 255) <= 31:
            required += ["formulas"]
        if kind == "pentagram_rank":
            required += ["globaltext", "rank_templates"]
        if kind == "standalone_errtel":
            required += ["globaltext"]
        unavailable = [k for k in required if self.tables.get(k) is None]
        if unavailable:
            return dict(status="table_unavailable", unavailable=unavailable)
        self._prepare()
        out = self.zero(32)
        self.sets(out, "UNCHANGED")
        if kind.startswith("earring"):
            self._earring_tables()
            args = [out, c["option"], c["selector"], c["tag"]]
            address = ENTRY[kind]
            ecx = 0x6FBAAC0
            if kind == "earring_text":
                args += [c.get("enhancement_level", 0)]
                if c.get("self_only", False):
                    address = 0x10EE35B
                else:
                    other = 0
                    if c.get("other_full_l") is not None:
                        other = self.zero(0x12C)
                        self.put32(other + 0x14, c["other_full_l"])
                    args += [other]
        elif kind == "errtel_text":
            self._jewel_tables()
            args = [c["code"], c["level"], c["physical_rank"], c["option"], out]
            ecx = 0
        elif kind == "standalone_errtel":
            if not 0 <= c.get("line", 0) <= 60:
                raise ValueError("bounded synthetic line start is 0..60")
            self._jewel_tables()
            it = self._item(c.get("code", 6365), grade=c.get("grade", 0))
            if len(c["slots"]) != 5:
                raise ValueError("standalone needs five physical slots")
            self.write(it + 0x73, bytes(c["slots"]))
            self.write(it + 0x78, bytes([c["socket_count"] & 255]))
            self.put32(0xB449C8C, 0)
            args = [it, c.get("line", 0)]
            ecx = 0
        elif kind == "pentagram_rank":
            it = self._item(required_level=c["required_level"])
            args = [
                out,
                it,
                c["type"],
                c["level"],
                c["defense_flag"],
                c.get("status", 0),
            ]
            ecx = 0
        else:
            self._advanced_tables()
            ecx = 0
            args = [c["group"], c["option"], c["value"]]
            if kind == "advanced_text":
                args = [out, *args, c.get("convert", 0)]
        try:
            ret = self.call(
                address if kind.startswith("earring") else ENTRY[kind],
                args,
                ecx=ecx,
                limit=500000,
            )
        except cm.CaseError as e:
            if "uncaptured mastery branch" in str(e):
                return dict(
                    status="uncaptured_mastery",
                    formats=self.formats,
                    selection=self.selection,
                    formula_calls=self.formula_calls,
                )
            if "missing GlobalText" in str(e) or "missing ItemTooltipText" in str(e):
                return dict(
                    status="text_dependency_missing",
                    detail=str(e),
                    formats=self.formats,
                    selection=self.selection,
                    formula_calls=self.formula_calls,
                )
            raise
        if self.calls:
            raise cm.CaseError("unexpected import trace in presenter case")
        result = dict(
            status="ok",
            row_state=self.row_state,
            formats=copy.deepcopy(self.formats),
            selection=list(self.selection),
            formula_calls=list(self.formula_calls),
            encoding_calls=list(self.encoding_calls),
        )
        if kind in ("errtel_text", "standalone_errtel"):
            result["jewel_results"] = copy.deepcopy(self.jewel_results)
        if kind == "earring_numeric":
            result["numeric"] = list(struct.unpack("<iii", self.read(out, 12)))
        elif kind == "errtel_text":
            result.update(success=ret & 255, text=self.string(out))
        elif kind == "advanced_threshold":
            result["threshold"] = s32(ret)
        elif kind == "standalone_errtel":
            start = c.get("line", 0)
            result["next_line"] = s32(ret)
            result["lines"] = [
                dict(
                    text=cstring(self, 0x10C76988 + i * 255),
                    color=self.u32(0x10C7B938 + 4 * i),
                    bold=self.u32(0x10C7BA78 + 4 * i),
                )
                for i in range(start, ret)
            ]
            result["global_line_count"] = self.u32(0xB449C8C)
            result["row_state"] = "no_lines" if start == ret else "present"
        else:
            result["text"] = self.string(out)
        return result

    def provenance(self):
        ranges = sorted(set(self.allowed))
        return dict(
            text_sha256=hashlib.sha256(self.TEXT).hexdigest(),
            data_sha256=hashlib.sha256(self.DATA).hexdigest(),
            ranges=[
                dict(
                    start=hex(a),
                    end=hex(b),
                    offset=hex(a - 0x401000),
                    sha256=hashlib.sha256(
                        self.TEXT[a - 0x401000 : b - 0x401000]
                    ).hexdigest(),
                )
                for a, b in ranges
            ],
            stubs=[hex(a) for a, (kind, _) in self.stubs.items() if kind == "client"],
        )


def semantic_observation(result):
    """Stable comparison fields for the parent's C join; no guest pointer words.

    Keep raw words in full evidence. Compare logical string args rather than
    host-specific pointer addresses; all actual varargs are recorded first.
    """
    r = copy.deepcopy(result)
    for e in r.get("formats", []):
        e.pop("words", None)
        e.pop("consumed_words", None)
    return r
