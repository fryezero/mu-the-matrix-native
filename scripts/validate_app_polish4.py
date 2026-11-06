#!/usr/bin/env python3
"""APP-POLISH-004: the inventory item render info and the window name, original instructions vs native.

Families (the pinned restored text and data under Unicorn, the lang3 langread snapshot mapped at its
original addresses as in scripts/validate_lang.py):

* trs_lookup: ItemTRSData's find 0x011204db (this 0x06fbb624) for every key of the map and for absent keys
  returns node +0x14 or the default record 0x06fbaa40. The native side is native/core/mu_lang.c's
  mu_lang_item_trs over the itemtrs.tsv that scripts/live_lang_to_plain.py writes from the same snapshot:
  found/absent and the six words bit for bit.
* render_item3d: the slot wrapper 0x016c23d5 and RenderItem3D 0x016c154e with that real map lookup and the
  default record built by its static initializer 0x008dcce0, against the production resolver
  mu_hud_item_trs (native/core/mu_hud.c, compiled from its source text; the GFx item pass and the
  `mu-render ui inventory` pass both call it) feeding the reconstructed
  wrapper and RenderItem3D (reconstructed/hud/item_slots.c): every RenderObjectScreen argument and the item
  angle, bit for bit, at inventory geometry. Codes are every map key RenderItem3D does not special-case,
  plus absent codes; wing 0x19ab (model 0x2491) is always included.
* window_name: 0x012114c5 up to CreateWindowExW, with the battle-core query 0x0095fb99 false and true; the
  class and window name it passes. Native's MU_WINDOW_TITLE (native/client/main.c) must equal the first.

Modelled, not client code: the GFx manager, hover and NewUI queries (synthetic, as validate_hud's item3d);
RenderObjectScreen 0x016c2d82 and the overlay 0x016bf1fb are recording boundaries; the window routine's
user32/kernel32 imports return fixed handles and metrics. --mutants compiles planted mistakes; each must be
caught.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import pins  # noqa: E402
import client_ui_machine as cm  # noqa: E402
import live_lang_to_plain as plain  # noqa: E402
import validate_hud as vh  # noqa: E402
from validate_lang import LangMachine  # noqa: E402

ITEMTRS, TRS_FIND, DEFAULT_RECORD, DEFAULT_INIT = 0x06fbb624, 0x011204db, 0x06fbaa40, 0x008dcce0
WINDOW, CREATE_WINDOW_SLOT = 0x012114c5, 0x01a7c8b0
WINDOW_IMPORTS = {0x01a7c300: 4, 0x01a7c864: 8, 0x01a7c860: 8, 0x01a7c150: 4, 0x01a7c918: 4, 0x01a7c8a0: 12,
                  0x01a7c8e4: 4}
WING = 0x19ab
SECURITY_COOKIE = 0x01cf65c0

MUTANTS = [
    ('native/core/mu_hud.c', '    out->scale = v[5];', '    out->scale = v[5] * scale_factor;'),
    ('native/core/mu_hud.c', '    out->offset_y = v[1];', '    out->offset_y = v[0];'),
    ('native/core/mu_hud.c', '    out->rotation[0] = v[2];', '    out->rotation[0] = v[3];'),
    ('native/core/mu_hud.c', '        return mu_hud_trs_find(NULL, code, 1.0f, out);',
     '        return mu_hud_trs_find(NULL, code, scale_factor, out);'),
    ('native/core/mu_lang.c', '    if (!r)\n        return 0;\n    memcpy(values, r->v, sizeof(float) * 6);',
     '    if (!r)\n        r = L->itemtrs;\n    memcpy(values, r->v, sizeof(float) * 6);'),
    ('native/core/mu_lang.c', 'load_rows(dir, "itemtrs.tsv", 6,', 'load_rows(dir, "itemtrs.tsv", 5,'),
    ('scripts/live_lang_to_plain.py', "struct.unpack('<6i', snap.read(record(node), 24))",
     "struct.unpack('<6i', snap.read(record(node) + 4, 24))"),
    ('native/client/main.c', '#define MU_WINDOW_TITLE "MU"', '#define MU_WINDOW_TITLE "Mu"'),
]


def function(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}', start) + 2]


def sources(mutation=None):
    """The production source texts, one planted mistake applied when given."""
    out = {}
    for name in ('native/core/mu_lang.c', 'native/core/mu_hud.c',
                 'scripts/live_lang_to_plain.py', 'native/client/main.c'):
        text = (ROOT/name).read_text()
        if mutation and mutation[0] == name:
            if mutation[1] not in text:
                raise SystemExit(f'mutant anchor missing in {name}: {mutation[1]!r}')
            text = text.replace(mutation[1], mutation[2], 1)
        out[name] = text
    return out


def exported_rows(src, snapshot):
    """The itemtrs.tsv rows the (possibly mutated) converter's read_itemtrs gives for the snapshot."""
    module = type(sys)('polish4_plain')
    module.__file__ = str(ROOT/'scripts/live_lang_to_plain.py')
    exec(compile(src['scripts/live_lang_to_plain.py'], 'live_lang_to_plain.py', 'exec'), module.__dict__)
    return module.read_itemtrs(snapshot)


class Native:
    """mu_lang + the production resolver + reconstructed RenderItem3D, compiled from `src`; `rows` is the
    itemtrs.tsv content (None: no table)."""

    def __init__(self, work, src, rows):
        work.mkdir(parents=True, exist_ok=True)
        lang = work/'lang'
        lang.mkdir(exist_ok=True)
        if rows is not None:
            with open(lang/'itemtrs.tsv', 'w', encoding='ascii', newline='\n') as f:
                f.write('#code\tx\ty\trx\try\trz\tscale\n')
                for row in rows:
                    f.write('\t'.join(map(str, row)) + '\n')
        else:
            (lang/'globaltext.txt').write_text('0\tGulim\n')   # a lang folder without the table
        (work/'mu_lang.c').write_text(src['native/core/mu_lang.c'].replace('#include "mu_lang.h"',
                                                                           f'#include "{ROOT}/native/core/mu_lang.h"')
                                      .replace('#include "mu_lang_maps.h"',
                                               f'#include "{ROOT}/native/core/mu_lang_maps.h"'))
        title = re.search(r'#define MU_WINDOW_TITLE "([^"]*)"', src['native/client/main.c']).group(1)
        probe = '\n'.join([
            '#include <string.h>',
            '#include "native/core/mu_lang.h"',
            '#include "native/core/mu_hud.h"',
            function(src['native/core/mu_hud.c'], 'int mu_hud_trs_find('),
            function(src['native/core/mu_hud.c'], 'int mu_hud_item_trs('),
            '/* the GFx item pass and mu_hud_inventory_pass_at pass 200 (NATIVE-HUD-001) for the bmd stand-in */',
            'int resolve(const mu_lang *L, int32_t code, mu_item_trs *out) {'
            ' return mu_hud_item_trs(L, NULL, code, 200.0f, out); }',
            f'const char *window_title(void) {{ return "{title}"; }}', ''])
        (work/'probe.c').write_text(probe)
        cc = shutil.which('cc') or shutil.which('clang')
        lib = work/('libpolish4.dylib' if sys.platform == 'darwin' else 'libpolish4.so')
        subprocess.run([cc, '-std=c11', '-O2', '-ffp-contract=off', '-fno-fast-math', '-fPIC', '-shared', '-I', str(ROOT),
                        str(work/'probe.c'),
                        str(work/'mu_lang.c'), str(ROOT/'reconstructed/hud/item_slots.c'),
                        str(ROOT/'reconstructed/hud/inv_grid.c'), '-lm', '-o', str(lib)],
                       check=True, capture_output=True)
        self.lib = L = vh.slot_lib(vh.grid_lib(ctypes.CDLL(str(lib))))
        L.mu_lang_load.restype = ctypes.c_void_p
        L.mu_lang_load.argtypes = [ctypes.c_char_p]
        L.mu_lang_item_trs.restype = ctypes.c_int
        L.mu_lang_item_trs.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_float*6)]
        L.resolve.restype = ctypes.c_int
        L.resolve.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(vh.ItemTRS)]
        L.window_title.restype = ctypes.c_char_p
        self.handle = L.mu_lang_load(str(lang).encode())
        self.title = L.window_title().decode()

    def lookup(self, code):
        values = (ctypes.c_float*6)()
        found = self.lib.mu_lang_item_trs(self.handle, code, ctypes.byref(values))
        return found, struct.pack('<6f', *values) if found == 1 else None

    def resolve(self, code):
        out = vh.ItemTRS()
        found = self.lib.resolve(self.handle, code, ctypes.byref(out))
        return found, out

    def trs(self, code):
        return self.resolve(code)[1]


# ---- original side -------------------------------------------------------------------------------------

class Original:
    def __init__(self, text, data, snap):
        self.m = m = LangMachine(text, data, snap, check_reads=False)
        client = vh.Client.__new__(vh.Client)
        client.text, client.data, client.machine, client.events = text, data, m, []
        client.common_stubs()
        self.client = client
        self.prepared = False

    def prepare(self):
        m = self.m
        m.prepare()
        m.put32(SECURITY_COOKIE, 0xbb40e64e)
        if m.u32(DEFAULT_RECORD + 0x14) == 0:
            m.stub(0x0191be48, lambda mm: 0, 0)    # atexit(0x01a79bbe): the record's destructor
            m.call(DEFAULT_INIT)
            if m.errors:
                raise cm.CaseError(f'default record initializer: {m.errors}')

    def lookup(self, code):
        self.prepare()
        m = self.m
        pointer = m.call(TRS_FIND, (code & 0xffffffff,), ecx=ITEMTRS)
        if m.errors:
            raise cm.CaseError(f'0x011204db({code:#x}): {m.errors}')
        return pointer, m.read(pointer, 24)


def item3d_case(orig, nat, code, rng):
    """One slot wrapper + RenderItem3D case at inventory geometry; returns (client, native) tuples."""
    o = orig
    o.prepare()
    m = o.m
    sw, sh = rng.choice([(1280, 800), (1504, 936), (1722, 1048), (1920, 1080)])
    rate_x, rate_y = cm.f32(640.0/sw), cm.f32(480.0/sh)
    gfx = m.alloc(0x300, define=True)
    busy_obj, cc_obj, scale_obj = (m.alloc(0x60, define=True) for _ in range(3))
    frame = m.alloc(0x80, define=True)
    m.put32(gfx + 0x2e4, frame)
    m.put32(gfx + 0xd4, busy_obj)
    m.put32(gfx + 0xcc, cc_obj)
    m.put32(gfx + 0xa0, scale_obj)
    frame_scale = rng.choice([cm.f32(1.0), vh.rand_float(rng, 0.5, 2.0)])
    m.putf(scale_obj + 0x58, frame_scale)
    m.putf(gfx + 0x2cc, rate_x)
    m.putf(gfx + 0x2d0, rate_y)
    m.stub(0xac3bf7, lambda mm: gfx, 0)
    cursor_in = rng.random() < 0.3
    m.stub(0xc08654, lambda mm: 0, 0)
    m.stub(0xaae6f9, lambda mm: 0, 0)
    m.stub(0xec4bf2, lambda mm: int(cursor_in), 0)
    newui = m.alloc(0x10, define=True)
    m.stub(0xf2bb92, lambda mm: newui, 0)
    m.stub(0xf2aba9, lambda mm: 0, 4)
    m.stub(0xf2b602, lambda mm: 0, 0)
    m.stub(0xc94193, lambda mm: 0, 0)
    m.stub(0xcda1cf, lambda mm: 0, 0)
    m.stub(0xcd4ea8, lambda mm: newui, 0)
    m.stub(0xcd6017, lambda mm: 0, 8)
    m.stub(0xcd5fac, lambda mm: 0, 8)
    obj = m.alloc(0x120, define=True)
    level = rng.randrange(0, 16)
    level_word = level << 3
    m.put32(obj, m.alloc(vh.RECORD_SIZE, define=True))
    m.put32(obj + 0x10, code & 0xffffffff)
    m.put32(obj + 0x14, level_word)
    m.write(obj + 0x3b, b'\0')
    m.write(obj + 0x92, b'\0')
    m.write(obj + 0x98, b'\0')
    m.put32(obj + 0x84, 0xffffffff)
    # an inventory slot: 8 x 8 grid cells of 20 x 20 movie units, items up to 2 x 4 cells
    col, row = rng.randrange(0, 7), rng.randrange(0, 5)
    cw, ch = rng.choice([1, 2]), rng.choice([1, 2, 3, 4])
    x, y = cm.f32(440.0 + 20*col), cm.f32(120.0 + 20*row)
    w, h = cm.f32(20.0*cw), cm.f32(20.0*ch)
    args = (obj, vh.F(x), vh.F(y), vh.F(w), vh.F(h), 1, 0, 0, 0, frame, 0, vh.F(0.0), 0xffffffff, 0, 1, 0)
    ros_c = []

    def ros(mm):
        wd = mm.args(12)
        pos = struct.unpack('<3I', mm.read(wd[4], 12))
        angle = struct.unpack('<3I', mm.read(vh.ITEM_ANGLE, 12))
        ros_c.append(tuple(wd[:4]) + pos + tuple(wd[5:]) + angle)
        return 0
    m.stub(0x16c2d82, ros, 0)
    m.stub(0x16bf1fb, lambda mm: 0, 0)
    m.call(0x16c23d5, args)
    if m.errors:
        raise cm.CaseError(f'RenderItem3D {code:#x}: {m.errors}')
    win = vh.WrapperIn(code, level_word, 0, 0, -1, obj + 0x108, x, y, w, h, 1, 0, 0, 0, frame, 0, 0.0, -1, 0, 1, 0,
                       1, 0, 0, int(cursor_in))
    sysin = vh.Item3dIn()
    sysin.cursor_in = int(cursor_in)
    sysin.trs = nat.trs(code)
    sysin.frame_scale, sysin.rate_x, sysin.rate_y = frame_scale, rate_x, rate_y
    wout = vh.WrapperOut()
    nat.lib.mu_slot_wrapper(1, ctypes.byref(win), ctypes.byref(sysin), ctypes.byref(wout))
    out = vh.Item3dOut()
    kind = nat.lib.mu_item3d(ctypes.byref(wout.item3d), ctypes.byref(out))
    ros_a = []
    if kind == 1:
        ros_a.append((out.model & 0xffffffff, out.level_word & 0xffffffff, out.excellent & 0xffffffff, out.set_bits & 0xffffffff)
                     + tuple(vh.F(v) for v in out.position) + (out.select, out.a28 & 0xffffffff,
                                                               out.a2c & 0xffffffff, out.a30 & 0xffffffff,
                                                               vh.F(out.scale), out.a44 & 0xffffffff,
                                                               out.a48 & 0xffffffff) + tuple(vh.F(v) for v in out.angle))
    return ros_c, ros_a, (sw, sh, x, y, w, h, frame_scale)


def window_name(text, data, battle_core):
    """The class and window names 0x012114c5 passes to CreateWindowExW."""
    m = cm.Machine(text, data)
    client = vh.Client.__new__(vh.Client)
    client.text, client.data, client.machine, client.events = text, data, m, []
    roots, stops = (WINDOW,), {0x0095f75d, 0x0095fb99, vh.OP_NEW, vh.OP_DELETE, vh.MEMSET, vh.MEMMOVE, vh.MEMCPY}
    client.prepare(roots, stops)
    client.common_stubs()
    m.reset()
    m.put32(SECURITY_COOKIE, 0xbb40e64e)
    m.stub(0x0095f75d, lambda mm: 0x0bf00000, 0)
    m.stub(0x0095fb99, lambda mm: int(battle_core), 0)
    names = []

    def wide(address):
        out = bytearray()
        while len(out) < 512:
            pair = m.read(address + len(out), 2)
            if pair == b'\0\0':
                return out.decode('utf-16le')
            out += pair
        raise cm.CaseError('unterminated wide string')

    def create(mm):
        a = mm.args(12)
        names.append((wide(a[1]), wide(a[2])))
        mm.uc.reg_write(cm.UC_X86_REG_EIP, cm.RETURN_SENTINEL)
        return cm.REDIRECT
    for slot, cleanup in list(WINDOW_IMPORTS.items()) + [(CREATE_WINDOW_SLOT, 48)]:
        address = m._new_stub()
        m.put32(slot, address)
        m.stub(address, create if slot == CREATE_WINDOW_SLOT else (lambda mm: 0x100), cleanup)
    m.put32(0x0bdcb280, 2)            # the CRT's vector ISA level (as validate_lang's FTOL_LEVEL)
    m.put32(0x01cf0fc0, 0)            # windowed: the second CreateWindowExW (0x01211686)
    m.put32(0x01cf1624, 1504)
    m.put32(0x01cf1628, 936)
    m.call(WINDOW, (0x00400000,))
    if not names:
        raise cm.CaseError(f'CreateWindowExW not reached: {m.errors}')
    return names[0]


# ---- run ---------------------------------------------------------------------------------------------

def compare(orig, nat, keys, absent, item_codes, rng, report=None):
    """Raises CaseError at the first difference; returns the family counts."""
    families = {'trs_lookup': {'cases': 0, 'found': 0, 'absent': 0, 'mismatches': 0},
                'render_item3d': {'cases': 0, 'draws': 0, 'absent': 0, 'mismatches': 0}}
    for code in keys + absent:
        pointer, payload = orig.lookup(code)
        found, words = nat.lookup(code)
        client = (1, payload) if pointer != DEFAULT_RECORD else (0, None)
        if client != (found, words):
            raise cm.CaseError(f'trs_lookup {code:#x}: client {client} native {(found, words)}')
        fam = families['trs_lookup']
        fam['cases'] += 1
        fam['found' if found else 'absent'] += 1
    for code in item_codes:
        c, a, geometry = item3d_case(orig, nat, code, rng)
        if c != a:
            raise cm.CaseError(f'render_item3d {code:#x} {geometry}: client {c} native {a}')
        fam = families['render_item3d']
        fam['cases'] += 1
        fam['draws'] += len(c)
        fam['absent'] += int(code in absent)
        if report is not None and code == WING and 'wing' not in report:
            o = [struct.unpack('<f', struct.pack('<I', v))[0] for v in c[0][4:7]] if c else []
            report['wing'] = {'code': hex(WING), 'model': hex(c[0][0]) if c else None, 'geometry': list(geometry),
                              'position': o, 'scale': struct.unpack('<f', struct.pack('<I', c[0][11]))[0] if c else None}
    return families


def run(args):
    start = time.monotonic()
    text = pins.TEXT.read(args.text, exit=True)
    data = pins.DATA.read(args.data, exit=True)
    snap = plain.Snapshot(pins.LANG3.read(args.snapshot, exit=True))
    rng = random.Random(20261106)
    keys = [k for k, _ in snap.tree(ITEMTRS + 0x38)]
    keyset = set(keys)
    absent = sorted({-1, -0x80000000, 0x7fffffff, 0x2c00, 0xffff} |
                    {c for c in (rng.randrange(-0x400, 0x3000) for _ in range(args.absent)) if c not in keyset})
    absent = [c for c in absent if c not in keyset]
    report = {'snapshot_sha256': pins.LANG3.sha256, 'map_keys': len(keys)}
    with tempfile.TemporaryDirectory() as tmp:
        base = sources()
        nat = Native(Path(tmp)/'base', base, exported_rows(base, snap))
        special = {c for c in keys + absent if nat.lib.mu_item3d_is_special(c) or c < 0}
        pool = [c for c in keys if c not in special and c != WING]
        absent_items = [c for c in absent if c not in special]
        if args.item_cases and args.item_cases < len(pool) + len(absent_items):
            take = max(1, args.item_cases * len(pool) // (len(pool) + len(absent_items)))
            item_codes = [WING] + rng.sample(pool, take) + rng.sample(absent_items, min(len(absent_items),
                                                                                        args.item_cases - take))
        else:
            item_codes = [WING] + pool + absent_items
        orig = Original(text, data, snap)
        families = compare(orig, nat, keys, absent, item_codes, rng, report)
        names = [window_name(text, data, flag) for flag in (False, True)]
        families['window_name'] = {'cases': 2, 'mismatches': 0, 'client': [list(n) for n in names],
                                   'native': nat.title}
        if names[0] != (nat.title, nat.title):
            raise cm.CaseError(f'window_name: client {names[0]} native {nat.title!r}')
        report['families'] = families
        report['special_codes_skipped'] = len(special)
        mutants = {}
        if args.mutants:
            sample_keys = keys[:40] + [WING]
            sample_items = [WING] + item_codes[1:60] + absent_items[:20]
            for i, mutation in enumerate(MUTANTS):
                label = f'{i + 1}:{Path(mutation[0]).name}'
                try:
                    src = sources(mutation)
                    bad = Native(Path(tmp)/f'mutant{i}', src, exported_rows(src, snap))
                except subprocess.CalledProcessError as error:
                    raise SystemExit(f'mutant {label} does not compile: {error.stderr.decode()[-400:]}')
                caught = False
                if bad.title != names[0][1]:
                    caught = True
                else:
                    try:
                        compare(orig, bad, sample_keys, absent[:20], sample_items, random.Random(7))
                    except cm.CaseError:
                        caught = True
                mutants[label] = caught
                if not caught:
                    raise SystemExit(f'mutant {label} was not caught: {mutation[1]!r} -> {mutation[2]!r}')
        report['mutants'] = mutants
    report['wall_seconds'] = round(time.monotonic() - start, 3)
    report['ok'] = True
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--text', default=pins.TEXT.default_str())
    ap.add_argument('--data', default=pins.DATA.default_str())
    ap.add_argument('--snapshot', default=pins.LANG3.default_str(), help='langread snapshot lang3.bin')
    ap.add_argument('--absent', type=int, default=600, help='random absent codes drawn (before dropping keys)')
    ap.add_argument('--item-cases', type=int, default=0, help='RenderItem3D cases (0: every code)')
    ap.add_argument('--mutants', action='store_true')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    report = run(args)
    encoded = json.dumps(report, indent=1) + '\n'
    if args.output:
        args.output.write_text(encoded)
    print(json.dumps({k: v for k, v in report.items() if k != 'families'} |
                     {'cases': {k: v['cases'] for k, v in report['families'].items()}}))


if __name__ == '__main__':
    main()
