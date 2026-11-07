#!/usr/bin/env python3
"""RENDER-EFFECTS-021 original-instruction families and compiled production mutants.

* pre_create / pre_move / pre_render: the three particle kinds the item pre-draw programs create without an owner
  (RenderObjDraw's own case, item_owner_fx.h op 14) that no pool reconstructed before: Clud64 0x7ffd/0x1b (bow
  0x1316), Shiny01 0x7f66/5 (0x230c, 0x2496) and shiny06 0x8180/5 (0x23ef, 0x2400, 0x2405), through
  validate_particles' create (CreateParticle 0x015ae7b0), move (MoveParticles 0x01616c80) and render
  (RenderParticles 0x0159123f) families against reconstructed/particles (item_predraw_kinds.inc). The move family's
  records take boundary values (LifeTime 1/2/15 against initial LifeTimes 15, 1, 0 and -1).
* tables: shiny06 subtype 5 has no block: the jump tables of CreateParticle's 0x8180 case (0x016167a0),
  MoveParticles' (0x0168f700) and RenderParticles' (0x015ae50f) send index 5 straight to each switch's end
  (0x015e93ab, 0x0165c194, 0x0159a5a6), and the three type dispatches reach those cases for 0x8180. Shiny01's move
  case (0x016584c2) has no head before its subtype chain, Clud64's create reaches 0x1b's block at 0x015c304a.
* owner_host: the armour owner-effect programs (RENDER-ITEMS-002Q) in the world. The real 0x012b678d(out, OBJECT,
  bone, local) (thiscall on the part model) runs with an OBJECT whose +0x5c names the player model (bone count
  through 0x00966cc4 / 0x00eaa8cf), +0x318 points at posed bone matrices (0x0129f12c), +0x158 is its position, and
  the part model's +0x22 / +0x74 are its bone count and scale. Random rotations, translations, local points, scales
  and positions. The native world host (world_rt_part_owner: the character's player_bones as +0x318, the Player.bmd
  bone count, the part model's bone count, body scale and origin) transforms with mu_pt_transform_position
  (mu_renderchar owner_transform); inside both bone domains the outputs must be equal bit for bit. Outside: a bone
  at or above the part model's count leaves out unwritten (native: no request); a bone at or above the player
  model's count, or +0x318 = 0, makes the client read BoneTransform 0x06fce398 (here other matrices, so the case
  proves the source), which the native host refuses (owner_fx: the program's highest bone must be below both).

No client bytes or decoded data are written by this tool.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import random
import struct
import tempfile
import time

import actor_machine as am
import pins
import validate_particles as pt
import validate_render_effects11 as re11

ROOT = Path(__file__).resolve().parents[1]
PRE_KINDS = [(0x7ffd, 0x1b), (0x7f66, 5), (0x8180, 5)]

MUTANTS = [
    # (name, old, new, family, kind) on reconstructed/particles/item_predraw_kinds.inc
    ('admit_clud', '(type == 0x7ffd && subtype == 0x1b)', '(type == 0x7ffd && subtype == 0x1c)', 'create',
     (0x7ffd, 0x1b)),
    ('admit_shiny06', '(type == 0x8180 && subtype == 5)', '(type == 0x8180 && subtype == 6)', 'create',
     (0x8180, 5)),
    ('clud_life', 'p->initial_lifetime = 15;', 'p->initial_lifetime = 16;', 'create', (0x7ffd, 0x1b)),
    ('clud_rotation', 'p->rotation = (float)(mu_pt_rand(h) % 360);', 'p->rotation = (float)(mu_pt_rand(h) % 180);',
     'create', (0x7ffd, 0x1b)),
    ('clud_alpha', '        p->alpha = 1.0f;\n', '        p->alpha = 0.5f;\n', 'create', (0x7ffd, 0x1b)),
    ('clud_velocity', 'p->velocity[k] = rand_range(h, -0.5f, 0.5f, 1);', 'p->velocity[k] = rand_range(h, -0.5f, 1.5f, 1);',
     'create', (0x7ffd, 0x1b)),
    ('shiny_angle', 'p->angle[0] = 45.0f;', 'p->angle[0] = 0.0f;', 'create', (0x7f66, 5)),
    ('shiny_life', 'p->lifetime = mu_pt_rand(h) % 10 + 10;', 'p->lifetime = mu_pt_rand(h) % 10 + 11;', 'create',
     (0x7f66, 5)),
    ('shiny_scale', '* 0.02f + scale;', '* 0.02f;', 'create', (0x7f66, 5)),
    ('shiny_jitter', 'p->position[1] = (float)(mu_pt_rand(h) % 10 - 5) + p->position[1];',
     'p->position[1] = (float)(mu_pt_rand(h) % 10 - 5) + p->position[0];', 'create', (0x7f66, 5)),
    ('shiny_gravity', 'p->gravity = -(float)(mu_pt_rand(h) % 10) * 0.3f;',
     'p->gravity = (float)(mu_pt_rand(h) % 10) * 0.3f;', 'create', (0x7f66, 5)),
    ('clud_fade', 'p->alpha = (float)p->lifetime / (float)p->initial_lifetime;',
     'p->alpha = (float)(p->lifetime - 1) / (float)p->initial_lifetime;', 'move', (0x7ffd, 0x1b)),
    ('clud_grow', 'p->scale = p->scale + 0.04f;', 'p->scale = p->scale + 0.03f;', 'move', (0x7ffd, 0x1b)),
    ('shiny_spin', 'p->rotation = p->rotation + 10.0f;', 'p->rotation = p->rotation - 10.0f;', 'move', (0x7f66, 5)),
    ('shiny_rise', 'p->position[2] = p->position[2] + p->gravity;', 'p->position[2] = p->position[2] - p->gravity;',
     'move', (0x7f66, 5)),
    ('shiny_dim', 'p->light[k] = p->light[k] / 1.02f;', 'p->light[k] = p->light[k] * 0.98f;', 'move', (0x7f66, 5)),
    ('shiny_shrink', 'p->scale = p->scale - 0.01f;', 'p->scale = p->scale - 0.02f;', 'move', (0x7f66, 5)),
    ('render_clud_alpha', 'for (int k = 0; k < 3; ++k) s->light[k] = p->light[k] * p->alpha;',
     'for (int k = 0; k < 2; ++k) s->light[k] = p->light[k] * p->alpha;', 'render', (0x7ffd, 0x1b)),
    ('render_shiny06_draws', 'return !(p->type == 0x8180 && p->subtype == 5);', 'return 1;', 'render', (0x8180, 5)),
]


def check_anchors():
    """Every mutant anchor must occur exactly once in its file."""
    source = (ROOT/'reconstructed/particles/item_predraw_kinds.inc').read_text()
    return [name for name, old, *_ in MUTANTS if source.count(old) != 1]


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


# ---------------------------------------------------------------- the three kinds

# (LifeTime, initial LifeTime): Clud64's fade at its first and last steps, an initial LifeTime of 0 and -1
BOUNDARIES = [(15, 15), (1, 15), (2, 15), (7, 15), (1, 1), (3, 0), (2, -1), (2, 2), (19, 30)]


def boundary_particle(rng, kind, base=pt.random_particle):
    p = base(rng, kind)
    if rng.random() < 0.6:
        p.lifetime, p.initial_lifetime = rng.choice(BOUNDARIES)
        p.live = 1
    return p


def pt_family(text, data, lib, name, kinds, cases, report, seed='render-effects-021-'):
    saved = pt.KINDS, pt.OWNED_KINDS, pt.random_particle
    pt.KINDS, pt.OWNED_KINDS = kinds, set()
    pt.random_particle = lambda rng, kind: boundary_particle(rng, kind, saved[2])
    try:
        r = pt.Report()
        dict(pt.FAMILIES)[name](pt.PtMachine(text, data), lib, random.Random(seed + name), cases * len(kinds), r,
                                defaultdict(int))
    finally:
        pt.KINDS, pt.OWNED_KINDS, pt.random_particle = saved
    report.families['pre_' + name] = r.families[name]
    report.coverage['pre_' + name] = r.coverage.get(name, {})


# ---------------------------------------------------------------- tables

def family_tables(text, data, report):
    """The switch tables and dispatch targets named in item_predraw_kinds.inc."""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    def dword(a):
        if am.TEXT_BASE <= a < am.TEXT_BASE + len(text):
            return struct.unpack_from('<I', text, a - am.TEXT_BASE)[0]
        return struct.unpack_from('<I', data, a - am.DATA_BASE)[0]

    def ins(a, n=1):
        return list(md.disasm(text[a - am.TEXT_BASE:a - am.TEXT_BASE + 16 * n], a))[:n]

    # (name, table, index, expected target, switch head, the bound compare)
    for name, table, end, head in (('create', 0x016167a0, 0x015e93ab, 0x015e89c6),
                                   ('move', 0x0168f700, 0x0165c194, 0x0165b814),
                                   ('render', 0x015ae50f, 0x0159a5a6, 0x0159a3c5)):
        heads = ins(head, 6)
        ok = dword(table + 4 * 5) == end and heads[0].op_str == 'eax, dword ptr [eax + 0x14]' and \
            heads[2].op_str.endswith(', 8') and heads[3].mnemonic == 'ja' and int(heads[3].op_str, 16) == end and \
            heads[5].op_str == f'dword ptr [eax*4 + {table:#x}]'
        # the end is a plain jump to the switch's tail, and index 5 is the only entry that goes there
        tail = ins(end)[0]
        others = [k for k in range(9) if k != 5 and dword(table + 4 * k) == end]
        ok = ok and tail.mnemonic == 'jmp' and not others
        report.add('tables', ok, {'switch': name, 'table': hex(table), 'entry5': hex(dword(table + 20)),
                                  'tail': f'{tail.mnemonic} {tail.op_str}', 'others': others})
        report.cover('tables', f'0x8180/5 {name}')
    # the type dispatches reach the 0x8180 cases (create: the case at 0x015e89bb loads the subtype at 0x015e89c6)
    checks = [(0x0161737c, 'move', 'dword ptr [ebp - 0x5c], 0x8180', 0x0165b809),
              (0x01591a2b, 'render', 'dword ptr [ebp - 0x20], 0x8180', 0x0159a3bd)]
    for at, name, operand, target in checks:
        cmp_, je = ins(at, 2)
        ok = cmp_.op_str == operand and je.mnemonic == 'je' and int(je.op_str, 16) == target
        report.add('tables', ok, {'dispatch': name, 'site': hex(at)})
        report.cover('tables', f'0x8180 {name} dispatch')
    # Shiny01's move case: the table target is the subtype chain's first compare (no common head)
    first = ins(0x016584c2, 3)
    ok = [x.mnemonic for x in first] == ['lea', 'call', 'cmp'] and first[2].op_str == 'dword ptr [eax + 0x14], 2'
    report.add('tables', ok, {'case': '0x7f66 move', 'first': [f'{x.mnemonic} {x.op_str}' for x in first]})
    report.cover('tables', '0x7f66 move head')
    # Clud64's 0x1b block: the compare, LifeTime 15 into +0x4c, and the end jump to CreateParticle's tail
    block = ins(0x015c3040, 4)
    ok = block[0].op_str == 'dword ptr [eax + 0x14], 0x1b' and block[1].mnemonic == 'jne' and \
        int(block[1].op_str, 16) == 0x015c3207 and ins(0x015c3207)[0].op_str == '0x1615f0a' and \
        ins(0x015c3055)[0].op_str == 'dword ptr [eax + 0x4c], 0xf'
    report.add('tables', ok, {'case': '0x7ffd/0x1b block'})
    report.cover('tables', '0x7ffd/0x1b block')


# ---------------------------------------------------------------- owner host

def family_owner_host(cases, report, plib):
    import ctypes as C
    import renderchar_machine as machine
    import validate_renderchar as v
    plib.mu_pt_transform_position.argtypes = [C.POINTER(C.c_float)] * 3 + [C.c_int, C.c_float, C.POINTER(C.c_float)]
    plib.mu_pt_transform_position.restype = None
    w = v.World(*(pin.read() for pin in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE)))
    m = w.m
    F3, F12 = C.c_float * 3, C.c_float * 12
    rng = random.Random('render-effects-021-owner-host')
    pose_global = 0x06fce398
    m.ensure(pose_global, 0x30 * 200)
    out, local_at = v.LIGHT, v.LIGHT + 0x100

    def matrix(r):
        a, b, c = (r.uniform(-180, 180) for _ in range(3))
        import math
        ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
        rot = [cb * cc, -cb * sc, sb, sa * sb * cc + ca * sc, ca * cc - sa * sb * sc, -sa * cb,
               -ca * sb * cc + sa * sc, ca * sb * sc + sa * cc, ca * cb]
        t = [r.uniform(-150, 150) for _ in range(3)]
        return [f32(x) for x in rot[0:3] + [t[0]] + rot[3:6] + [t[1]] + rot[6:9] + [t[2]]]
    for n in range(cases):
        item_bones = rng.choice([4, 27, 36, 60, 60, 61])
        owner_bones = rng.choice([27, 36, 60, 60, 61])
        attached = rng.random() > 0.1
        bone = rng.choice([rng.randrange(0, 61), 0, 19, 26, 35, item_bones - 1, item_bones, owner_bones - 1,
                           owner_bones, -1])
        scale = f32(rng.choice([1.0, 1.2, 0.9, rng.uniform(0.1, 3.0)]))
        position = [f32(rng.uniform(0, 25600)), f32(rng.uniform(0, 25600)), f32(rng.uniform(-100, 800))]
        local = [f32(rng.uniform(-60, 60)) for _ in range(3)]
        bones = [matrix(rng) for _ in range(64)]
        stale = [matrix(rng) for _ in range(64)]
        w.models.clear()
        w.add_model(0x1bc3, v.MODEL, bones=item_bones)
        w.add_model(0xa91, v.PLAYER_MODEL, bones=owner_bones)
        m.wf(v.MODEL + 0x74, scale)
        obj = bytearray(0x400)
        struct.pack_into('<i', obj, 0x5c, 0xa91)
        struct.pack_into('<3f', obj, 0x158, *position)
        struct.pack_into('<I', obj, 0x318, v.BONES if attached else 0)
        m.write(v.OBJ, bytes(obj))
        m.write(v.BONES, b''.join(struct.pack('<12f', *b) for b in bones))
        m.write(pose_global, b''.join(struct.pack('<12f', *b) for b in stale))
        sentinel = struct.pack('<3I', 0x7fc0dead, 0x7fc0beef, 0x7fc0f00d)
        m.write(out, sentinel)
        m.write(local_at, struct.pack('<3f', *local))
        result = m.run(0x012b678d, [out, v.OBJ, bone, local_at], v.MODEL)
        checks = dict(result['checks'])
        checks['esp'] = m.uc.reg_read(m.x86.UC_X86_REG_ESP) == machine.ENTRY_ESP + 20
        client = m.read(out, 12)
        # the native world host: owner_fx runs only inside both bone domains (owner_transform otherwise unused)
        native_runs = 0 <= bone < item_bones and bone < owner_bones and attached
        if native_runs:
            o = F3()
            plib.mu_pt_transform_position(F12(*bones[bone]), F3(*local), o, 1, scale, F3(*position))
            expected, mode = bytes(o), 'owner bones'
        elif bone < 0 or bone >= item_bones:
            expected, mode = sentinel, 'outside the part model: unwritten, native refuses'
        else:
            o = F3()
            plib.mu_pt_transform_position(F12(*stale[bone]), F3(*local), o, 1, scale, F3(*position))
            expected, mode = bytes(o), 'BoneTransform fallback: native refuses'
        ok = not result['error'] and not result['stopped'] and all(checks.values()) and client == expected
        report.add('owner_host', ok, {'case': n, 'bone': bone, 'item_bones': item_bones, 'owner_bones': owner_bones,
                                      'attached': attached, 'mode': mode, 'client': client.hex(),
                                      'expected': expected.hex(), 'checks': checks, 'error': result['error']})
        report.cover('owner_host', mode)


# ---------------------------------------------------------------- main

def run_families(text, data, plib, cases, report):
    for name in ('create', 'move', 'render'):
        pt_family(text, data, plib, name, PRE_KINDS, cases, report)
    family_tables(text, data, report)
    family_owner_host(max(20, cases * 4), report, plib)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=100, help='cases per kind and family')
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
    start = time.monotonic()
    plib = pt.load_library(ROOT/f'reconstructed/particles/libclient_particles.{re11.fx.SUFFIX}')
    report = pt.Report()
    run_families(text, data, plib, a.cases, report)
    equal = all(f['equal'] == f['cases'] for f in report.families.values())
    print(json.dumps(dict(instruction_cases=sum(f['cases'] for f in report.families.values()), all_equal=equal,
                          families={k: (v['cases'], v['equal']) for k, v in report.families.items()})), flush=True)
    mutants = []
    if a.mutations and equal:
        with tempfile.TemporaryDirectory(prefix='effects21-') as tmp:
            for name, old, new, family, kind in MUTANTS:
                ml = re11.compile_pt_mutant(tmp, name, 'item_predraw_kinds.inc', old, new)
                rr = pt.Report()
                pt_family(text, data, ml, family, [kind], max(120, a.cases), rr, 'render-effects-021-mutant-')
                f = rr.families['pre_' + family]
                mutants.append(dict(name=name, family='pre_' + family, cases=f['cases'],
                                    detected=f['cases'] - f['equal'],
                                    stopped=sum(bool(x.get('stopped')) for x in f['first_failures'])))
                print('mutant', json.dumps(mutants[-1]), flush=True)
    result = dict(families=report.families, coverage=report.coverage,
                  instruction_cases=sum(f['cases'] for f in report.families.values()), all_equal=equal,
                  mutants=mutants, all_mutants_caught=all(x['detected'] and not x['stopped'] for x in mutants),
                  seconds=round(time.monotonic() - start, 3), text_sha256=am.TEXT_SHA256, data_sha256=am.DATA_SHA256)
    if a.output:
        Path(a.output).write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k not in ('families',)}, indent=1))
    if not equal:
        for name, f in report.families.items():
            for failure in f['first_failures'][:3]:
                print(name, str(failure)[:1500])
    return 0 if equal and result['all_mutants_caught'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
