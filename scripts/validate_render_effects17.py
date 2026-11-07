#!/usr/bin/env python3
"""RENDER-EFFECTS-017 original-instruction families and compiled production mutants.

* armour_create / armour_move / armour_render: the particle kinds the armour owner-effect programs of RENDER-ITEMS-002Q
  request, 0x810a/7, 0x810a/0xf and Spark03 0x7f26/0x26, through validate_particles' create (CreateParticle
  0x015ae7b0), move (MoveParticles 0x01616c80) and render (RenderParticles 0x0159123f) families against
  reconstructed/particles (armour_kinds.inc). The move family's records are drawn with the cases' boundary values
  (LifeTime 46/45/1, LifeTime / initial LifeTime 0.5, Scale 0.01 and 0.015) mixed in.
* raster_sample: native/core/mu_raster.c's texture lookup (native/tests/effects17_host.c) against the GL rule the
  native GL parts use, binary32 for binary32: GL_CLAMP bitmaps clamp to edge (both bilinear taps clamped into
  [0, size - 1]; nearest: the clamped texel), GL_REPEAT bitmaps wrap. Random textures 1..256 texels wide, coordinates
  inside, outside and on the half-texel edges.
* fog_sites: every instruction that names the fog flag 0x0bdc597c (the five stores, each of 0, and the wrappers'
  and the scene setup's gated reads), no pointer to it in the pinned text, data or third section, and every
  glEnable/glDisable(GL_FOG) call site: the wrappers' and the scene setup's are gated by the flag; the only
  ungated glEnable is world 0x1e's box fog 0x00d8cca8 (called once, from the render scene 0x0185916b).

No client bytes or decoded data are written by this tool.
"""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import random
import re
import struct
import subprocess
import sys
import tempfile
import time

import actor_machine as am
import pins
import validate_particles as pt
import validate_render_effects11 as re11

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'native'/'tests'))
ARMOUR_KINDS = [(0x810a, 7), (0x810a, 0xf), (0x7f26, 0x26)]
FOG_FLAG = 0x0bdc597c
GL_ENABLE_SLOT, GL_DISABLE_SLOT = 0x01a7c75c, 0x01a7c758
FOG_STORES = (0x01851c24, 0x018576de, 0x01857f0d, 0x018591af, 0x0185b124)
FOG_SCENE_ON, FOG_SCENE_OFF, FOG_SCENE_CALLER, FOG_SCENE_OFF_CALLER = 0x00d8cca8, 0x00d8cd12, 0x01859783, 0x01859cad
CLAMP, REPEAT, LINEAR, NEAREST = 0x2900, 0x2901, 0x2601, 0x2600

PT_MUTANTS = [
    # (name, file, old, new, family, kind) on reconstructed/particles
    ('admit_0xf', 'armour_kinds.inc', '(subtype == 7 || subtype == 0xf)', '(subtype == 7)', 'create', (0x810a, 0xf)),
    ('create7_velocity', 'armour_kinds.inc', 'p->velocity[1] = (float)(mu_pt_rand(h) % 5);',
     'p->velocity[1] = (float)(mu_pt_rand(h) % 3);', 'create', (0x810a, 7)),
    ('create_f_direction', 'armour_kinds.inc', '    copy3(p->velocity, p->angle);', '', 'create', (0x810a, 0xf)),
    ('create_f_angle', 'armour_kinds.inc', '    p->angle[0] = p->angle[1] = p->angle[2] = 0.0f;', '', 'create',
     (0x810a, 0xf)),
    ('create26_gravity', 'armour_kinds.inc', 'p->gravity = 2.5f;', 'p->gravity = 0.5f;', 'create', (0x7f26, 0x26)),
    ('create26_life', 'armour_kinds.inc', 'p->lifetime = mu_pt_rand(h) % 5 + 30;',
     'p->lifetime = mu_pt_rand(h) % 5 + 50;', 'create', (0x7f26, 0x26)),
    ('move7_gate', 'armour_kinds.inc', 'if (p->lifetime <= 45) {', 'if (p->lifetime < 45) {', 'move', (0x810a, 7)),
    ('move7_turn', 'armour_kinds.inc', '{-p->angle[0], -p->angle[1], -p->angle[2]}',
     '{p->angle[0], p->angle[1], p->angle[2]}', 'move', (0x810a, 7)),
    ('move7_kill_scale', 'armour_kinds.inc', '|| 0.0f >= p->scale)', '|| 0.0f > p->scale)', 'move', (0x810a, 7)),
    ('move7_light', 'armour_kinds.inc', 'p->light[k] = p->light[k] / 1.005f;', 'p->light[k] = p->light[k] / 1.05f;',
     'move', (0x810a, 7)),
    ('move_f_half', 'armour_kinds.inc', '(float)p->initial_lifetime > 0.5f)', '(float)p->initial_lifetime >= 0.5f)',
     'move', (0x810a, 0xf)),
    ('move_f_floor', 'armour_kinds.inc', '    if (0.0f > p->scale)\n        p->scale = 0.0f;\n', '', 'move',
     (0x810a, 0xf)),
    ('move_f_sink', 'armour_kinds.inc', 'p->velocity[2] = p->velocity[2] - 0.15f;',
     'p->velocity[2] = p->velocity[2] - 0.015f;', 'move', (0x810a, 0xf)),
    ('move26_damp', 'armour_kinds.inc', 'p->velocity[k] = p->velocity[k] * 0.85f;',
     'p->velocity[k] = p->velocity[k] * 0.8f;', 'move', (0x7f26, 0x26)),
    ('move26_fall', 'armour_kinds.inc', 'p->position[2] = p->position[2] - p->gravity;',
     'p->position[2] = p->position[2] + p->gravity;', 'move', (0x7f26, 0x26)),
    ('move26_kill', 'armour_kinds.inc', '        if (p->lifetime <= 0)\n            p->live = 0;\n        return;\n    }\n'
     '    if (p->subtype == 7)', '        if (p->lifetime < 0)\n            p->live = 0;\n        return;\n    }\n'
     '    if (p->subtype == 7)', 'move', (0x7f26, 0x26)),
]
RASTER_MUTANTS = [
    # (name, old, new) on native/core/mu_raster.c
    ('raster_wrap_tap', 'x1 = fu + 1.0 < 0.0 ? 0 : (fu + 1.0 >= w - 1 ? w - 1 : (long long)fu + 1);',
     'x1 = (x0 + 1) % w;'),
    ('raster_low_edge', 'y0 = fv < 0.0 ? 0 : (fv >= h - 1 ? h - 1 : (long long)fv);',
     'y0 = fv < 0.0 ? h - 1 : (fv >= h - 1 ? h - 1 : (long long)fv);'),
    ('raster_no_clamp', '    if (clamp) {\n        /* RENDER-EFFECTS-017', '    if (0) {\n        /* RENDER-EFFECTS-017'),
    ('raster_high_edge', 'x0 = fu < 0.0 ? 0 : (fu >= w - 1 ? w - 1 : (long long)fu);',
     'x0 = fu < 0.0 ? 0 : (fu >= w ? w - 1 : (long long)fu);'),
]


def check_anchors():
    """Every mutant anchor must occur exactly once in its file."""
    bad = [name for name, file, old, *_ in PT_MUTANTS
           if (ROOT/'reconstructed/particles'/file).read_text().count(old) != 1]
    raster = (ROOT/'native/core/mu_raster.c').read_text()
    return bad + [name for name, old, _ in RASTER_MUTANTS if raster.count(old) != 1]


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def fbits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


# ---------------------------------------------------------------- the armour particle kinds

# (LifeTime, initial LifeTime, Scale): 0x810a/7's gate at 45 and its kill at Scale 0 (0.01 - 0.01), 0x810a/0xf's
# half-life test (15 / 30) and its floor at 0, the last steps of all three
BOUNDARIES = [(45, 30, 1.0), (46, 30, 1.0), (15, 30, 0.01), (15, 30, 1.0), (16, 30, 0.005), (1, 30, 1.0),
              (2, 30, 0.01), (30, 60, 0.0149), (30, 0, 0.5), (1, 1, 0.015)]


def boundary_particle(rng, kind, base=pt.random_particle):
    p = base(rng, kind)
    if rng.random() < 0.6:
        p.lifetime, p.initial_lifetime, scale = rng.choice(BOUNDARIES)
        p.live, p.scale = 1, f32(scale)
    return p


def pt_family(text, data, lib, name, kinds, cases, report, seed='render-effects-017-'):
    saved = pt.KINDS, pt.OWNED_KINDS, pt.random_particle
    pt.KINDS, pt.OWNED_KINDS = kinds, set()
    pt.random_particle = lambda rng, kind: boundary_particle(rng, kind, saved[2])
    try:
        r = pt.Report()
        dict(pt.FAMILIES)[name](pt.PtMachine(text, data), lib, random.Random(seed + name), cases * len(kinds), r,
                                defaultdict(int))
    finally:
        pt.KINDS, pt.OWNED_KINDS, pt.random_particle = saved
    report.families['armour_' + name] = r.families[name]
    report.coverage['armour_' + name] = r.coverage.get(name, {})


# ---------------------------------------------------------------- the raster's texture lookup

def build_host(directory, raster=None):
    """effects17_host.c against the native libraries; raster: a mutated copy of mu_raster.c."""
    import test_render_effects17 as t
    return t.build_host(directory, raster)


def reference(w, h, wrap, filt, s, t, rgba):
    """GL texture lookup (binary32 as the raster's arithmetic): clamp to edge for GL_CLAMP, repeat for GL_REPEAT."""
    def texel(x, y):
        return rgba[4*(y*w + x):4*(y*w + x) + 4]
    if filt == NEAREST:
        x, y = math.floor(s * w), math.floor(t * h)
        if wrap == CLAMP:
            x, y = min(max(x, 0), w - 1), min(max(y, 0), h - 1)
        else:
            x, y = int(math.fmod(x, w)) % w, int(math.fmod(y, h)) % h
        return [f32(f32(c) / f32(255.0)) for c in texel(x, y)]
    u, v = f32(f32(s * f32(w)) - f32(0.5)), f32(f32(t * f32(h)) - f32(0.5))
    fu, fv = math.floor(u), math.floor(v)
    ax, ay = f32(u - fu), f32(v - fv)
    if wrap == CLAMP:
        x0, x1 = min(max(fu, 0), w - 1), min(max(fu + 1, 0), w - 1)
        y0, y1 = min(max(fv, 0), h - 1), min(max(fv + 1, 0), h - 1)
    else:
        x0, y0 = fu % w, fv % h
        x1, y1 = (x0 + 1) % w, (y0 + 1) % h
    out = []
    for k in range(4):
        p00, p10, p01, p11 = texel(x0, y0)[k], texel(x1, y0)[k], texel(x0, y1)[k], texel(x1, y1)[k]
        top = f32(p00 + f32(f32(p10 - p00) * ax))
        bottom = f32(p01 + f32(f32(p11 - p01) * ax))
        out.append(f32(f32(top + f32(f32(bottom - top) * ay)) / f32(255.0)))
    return out


def coordinate(rng, size):
    half = 0.5 / size
    return f32(rng.choice([rng.uniform(-0.5, 1.5), rng.uniform(0, 1), rng.uniform(0, 1), 0.0, -0.0, 1.0, half,
                           f32(half) - 1e-7, f32(half) + 1e-7, 1 - half, 1 - half - 1e-7, 1 - half + 1e-7,
                           rng.uniform(-half, half), rng.uniform(1 - half, 1 + half), -3.25, 2.75]))


def family_raster(host, rng, cases, report):
    rows, inputs = [], []
    for n in range(cases):
        w, h = rng.choice([1, 2, 3, 4, 8, 16, 64, 256]), rng.choice([1, 2, 4, 5, 32, 128])
        rgba = bytes(rng.choice([0, 255, rng.randrange(256)]) for _ in range(4*w*h))
        wrap, filt = rng.choice([CLAMP, CLAMP, REPEAT]), rng.choice([LINEAR, LINEAR, NEAREST])
        s, t = coordinate(rng, w), coordinate(rng, h)
        rows.append((w, h, wrap, filt, s, t, rgba))
        inputs.append(f'{w} {h} {wrap:x} {filt:x} {fbits(s):08x} {fbits(t):08x} {rgba.hex()}')
    p = subprocess.run([str(host), 'sample'], input='\n'.join(inputs) + '\n', capture_output=True, text=True)
    lines = p.stdout.splitlines()
    for n, (w, h, wrap, filt, s, t, rgba) in enumerate(rows):
        mine = [int(x, 16) for x in lines[n].split()] if n < len(lines) else None
        expect = [fbits(x) for x in reference(w, h, wrap, filt, s, t, rgba)]
        report.add('raster_sample', mine == expect, {'case': n, 'size': [w, h], 'wrap': hex(wrap), 'filter': hex(filt),
                                                     's': s, 't': t, 'mine': mine, 'expected': expect})
        edge = 'edge' if min(abs(s * w - 0.5), abs(s * w - w + 0.5)) < 0.5 or s < 0 or s > 1 else 'inside'
        report.cover('raster_sample', f"{'clamp' if wrap == CLAMP else 'repeat'} "
                                      f"{'linear' if filt == LINEAR else 'nearest'} {edge}")


# ---------------------------------------------------------------- the fog flag's sites

def family_fog(text, data, section3, report):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    def ins_at(address, count=1):
        o = address - am.TEXT_BASE
        return list(md.disasm(text[o:o + 16 * count], address, count=count))

    flag = struct.pack('<I', FOG_FLAG)
    refs, stores = [], []
    i = text.find(flag)
    while i >= 0:
        refs.append(am.TEXT_BASE + i)
        i = text.find(flag, i + 1)
    for site in refs:
        decoded = None
        for back in range(1, 9):
            got = ins_at(site - back)
            if got and got[0].address + got[0].size > site and f'[{FOG_FLAG:#x}]' in got[0].op_str:
                decoded = got[0]
                break
        text_ins = f'{decoded.mnemonic} {decoded.op_str}' if decoded else None
        if text_ins == f'mov byte ptr [{FOG_FLAG:#x}], 0':
            stores.append(decoded.address)
            kind = 'store 0'
            ok = True
        else:   # a read: movzx eax, byte [flag]; test eax, eax; je over push GL_FOG; call glEnable/glDisable
            follow = ins_at(decoded.address, 4) if decoded else []
            seq = [f'{x.mnemonic} {x.op_str}' for x in follow]
            ok = (len(seq) == 4 and seq[0] == f'movzx eax, byte ptr [{FOG_FLAG:#x}]' and seq[1] == 'test eax, eax'
                  and seq[2].startswith('je ') and seq[3] == 'push 0xb60')
            kind = 'gated read'
        report.add('fog_sites', ok, {'site': hex(site), 'instruction': text_ins})
        report.cover('fog_sites', kind)
    report.add('fog_sites', tuple(stores) == FOG_STORES, {'stores': [hex(x) for x in stores]})
    report.cover('fog_sites', 'the five stores')
    for name, blob in (('data', data), ('section3', section3)):
        report.add('fog_sites', blob.count(flag) == 0, {'pointer in': name, 'count': blob.count(flag)})
        report.cover('fog_sites', 'no pointer in ' + name)
    # every push GL_FOG; call [glEnable/glDisable] in the text
    push = bytes.fromhex('68600b0000')
    i, gl_sites = text.find(push), []
    while i >= 0:
        got = ins_at(am.TEXT_BASE + i, 2)
        if len(got) == 2 and got[1].mnemonic == 'call' and got[1].op_str in (f'dword ptr [{GL_ENABLE_SLOT:#x}]',
                                                                            f'dword ptr [{GL_DISABLE_SLOT:#x}]'):
            gl_sites.append((got[0].address, got[1].op_str == f'dword ptr [{GL_ENABLE_SLOT:#x}]'))
        i = text.find(push, i + 1)
    for address, enable in gl_sites:
        # gated: movzx eax, byte [flag]; test eax, eax; je (short) right before the push
        before = ins_at(address - 11, 3)
        gated = [f'{x.mnemonic} {x.op_str}' for x in before][:2] == [f'movzx eax, byte ptr [{FOG_FLAG:#x}]',
                                                                       'test eax, eax'] and \
            len(before) == 3 and before[2].mnemonic == 'je' and before[2].address + before[2].size == address
        if enable and not gated:
            ok = address == FOG_SCENE_ON + 3   # push ebp; mov ebp, esp; push GL_FOG: the box fog routine
            kind = 'ungated glEnable: world 0x1e box fog'
        else:
            ok = True
            kind = 'gated' if gated else 'ungated glDisable'
        report.add('fog_sites', ok, {'site': hex(address), 'enable': enable, 'gated': gated})
        report.cover('fog_sites', kind)
    callers, off = _callers(text, FOG_SCENE_ON), _callers(text, FOG_SCENE_OFF)
    world = ins_at(0x018596b4)
    ok = callers == [FOG_SCENE_CALLER] and off == [FOG_SCENE_OFF_CALLER] and bool(world) and \
        f'{world[0].mnemonic} {world[0].op_str}' == 'cmp dword ptr [0x1cf15fc], 0x1e'
    report.add('fog_sites', ok, {'box fog callers': [hex(c) for c in callers], 'off callers': [hex(c) for c in off]})
    report.cover('fog_sites', 'box fog: one caller, world 0x1e')


def _callers(text, target):
    """Every E8 rel32 call site of target."""
    out = []
    for m in re.finditer(b'\xe8', text):
        j = m.start()
        if j + 5 <= len(text) and am.TEXT_BASE + j + 5 + struct.unpack_from('<i', text, j + 1)[0] == target:
            out.append(am.TEXT_BASE + j)
    return out


# ---------------------------------------------------------------- main

def run_families(text, data, section3, plib, host, cases, report, seed='render-effects-017-', only=None):
    for name in ('create', 'move', 'render'):
        if not only or only == 'armour_' + name:
            pt_family(text, data, plib, name, ARMOUR_KINDS, cases, report, seed)
    if not only or only == 'raster_sample':
        family_raster(host, random.Random(seed + 'raster'), cases * 20, report)
    if not only or only == 'fog_sites':
        family_fog(text, data, section3, report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=20, help='cases per armour kind and family (x20 raster lookups)')
    p.add_argument('--mutations', action='store_true')
    p.add_argument('--output')
    a = p.parse_args()
    if a.cases < 1:
        p.error('--cases must be positive')
    bad = check_anchors()
    if bad:
        raise SystemExit(f'mutant anchors not unique: {bad}')
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    section3 = pins.SECTION3.read(exit=True)
    start = time.monotonic()
    plib = pt.load_library(ROOT/f'reconstructed/particles/libclient_particles.{re11.fx.SUFFIX}')
    report = pt.Report()
    mutants = []
    with tempfile.TemporaryDirectory(prefix='effects17-') as tmp:
        host = build_host(tmp)
        run_families(text, data, section3, plib, host, a.cases, report)
        equal = all(f['equal'] == f['cases'] for f in report.families.values())
        print(json.dumps(dict(instruction_cases=sum(f['cases'] for f in report.families.values()), all_equal=equal,
                              families={k: (v['cases'], v['equal']) for k, v in report.families.items()})), flush=True)
        if a.mutations and equal:
            def record(name, family, rr):
                f = rr.families[family]
                mutants.append(dict(name=name, family=family, cases=f['cases'], detected=f['cases'] - f['equal'],
                                    stopped=sum(bool(x.get('stopped')) for x in f['first_failures'])))
                print('mutant', json.dumps(mutants[-1]), flush=True)
            for name, file, old, new, family, kind in PT_MUTANTS:
                ml = re11.compile_pt_mutant(tmp, name, file, old, new)
                rr = pt.Report()
                pt_family(text, data, ml, family, [kind], max(120, a.cases), rr, 'render-effects-017-mutant-')
                record(name, 'armour_' + family, rr)
            for name, old, new in RASTER_MUTANTS:
                work = Path(tmp)/name
                work.mkdir()
                source = (ROOT/'native/core/mu_raster.c').read_text()
                (work/'mu_raster.c').write_text(source.replace(old, new))
                mh = build_host(work, work/'mu_raster.c')
                rr = pt.Report()
                family_raster(mh, random.Random('render-effects-017-mutant-raster'), max(400, a.cases * 20), rr)
                record(name, 'raster_sample', rr)
    result = dict(families=report.families, coverage=report.coverage,
                  instruction_cases=sum(f['cases'] for f in report.families.values()), all_equal=equal,
                  mutants=mutants, all_mutants_caught=all(x['detected'] and not x['stopped'] for x in mutants),
                  seconds=round(time.monotonic() - start, 3), text_sha256=am.TEXT_SHA256, data_sha256=am.DATA_SHA256)
    if a.output:
        Path(a.output).write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k not in ('families', 'coverage')}, indent=1))
    if not equal:
        for name, f in report.families.items():
            for failure in f['first_failures'][:3]:
                print(name, str(failure)[:1500])
    return 0 if equal and result['all_mutants_caught'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
