#!/usr/bin/env python3
"""RENDER-ITEMS-CALLERS-001: the world callers of RenderObjDraw's pre-draw programs against the pinned client.

RenderObjDraw 0x0176ce74 runs an item's pre-draw program (RENDER-ITEMS-002R) on BoneTransform 0x06fce398 and gates
most cases on its flag [ebp-0xd] = TestFrustrum2D 0x016ccce7(OBJECT +0x158 x * 0.01, y * 0.01, -20). The native
world callers (native/world/world_rt.c world_rt_item_pre) give it the item's saved pose and the flag computed by
native/world/world_item_pre.h at the item model's origin. Families:

* link_flag   RenderLinkItem 0x012bd910's copy of the item model's BodyOrigin (model +0x78) into the link OBJECT
              (PART + 0x24) +0x158 at 0x012c6302..0x012c637d, then RenderObjDraw's own entry up to the flag store
              (0x0176ce74..0x0176cef5: stack probe, SEH frame, TestFrustrum2D on the scene state 0x01d1df70 and the
              polygon 0x0b6b5400/0x0b6b5410). The client's flag byte against the C header on the model origin:
              random convex polygons of both windings, origins inside/around them, directed origins on the -20
              margin line (d = -20 +- small steps), and NaN/infinite/signed-zero coordinates. Scene states 6 and 5
              (every state outside 1..4 tests the polygon).
* part_flag   the same through RenderPartObject 0x017e63f4's copy of the OBJECT +0x158 into model +0x78
              (0x017e64dc..0x017e6545; ground items): the flag at the OBJECT equals the C on the model origin.
* order       static control flow: in RenderLinkItem every path from the origin copy (0x012c6302) to the call of
              RenderObjDraw (0x012c6a83) passes the item's pose, Animation 0x012b5064 at 0x012c6478 (so the pre-draw
              program reads the item's own bones, then the body draws); in RenderPartObject the origin copy
              dominates both calls (0x017e7960, 0x017e7997) and every switch jump on the way.
* callers     the text's call sites of RenderObjDraw: RenderLinkItem (worn weapons/wings: the native hero, players
              and player-model actors), RenderPartObject (ground items, body parts) and two in 0x00a49266, the
              render callback 0x00a16273 registers for object type 0x67a (INVENTORY-FX; the inventory's icons reach
              RenderObjDraw through RenderObjectScreen -> RenderPartObject).

--mutations plants mistakes in the C header (separately compiled) and requires each to be caught.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins  # noqa: E402

TEXT_BASE, DATA_BASE = 0x00401000, 0x01a7c000
RENDER_OBJ_DRAW, FLAG_STORED = 0x0176ce74, 0x0176cef5
LINK_COPY, LINK_COPY_END, LINK_POSE, LINK_CALL = 0x012c6302, 0x012c637d, 0x012c6478, 0x012c6a83
PART_FN, PART_COPY, PART_COPY_END, PART_CALLS = 0x017e63f4, 0x017e64dc, 0x017e6545, (0x017e7960, 0x017e7997)
SCENE_STATE, X2D, Y2D = 0x01d1df70, 0x0b6b5400, 0x0b6b5410
EXPECTED_CALLERS = {0x00a497c6: 'object 0x67a', 0x00a49bc9: 'object 0x67a', LINK_CALL: 'RenderLinkItem',
                    PART_CALLS[0]: 'RenderPartObject', PART_CALLS[1]: 'RenderPartObject'}
HEADER = ROOT / 'native/world/world_item_pre.h'
TERRAIN = ['reconstructed/terrain/terrain.c', 'reconstructed/terrain/world_haze.c',
           'reconstructed/record-math/record_math.c']
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
MUTANTS = {
    'scale': ('const float x = origin[0] * 0.01f', 'const float x = origin[0] * 0.02f'),
    'axis': ('y = origin[1] * 0.01f', 'y = origin[2] * 0.01f'),
    'range': ('6, x, y, -20.0f)', '6, x, y, -21.0f)'),
    'negate': ('return !mu_terrain_test_frustum_2d', 'return mu_terrain_test_frustum_2d'),
    'scene': ('(x2d, y2d, 6, x', '(x2d, y2d, 3, x'),
    'swap': ('mu_terrain_test_frustum_2d(x2d, y2d,', 'mu_terrain_test_frustum_2d(y2d, x2d,'),
}


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def descriptor(base, limit, access=0x93, flags=0xc):
    return struct.pack('<Q', (limit & 0xffff) | ((base & 0xffffff) << 16) | (access << 40) |
                       (((limit >> 16) & 0xf) << 48) | (flags << 52) | ((base >> 24) << 56))


class Client:
    TEB, GDT, STACK, WORK, SENTINEL = 0x00280000, 0x00290000, 0x00300000, 0x00400000 - 0x10000, 0x00290ff0
    OBJ, MODEL, FRAME = 0x003f0000, 0x003f2000, 0x003f8000

    def __init__(self, text, data):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_PROT_ALL
        from unicorn import x86_const as x86
        self.x86 = x86
        uc = self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(TEXT_BASE, len(text), UC_PROT_ALL)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, (len(data) + 0xfff) & ~0xfff, UC_PROT_ALL)
        uc.mem_write(DATA_BASE, data)
        for base, size in ((0x01d1d000, 0x1000), (0x0b6b5000, 0x1000), (self.TEB, 0x1000), (self.GDT, 0x1000),
                           (self.STACK, 0x40000), (self.WORK, 0x10000)):
            uc.mem_map(base, size, UC_PROT_ALL)
        gdt = (b'\0' * 8 + descriptor(0, 0xfffff, 0x9a, 0xc) + descriptor(0, 0xfffff, 0x92, 0xc) +
               descriptor(self.TEB, 0xfff, 0x92, 0x4))
        uc.mem_write(self.GDT, gdt)
        uc.reg_write(x86.UC_X86_REG_GDTR, (0, self.GDT, len(gdt) - 1, 0))
        uc.reg_write(x86.UC_X86_REG_SS, 2 << 3)
        uc.reg_write(x86.UC_X86_REG_FS, 3 << 3)
        uc.mem_write(self.TEB, struct.pack('<I', 0xffffffff))

    def run(self, start, until, esp, ebp=0x13579bdf):
        x86, uc = self.x86, self.uc
        uc.reg_write(x86.UC_X86_REG_ESP, esp)
        uc.reg_write(x86.UC_X86_REG_EBP, ebp)
        uc.reg_write(x86.UC_X86_REG_EFLAGS, 2)
        uc.reg_write(x86.UC_X86_REG_MXCSR, 0x1f80)
        try:
            uc.emu_start(start, until, timeout=0, count=200000)
        except Exception as failure:  # UcError
            return f'uc {failure} at {uc.reg_read(x86.UC_X86_REG_EIP):#x}'
        pc = uc.reg_read(x86.UC_X86_REG_EIP)
        return None if pc == until else f'stopped at {pc:#x}'

    def setup(self, xs, ys, state):
        self.uc.mem_write(X2D, struct.pack('<4f', *xs))
        self.uc.mem_write(Y2D, struct.pack('<4f', *ys))
        self.uc.mem_write(SCENE_STATE, struct.pack('<i', state))

    def flag(self, obj):
        """RenderObjDraw(obj, type, ...) up to the flag store; returns ([ebp-0xd], error)."""
        top = self.STACK + 0x3f000
        frame = struct.pack('<I', self.SENTINEL) + struct.pack('<4I', obj, 0x2382, self.WORK, 0x3f800000)
        self.uc.mem_write(top, frame + b'\0' * 0x30)
        error = self.run(RENDER_OBJ_DRAW, FLAG_STORED, top)
        ebp = self.uc.reg_read(self.x86.UC_X86_REG_EBP)
        return (self.uc.mem_read(ebp - 0xd, 1)[0] if error is None else None), error

    def link_copy(self, origin, junk):
        """RenderLinkItem's copy of model +0x78 into the link OBJECT +0x158 (frame: [ebp-0x114] model, -0x120 OBJECT)."""
        uc = self.uc
        uc.mem_write(self.MODEL + 0x78, struct.pack('<3f', *origin))
        uc.mem_write(self.OBJ + 0x158, struct.pack('<3f', *junk))
        uc.mem_write(self.FRAME - 0x120, struct.pack('<I', self.OBJ))
        uc.mem_write(self.FRAME - 0x114, struct.pack('<I', self.MODEL))
        return self.run(LINK_COPY, LINK_COPY_END, self.STACK + 0x20000, self.FRAME)

    def part_copy(self, position, junk):
        """RenderPartObject's copy of the OBJECT +0x158 into model +0x78 (frame: [ebp+8] OBJECT, [ebp-0x10] model)."""
        uc = self.uc
        uc.mem_write(self.OBJ + 0x158, struct.pack('<3f', *position))
        uc.mem_write(self.MODEL + 0x78, struct.pack('<3f', *junk))
        uc.mem_write(self.FRAME + 8, struct.pack('<I', self.OBJ))
        uc.mem_write(self.FRAME - 0x10, struct.pack('<I', self.MODEL))
        return self.run(PART_COPY, PART_COPY_END, self.STACK + 0x20000, self.FRAME)

    def vec(self, address):
        return struct.unpack('<3f', self.uc.mem_read(address, 12))


def build_c(work: Path, header_root: Path, objects: list[Path], name: str):
    shim = work / f'{name}.c'
    shim.write_text('#include "native/world/world_item_pre.h"\n'
                    'int shim_out_of_view(const float *x2d, const float *y2d, const float *origin)\n'
                    '{ return mu_world_item_out_of_view(x2d, y2d, origin); }\n')
    out = work / f'lib{name}.{SUFFIX}'
    result = subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wconversion', '-fPIC',
                             '-ffp-contract=off', '-shared', '-I', str(header_root), str(shim),
                             *map(str, objects), '-lm', '-o', str(out)], capture_output=True, text=True)
    if result.returncode:
        return None, result.stderr[-2000:]
    lib = ctypes.CDLL(str(out))
    P = ctypes.POINTER(ctypes.c_float)
    lib.shim_out_of_view.argtypes = [P, P, P]
    lib.shim_out_of_view.restype = ctypes.c_int
    return lib, None


def farr(values):
    return (ctypes.c_float * len(values))(*values)


def polygon(g):
    """A convex quadrilateral (tile units) around a centre, either winding."""
    cx, cy = g.uniform(20, 236), g.uniform(20, 236)
    angle, near, far, depth = g.uniform(0, 2 * math.pi), g.uniform(2, 8), g.uniform(8, 20), g.uniform(8, 24)
    local = [(-near, 0.0), (near, 0.0), (far, depth), (-far, depth)]
    if g.random() < 0.5:
        local.reverse()
    c, s = math.cos(angle), math.sin(angle)
    pts = [(cx + x * c - y * s, cy + x * s + y * c - depth / 2) for x, y in local]
    return [f32(p[0]) for p in pts], [f32(p[1]) for p in pts]


def cross(xs, ys, i, j, x, y):
    return (xs[i] - x) * (ys[j] - y) - (xs[j] - x) * (ys[i] - y)


def origins(g, xs, ys, count):
    """World-unit origins: around the polygon, on its -20 margin lines, and special values."""
    out = []
    for k in range(count):
        z = f32(g.uniform(-500, 500))
        pick = k % 10
        if pick < 2:   # inside: a convex combination of the corners
            w = [g.random() for _ in range(4)]
            x, y = (sum(a * b for a, b in zip(w, v)) / sum(w) for v in (xs, ys))
        elif pick < 4:
            x, y = g.uniform(min(xs) - 6, max(xs) + 6), g.uniform(min(ys) - 6, max(ys) + 6)
        elif pick < 9:
            i = g.randrange(4)
            j = (i + 3) % 4
            t = g.random()
            px, py = xs[i] + t * (xs[j] - xs[i]), ys[i] + t * (ys[j] - ys[i])
            ex, ey = xs[j] - xs[i], ys[j] - ys[i]
            length = math.hypot(ex, ey) or 1.0
            nx, ny = -ey / length, ex / length
            # d(P + u n) = d(P) + u * slope; solve for d = -20 + delta
            slope = cross(xs, ys, i, j, px + nx, py + ny) - cross(xs, ys, i, j, px, py)
            delta = g.choice([-1.5, -0.5, -0.05, -0.001, 0.0, 0.001, 0.05, 0.5, 1.5]) * g.random()
            u = (-20.0 + delta - cross(xs, ys, i, j, px, py)) / (slope or 1.0)
            x, y = px + u * nx, py + u * ny
        else:
            # world units: x * 0.01 of these overflows, underflows or stays NaN in single precision
            special = [float('nan'), float('inf'), -float('inf'), 0.0, -0.0, 3.0e38, -3.0e38, 1e-44]
            x = g.choice(special) if g.random() < 0.6 else f32(g.uniform(0, 25600))
            y = g.choice(special) if g.random() < 0.6 else f32(g.uniform(0, 25600))
            out.append((f32(x), f32(y), z))
            continue
        out.append((f32(x * 100.0), f32(y * 100.0), z))
    return out


def same_bits(a, b):
    return all(bits(p) == bits(q) for p, q in zip(a, b))


def flag_families(client, lib, cases, seed):
    g = random.Random(seed)
    fam = {'link_flag': {'cases': 0, 'mismatches': 0, 'clear': 0, 'copy_mismatches': 0},
           'part_flag': {'cases': 0, 'mismatches': 0, 'clear': 0, 'copy_mismatches': 0}}
    first = {}
    per_polygon = 50
    for start in range(0, cases, per_polygon):
        xs, ys = polygon(g)
        state = 6 if g.random() < 0.8 else 5
        client.setup(xs, ys, state)
        for origin in origins(g, xs, ys, min(per_polygon, cases - start)):
            junk = (f32(g.uniform(-1e4, 1e4)), f32(g.uniform(-1e4, 1e4)), f32(g.uniform(-1e4, 1e4)))
            mine = 0 if lib.shim_out_of_view(farr(xs), farr(ys), farr(list(origin))) else 1
            for name, copy in (('link_flag', client.link_copy), ('part_flag', client.part_copy)):
                f = fam[name]
                f['cases'] += 1
                error = copy(origin, junk)
                moved = client.vec(Client.OBJ + 0x158) if name == 'link_flag' else client.vec(Client.MODEL + 0x78)
                if error or not same_bits(moved, origin):
                    f['copy_mismatches'] += 1
                got, error = client.flag(Client.OBJ)
                f['clear'] += int(got == 0)
                if error or got != mine:
                    f['mismatches'] += 1
                    first.setdefault(name, {'xs': xs, 'ys': ys, 'state': state, 'origin': list(origin),
                                            'client': got, 'c': mine, 'error': error})
    for name, f in fam.items():
        f['mismatches'] += f['copy_mismatches']
        if name in first:
            f['first_mismatch'] = first[name]
    return fam


def region_graph(text, lo, hi):
    """Basic successors of every instruction in [lo, hi): fall-through and direct jump targets."""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = False
    succ, indirect = {}, []
    for ins in md.disasm(text[lo - TEXT_BASE:hi - TEXT_BASE], lo):
        nxt = ins.address + ins.size
        m, op = ins.mnemonic, ins.op_str
        if m == 'ret':
            succ[ins.address] = []
        elif m == 'jmp':
            succ[ins.address] = [int(op, 16)] if op.startswith('0x') else []
            if not op.startswith('0x'):
                indirect.append(ins.address)
        elif m.startswith('j') or m.startswith('loop'):
            succ[ins.address] = [nxt, int(op, 16)]
        else:
            succ[ins.address] = [nxt]
    return succ, indirect


def reaches(succ, start, target, avoid):
    seen, todo = {start}, [start]
    while todo:
        a = todo.pop()
        if a == target:
            return True
        for b in succ.get(a, []):
            if b != avoid and b not in seen and b in succ:
                seen.add(b)
                todo.append(b)
    return False


def order_family(text):
    out = {'cases': 0, 'mismatches': 0, 'checks': []}
    link, link_indirect = region_graph(text, LINK_COPY, LINK_CALL + 5)
    part, part_indirect = region_graph(text, PART_FN, PART_CALLS[1] + 5)
    checks = [('RenderLinkItem: origin copy reaches the RenderObjDraw call', reaches(link, LINK_COPY, LINK_CALL, None)),
              ('RenderLinkItem: no path to the call avoids the pose 0x012c6478',
               not reaches(link, LINK_COPY, LINK_CALL, LINK_POSE)),
              ('RenderLinkItem: no indirect jump between the copy and the call', not link_indirect)]
    # a switch's indirect jump has no direct successors here: it must itself lie behind the copy
    for jump in part_indirect:
        checks.append((f'RenderPartObject: the indirect jump {jump:#x} lies behind the origin copy',
                       not reaches(part, PART_FN, jump, PART_COPY)))
    for call in PART_CALLS:
        checks.append((f'RenderPartObject: the entry reaches {call:#x}', reaches(part, PART_FN, call, None)))
        checks.append((f'RenderPartObject: no path to {call:#x} avoids the origin copy',
                       not reaches(part, PART_FN, call, PART_COPY)))
    for label, ok in checks:
        out['cases'] += 1
        out['mismatches'] += int(not ok)
        out['checks'].append({'check': label, 'ok': ok})
    return out


def callers_family(text):
    target = RENDER_OBJ_DRAW
    found = {}
    for off in range(len(text) - 5):
        if text[off] == 0xe8:
            rel = struct.unpack_from('<i', text, off + 1)[0]
            if (TEXT_BASE + off + 5 + rel) & 0xffffffff == target:
                found[TEXT_BASE + off] = EXPECTED_CALLERS.get(TEXT_BASE + off, 'unexpected')
    ok = set(found) == set(EXPECTED_CALLERS)
    return {'cases': len(EXPECTED_CALLERS), 'mismatches': 0 if ok else len(set(found) ^ set(EXPECTED_CALLERS)),
            'sites': {f'{a:#010x}': name for a, name in sorted(found.items())}}


def mutations(client, objects, cases, seed, work):
    source = HEADER.read_text()
    results = {}
    for name, (old, new) in MUTANTS.items():
        count = source.count(old)
        if count != 1:
            raise SystemExit(f'mutant {name}: anchor matches {count} times, expected exactly once')
        root = work / f'm_{name}'
        (root / 'native/world').mkdir(parents=True)
        (root / 'native/world/world_item_pre.h').write_text(source.replace(old, new))
        os.symlink(ROOT / 'reconstructed', root / 'reconstructed')
        lib, error = build_c(work, root, objects, f'm_{name}')
        if lib is None:
            raise SystemExit(f'mutant {name} does not compile: {error}')
        fam = flag_families(client, lib, cases, seed)
        results[name] = sum(f['mismatches'] for f in fam.values())
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=3000, help='flag cases per family')
    parser.add_argument('--seed', type=int, default=0x1c411e5)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--text')
    parser.add_argument('--data')
    args = parser.parse_args(argv)
    text = pins.TEXT.read(args.text, exit=True)
    data = pins.DATA.read(args.data, exit=True)
    client = Client(text, data)
    work = Path(tempfile.mkdtemp(prefix='item-callers-'))
    try:
        objects = []
        for src in TERRAIN:
            obj = work / (Path(src).stem + '.o')
            result = subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-c', str(ROOT / src),
                                     '-o', str(obj)], capture_output=True, text=True)
            if result.returncode:
                raise SystemExit(f'{src}: {result.stderr[-2000:]}')
            objects.append(obj)
        lib, error = build_c(work, ROOT, objects, 'item_callers')
        if lib is None:
            raise SystemExit(error)
        families = flag_families(client, lib, args.cases, args.seed)
        families['order'] = order_family(text)
        families['callers'] = callers_family(text)
        report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': families}
        if args.mutations:
            report['mutants'] = mutations(client, objects, args.cases, args.seed, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + '\n')
    bad = sum(f['mismatches'] for f in report['families'].values())
    missed = [k for k, v in report.get('mutants', {}).items() if not v]
    summary = {k: {'cases': v['cases'], 'mismatches': v['mismatches']} for k, v in report['families'].items()}
    print(json.dumps({'families': summary, 'mutants': report.get('mutants')}))
    return 1 if bad or missed else 0


if __name__ == '__main__':
    sys.exit(main())
