#!/usr/bin/env python3
"""RENDER-EFFECTS-020 original-instruction families and compiled production mutants.

* item_create / item_move / item_render: the two particle kinds the wings 0x2384/0x2385 create with their OBJECT as
  owner (RenderObjDraw's pre-draw case, item_owner_fx.h op 25), 0x810a/0x11 and 0x81cf/0, through validate_particles'
  create (CreateParticle 0x015ae7b0), move (MoveParticles 0x01616c80) and render (RenderParticles 0x0159123f)
  families against reconstructed/particles (item_owned_kinds.inc). Owners are NULL or an OBJECT whose only defined
  bytes are +0x158, +0x0b and +0x68 (a read of any other owner byte is an undefined read and fails the case); the
  move family's records take the cases' boundary values (LifeTime 10/9 against the half of 20, 1 and 0).
* owner_reads: the bytes of the owner OBJECT each kind's create and move read, recorded under Unicorn: only +0x158
  (the common owner block, 0x01616fee..0x01617071 / 0x015aeb5e..0x015aebd6), never the angle +0x164, the bones
  +0x318, the scale or the live/visible bytes.
* link_angle: every store to RenderLinkItem's link OBJECT +0x164 ([ebp-0x120] + 0x164 through 0x00cfc922) between
  its entry 0x012bd910 and the RenderObjDraw call 0x012c6a83 writes 0.0 (eleven stores), except type 0x44f's z
  (WorldTime); no other form addresses +0x164 there. A worn 0x2384/0x2385 passes the angle (0, 0, 0) to its particles.
* bitmap: the startup LoadBitmap 0x0185baac call at 0x018249a3 for 0x81cf (Effect\\magic_ground12.JPG, GL_LINEAR,
  GL_CLAMP), the world particle pool's new slot.

No client bytes or decoded data are written by this tool.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import random
import struct
import sys
import tempfile
import time

import actor_machine as am
import pins
import validate_particles as pt
import validate_render_effects11 as re11

ROOT = Path(__file__).resolve().parents[1]
ITEM_KINDS = [(0x810a, 0x11), (0x81cf, 0)]
LINK_ITEM, LINK_CALL, LINK_OBJECT_ANGLE_GET, LINK_OBJECT_CONST_GET = 0x012bd910, 0x012c6a83, 0x00cfc922, 0x00cfc94a
REGISTRATION = (0x0182498b, 0x018249a3, 0x81cf, 'Effect\\magic_ground12.JPG')

MUTANTS = [
    # (name, old, new, family, kind) on reconstructed/particles/item_owned_kinds.inc
    ('admit_17', '(type == 0x810a && subtype == 0x11)', '(type == 0x810a && subtype == 0x12)', 'create', (0x810a, 0x11)),
    ('create17_scale', 'p->scale = rand_range(h, 0.5f, 1.0f, 100) * scale;',
     'p->scale = rand_range(h, 0.5f, 1.0f, 10) * scale;', 'create', (0x810a, 0x11)),
    ('create17_jitter', 'p->position[k] = rand_range(h, -10.0f, 10.0f, 1) + p->position[k];',
     'p->position[k] = rand_range(h, -10.0f, 10.0f, 1);', 'create', (0x810a, 0x11)),
    ('create17_velocity', 'rand_range(h, -15.0f, 15.0f, 1) * 0.2f;', 'rand_range(h, -15.0f, 15.0f, 1) * 0.25f;',
     'create', (0x810a, 0x11)),
    ('create17_life', '    p->initial_lifetime = 30;', '    p->initial_lifetime = 20;', 'create', (0x810a, 0x11)),
    ('create0_scale', '        p->scale = 0.0f;\n        p->alpha = 1.0f;', '        p->scale = scale;\n        p->alpha = 1.0f;',
     'create', (0x81cf, 0)),
    ('create0_keep', '        p->initial_scale = scale;', '        p->initial_scale = 1.0f;', 'create', (0x81cf, 0)),
    ('move0_owner', '            p->live = 0;\n            return;', '            p->live = 1;\n            return;',
     'move', (0x81cf, 0)),
    ('move0_grow', 'p->scale = p->initial_scale / (float)p->initial_lifetime + p->scale;',
     'p->scale = p->initial_scale / (float)p->lifetime + p->scale;', 'move', (0x81cf, 0)),
    ('move0_half', 'if (p->lifetime < half)', 'if (p->lifetime <= half)', 'move', (0x81cf, 0)),
    ('move0_fade', 'p->alpha = p->alpha - 1.0f / (float)half;', 'p->alpha = p->alpha - 1.0f / (float)p->initial_lifetime;',
     'move', (0x81cf, 0)),
    ('move17_shrink', 'p->scale = p->scale - p->initial_scale / (float)p->initial_lifetime;',
     'p->scale = p->scale - p->initial_scale / (float)p->lifetime;', 'move', (0x810a, 0x11)),
    ('move17_fade', '    p->alpha = p->alpha - 1.0f / (float)p->initial_lifetime;\n}',
     '    p->alpha = p->alpha - 0.5f / (float)p->initial_lifetime;\n}', 'move', (0x810a, 0x11)),
    ('render_alpha', 'for (int k = 0; k < 3; ++k) s->light[k] = p->light[k] * p->alpha;',
     'for (int k = 0; k < 2; ++k) s->light[k] = p->light[k] * p->alpha;', 'render', (0x81cf, 0)),
]


def check_anchors():
    """Every mutant anchor must occur exactly once in its file."""
    source = (ROOT/'reconstructed/particles/item_owned_kinds.inc').read_text()
    return [name for name, old, *_ in MUTANTS if source.count(old) != 1]


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


# ---------------------------------------------------------------- the two kinds

# (LifeTime, initial LifeTime, Scale): 0x81cf/0's half-life test (10 against 20 / 2), odd and tiny initial
# LifeTimes (the integer half), the last steps
BOUNDARIES = [(10, 20, 0.5), (9, 20, 0.5), (11, 20, 0.0), (1, 20, 1.0), (2, 30, 0.01), (15, 30, 1.0),
              (3, 7, 0.2), (1, 1, 0.5), (1, 3, 0.1), (5, 0, 0.5), (30, 30, 1.0)]


def boundary_particle(rng, kind, base=pt.random_particle):
    p = base(rng, kind)
    if rng.random() < 0.6:
        p.lifetime, p.initial_lifetime, scale = rng.choice(BOUNDARIES)
        p.live, p.scale = 1, f32(scale)
    return p


def pt_family(text, data, lib, name, kinds, cases, report, seed='render-effects-020-'):
    saved = pt.KINDS, pt.OWNED_KINDS, pt.random_particle
    pt.KINDS, pt.OWNED_KINDS = kinds, set()
    pt.random_particle = lambda rng, kind: boundary_particle(rng, kind, saved[2])
    try:
        r = pt.Report()
        dict(pt.FAMILIES)[name](pt.PtMachine(text, data), lib, random.Random(seed + name), cases * len(kinds), r,
                                defaultdict(int))
    finally:
        pt.KINDS, pt.OWNED_KINDS, pt.random_particle = saved
    report.families['item_' + name] = r.families[name]
    report.coverage['item_' + name] = r.coverage.get(name, {})


# ---------------------------------------------------------------- owner reads

def family_owner_reads(text, data, lib, cases, report):
    """Each kind's create and move with an owner OBJECT: the owner bytes read (only +0x158..+0x163)."""
    from unicorn import UC_HOOK_MEM_READ
    m = pt.PtMachine(text, data)
    reads = []

    def hook(uc, access, address, size, value, user):
        reads.append((address - pt.OBJECTS, size))
    m.uc.hook_add(UC_HOOK_MEM_READ, hook, begin=pt.OBJECTS, end=pt.OBJECTS + 0x3ff)
    rng = random.Random('render-effects-020-owner-reads')
    for n in range(cases):
        kind = ITEM_KINDS[n % len(ITEM_KINDS)]
        case = pt.Case(rng, height=rng.uniform(-50, 400), owners=[[pt.rf(rng, 0, 25600), pt.rf(rng, 0, 25600), 150.0]])
        for mode in ('create', 'move'):
            reads.clear()
            if mode == 'create':
                inputs = am.defined_region('inputs', pt.INPUTS, struct.pack('<9f', *[pt.rf(rng, 0, 25600)] * 3,
                                                                         *[0.0] * 3, *[1.0] * 3), writable=False)
                record = am.defined_region('particle', pt.PARTICLE, am.poison(pt.PARTICLE_BYTES, 0x5d))
                r = m.execute(pt.CREATE_CORE, [kind[0], pt.INPUTS, pt.INPUTS + 12, pt.INPUTS + 24, kind[1],
                                               struct.unpack('<I', struct.pack('<f', 1.0))[0], pt.object_address(0), 0],
                              [inputs, record] + pt.globals_region() + case.owner_regions(), pt.shared_stubs(case, m),
                              ecx=pt.POOL, cleanup=0x20)
            else:
                p = boundary_particle(rng, kind)
                p.live, p.owner = 1, 0
                p.lifetime = max(p.lifetime, 1)
                list_state = am.defined_region('list-wind', 0x29000000, bytes(0x20))
                stubs = pt.shared_stubs(case, m, {0x0168ee7d: pt.jump_stub(0x0168eea4),
                                                  pt.BITMAP_RECORD_GET: case.bitmap_stub()})
                r = m.execute(0x01616f7c, [], [list_state, pt.particle_region(lib, p), case.bitmap_region()] +
                              pt.globals_region() + case.owner_regions(), stubs, ecx=pt.POOL,
                              frame=pt.mid_frame(pt.MOVE_FRAME, {-0x38: 7, -0x14: 0x29000000}))
            offsets = sorted({a + k for a, s in reads for k in range(s)})
            ok = pt.vc.ok(r) and offsets == list(range(0x158, 0x164))
            report.add('owner_reads', ok, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mode': mode,
                                           'offsets': [hex(x) for x in offsets], 'stopped': r['stopped']})
            report.cover('owner_reads', f'{kind[0]:#x}/{kind[1]} {mode}')


# ---------------------------------------------------------------- link angle

def family_link_angle(text, report):
    """RenderLinkItem's stores to the link OBJECT's +0x164 before RenderObjDraw."""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    code = text[LINK_ITEM - am.TEXT_BASE:LINK_CALL + 5 - am.TEXT_BASE]
    ins = list(md.disasm(code, LINK_ITEM))
    count, stores = 0, []
    for i in range(len(ins) - 6):
        if not (ins[i].mnemonic == 'mov' and ins[i].op_str == 'ecx, dword ptr [ebp - 0x120]' and
                ins[i + 1].op_str == 'ecx, 0x164'):
            continue
        element = ins[i - 1].op_str if ins[i - 1].mnemonic == 'push' else None
        tail = [f'{x.mnemonic} {x.op_str}' for x in ins[i + 3:i + 5]]
        if ins[i + 2].op_str == hex(LINK_OBJECT_CONST_GET) and tail[0] == 'push eax':
            value = 'read'   # the const accessor, passed by pointer (Animation's angle argument)
        elif ins[i + 2].op_str != hex(LINK_OBJECT_ANGLE_GET):
            value = 'other accessor ' + ins[i + 2].op_str
        elif tail == ['xorps xmm0, xmm0', 'movss dword ptr [eax], xmm0']:
            value = '0.0'
        elif tail == ['movss xmm0, dword ptr [0x6fce370]', 'movss dword ptr [eax], xmm0']:
            value = 'WorldTime'
        else:
            value = 'other: ' + '; '.join(tail)
        count += 1
        stores.append((ins[i].address, element, value))
    for address, element, value in stores:
        if value == 'read':
            report.add('link_angle', True, {'site': hex(address), 'value': value})
            report.cover('link_angle', 'read')
            continue
        ok = value == '0.0' or (value == 'WorldTime' and element == '2' and 0x012c5d35 < address < 0x012c5e76)
        report.add('link_angle', ok, {'site': hex(address), 'element': element, 'value': value})
        report.cover('link_angle', value)
    # the 0x44f gate in front of the WorldTime store, and the call that passes [ebp-0x120] as the OBJECT
    gate = [x for x in ins if x.address == 0x012c5d35]
    call = [x for x in ins if x.address in (LINK_CALL - 6, LINK_CALL)]
    ok = bool(gate) and gate[0].op_str == 'dword ptr [ebp + 0x1c], 0x44f' and len(call) == 2 and \
        call[0].op_str == 'dword ptr [ebp - 0x120]' and call[1].op_str == '0x176ce74'
    report.add('link_angle', ok, {'gate': gate[0].op_str if gate else None})
    report.cover('link_angle', 'the 0x44f gate and the OBJECT argument')
    zero = sum(1 for s in stores if s[2] == '0.0')
    report.add('link_angle', zero == 11, {'zero stores': zero})
    report.cover('link_angle', 'eleven zero stores')
    # no other access form: no memory operand at a register + 0x164, and +0x164 is added only to [ebp-0x120]
    direct = [hex(x.address) for x in ins if '+ 0x164]' in x.op_str and 'ebp' not in x.op_str]
    added = [x for k, x in enumerate(ins) if x.op_str == 'ecx, 0x164' and x.mnemonic == 'add']
    ok = not direct and len(added) == count and all(
        ins[k - 1].op_str == 'ecx, dword ptr [ebp - 0x120]' for k, x in enumerate(ins) if x in added)
    report.add('link_angle', ok, {'direct': direct, 'adds': len(added), 'accessor sites': count})
    report.cover('link_angle', 'only the accessor form')


# ---------------------------------------------------------------- bitmap

def family_bitmap(text, data, report):
    start, site, bitmap, path = REGISTRATION
    m = re11.fx.FxMachine(text, data)
    calls = []

    def load(mm):
        args = [mm.argument(i) for i in range(6)]
        at = args[0] - am.DATA_BASE
        calls.append([data[at:at + 256].split(b'\0')[0].decode('ascii'), *args[1:]])
        return 1

    def done(mm):
        return 0
    r = m.execute(start, [], [], {0x0185baac: load, site + 8: done})
    ok = re11.fx.vc.ok(r) and calls == [[path, bitmap, 0x2601, 0x2900, 1, 0]]
    report.add('bitmap', ok, {'call': hex(site), 'calls': calls})
    report.cover('bitmap', hex(bitmap))


# ---------------------------------------------------------------- main

def run_families(text, data, plib, cases, report):
    for name in ('create', 'move', 'render'):
        pt_family(text, data, plib, name, ITEM_KINDS, cases, report)
    family_owner_reads(text, data, plib, max(4, cases // 5), report)
    family_link_angle(text, report)
    family_bitmap(text, data, report)


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
        with tempfile.TemporaryDirectory(prefix='effects20-') as tmp:
            for name, old, new, family, kind in MUTANTS:
                ml = re11.compile_pt_mutant(tmp, name, 'item_owned_kinds.inc', old, new)
                rr = pt.Report()
                pt_family(text, data, ml, family, [kind], max(120, a.cases), rr, 'render-effects-020-mutant-')
                f = rr.families['item_' + family]
                mutants.append(dict(name=name, family='item_' + family, cases=f['cases'],
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
