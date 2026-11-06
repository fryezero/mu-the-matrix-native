#!/usr/bin/env python3
"""RENDER-EFFECTS-016 original-instruction families and compiled production mutants.

* fire06_create / fire06_move / fire06_render: Fire06 0x7f40 subtypes 1..3 (0x70c's stones, one in ten) through
  validate_particles' create (CreateParticle 0x015ae7b0), move (MoveParticles 0x01616c80) and render
  (RenderParticles 0x0159123f) families against reconstructed/particles. The three dispatches send 0x7f40 to
  Fire01's case (jump tables 0x01615f68/0x01615f3c, 0x0168eee0/0x0168eeb4, 0x015ae397/0x015ae373).
* render_state: EnableAlphaBlend 0x0184aa2b, EnableAlphaTest 0x0184a990(argument) and DisableAlphaBlend 0x0184a7f3,
  random sequences from random cache bytes and GL state, executed with the GL imports recorded; the caches and the
  GL state they leave against mu_sfx_render_state (reconstructed/combat/bow_fx.inc).
* decal_states: the native decal quads of 0x70a, 0x70c and 0x45e/3, 7 (native/tests/effects16_host.c, built
  against the native libraries) against the GL state the client's wrappers leave for the same op sequence: blend
  factors, alpha test and depth writes per RenderTerrainAlphaBitmap call (0x70c's crater: EnableAlphaTest(1)).
* bitmap_sites: every native combat bitmap row (mu_combat.c) and the world particle table's Fire06 slot against the
  arguments its LoadBitmap 0x0185baac call site pushes (index, filter, wrap, path), decoded from the instructions.

No client bytes or decoded data are written by this tool.
"""
import argparse
from collections import defaultdict
import ctypes as C
import json
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import time

import actor_machine as am
import client_ui_machine as cm
import pins
import validate_gfx3 as gfx
import validate_particles as pt
import validate_render_effects11 as re11
import validate_skill_fx as fx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'native'/'tests'))
FIRE06_KINDS = [(0x7f40, 1), (0x7f40, 2), (0x7f40, 3)]

ADD, ALPHA, OFF, DECAL = 0x0184aa2b, 0x0184a990, 0x0184a7f3, 0x016cdd5f
HELPERS = (0x0184a6fd, 0x0184a720, 0x0184a743, 0x0184a763)   # cull on/off, depth mask on/off
CACHE = {'blend': 0x0bdc58c4, 'cull': 0x0bdc597f, 'depth_mask': 0x0bdc5980, 'alpha_test': 0x0bdc58b5,
         'texture': 0x0bdc597d, 'fog_flag': 0x0bdc597c}
CAPS = {0x0be2: 'gl_blend', 0x0b44: 'gl_cull', 0x0bc0: 'gl_alpha_test', 0x0de1: 'gl_texture', 0x0b60: 'gl_fog'}
LOAD_BITMAP = 0x0185baac

# LoadBitmap call site of each native combat bitmap (mu_item_bitmaps.inc, the startup table) and Fire06's
SITES = {0x7534: 0x01820a39, 0x7dfe: 0x01820bb9, 0x7df3: 0x01820a79, 0x7df4: 0x01820a59, 0x7df5: 0x01820a99,
         0x7df6: 0x01820ab9, 0x7df7: 0x01820ad9, 0x7df8: 0x01820af9, 0x7f2b: 0x01822365, 0x7f84: 0x01821599,
         0x7f3c: 0x01820f19, 0x7f26: 0x01821639, 0x7fd8: 0x01822425, 0x7fd3: 0x018223c5, 0x7fd5: 0x01822385,
         0x7fd6: 0x018223e5, 0x7f79: 0x018228e5, 0x7f78: 0x01822545, 0x80e3: 0x01835b52, 0x80e4: 0x01835b72,
         0x814c: 0x01821dd9, 0x8182: 0x01833b47, 0x8185: 0x01833ba0, 0x828c: 0x01837b6c, 0x85cc: 0x0182f066,
         0x8070: 0x018218d9, 0x7f87: 0x018215f9, 0x8147: 0x0183611a, 0x824c: 0x01837137, 0x8078: 0x01821a19,
         0x7fe9: 0x01822c65, 0x810a: 0x0182d4bf, 0x8155: 0x01822625, 0x8179: 0x01822685, 0x8013: 0x01821819,
         0x8002: 0x01820f79}
FIRE06_SITE, FIRE06_PATH = 0x018229e5, 'Effect\\Fire06.jpg'

PT_MUTANTS = [
    # (name, file, old, new, family, kind) on reconstructed/particles
    ('fire06_admit', 'particles.c', 'return subtype >= 1 && subtype <= 3;', 'return subtype >= 1 && subtype <= 2;',
     'create', (0x7f40, 3)),
    ('fire06_create_case', 'particles.c', '    case MU_PT_BITMAP_FIRE06:\n        /* 0x015ba585',
     '        /* 0x015ba585', 'create', (0x7f40, 1)),
    ('fire06_move_case', 'particles.c', '        case MU_PT_BITMAP_FIRE06:\n            /* 0x016282c9',
     '            /* 0x016282c9', 'move', (0x7f40, 2)),
    ('fire06_render_case', 'particles.c', '    case MU_PT_BITMAP_FIRE06:\n        /* 0x015978bb',
     '        /* 0x015978bb', 'render', (0x7f40, 1)),
]
STATE_MUTANTS = [
    # (name, old, new) on reconstructed/combat/bow_fx.inc
    ('state_add_mask', 'gl_cap(&s->depth_mask, &s->gl_depth_mask, 0);       /* 0x0184a763 */',
     'gl_cap(&s->depth_mask, &s->gl_depth_mask, 1);       /* 0x0184a763 */'),
    ('state_alpha_arg', 'if ((uint8_t)argument)', 'if (argument)'),
    ('state_alpha_test', 'gl_cap(&s->alpha_test, &s->gl_alpha_test, 1);', 'gl_cap(&s->alpha_test, &s->gl_alpha_test, 0);'),
    ('state_add_fog', 's->gl_fog = 0;', 's->gl_fog = 1;'),
    ('state_blend_cache', 'if (s->blend != id) {', 'if (1) {'),
    ('state_off_blend', 'if (s->blend != 0) {', 'if (s->blend == 2) {'),
    ('state_cap_test', 'if (on ? *cache == 0 : *cache != 0) {', 'if (*cache != on) {'),
    ('state_off_cull', 'gl_cap(&s->cull, &s->gl_cull, 1);                   /* 0x0184a6fd */',
     'gl_cap(&s->cull, &s->gl_cull, 0);                   /* 0x0184a6fd */'),
    ('state_alpha_func', 'gl_blend_func(s, 2, 0x0302u, 0x0303u);', 'gl_blend_func(s, 2, 0x0302u, 0x0301u);'),
]
NATIVE_MUTANTS = [
    # (name, file, old, new, family) on native/core
    ('thunder_wrap', 'mu_combat.c', '"Thunder01.jpg", \'j\', 0x2601, 0x2901, 0}', '"Thunder01.jpg", \'j\', 0x2601, 0x2900, 0}',
     'bitmap_sites'),
    ('fire01_wrap', 'mu_combat.c', '"Fire01.jpg", \'j\', 0x2601, 0x2900, 0}', '"Fire01.jpg", \'j\', 0x2601, 0x2901, 0}',
     'bitmap_sites'),
    ('font_wrap', 'mu_combat.c', '"Font_Damage.tga", \'t\', 0x2601, 0x2900, 0}', '"Font_Damage.tga", \'t\', 0x2601, 0x2901, 0}',
     'bitmap_sites'),
    ('crater_filter', 'mu_combat.c', '"Cratered.tga", \'t\', 0x2600, 0x2900, 1}', '"Cratered.tga", \'t\', 0x2601, 0x2900, 1}',
     'bitmap_sites'),
    ('mono3_wrap', 'mu_combat.c', '"Swordeff_mono3.jpg", \'j\', 0x2601, 0x2901, 0}', '"Swordeff_mono3.jpg", \'j\', 0x2601, 0x2900, 0}',
     'bitmap_sites'),
    ('fire06_slot', 'mu_particles.c', '    MU_PT_BITMAP_FIRE06,\n    MU_PT_BITMAP_RAIN_SPLASH,', '    MU_PT_BITMAP_RAIN_SPLASH,',
     'bitmap_sites'),
    ('fire06_wrap', 'mu_particles.c', '|| bitmap_ids[i] == 0x83b8 ? 0x2901 : 0x2900;',
     '|| bitmap_ids[i] == 0x83b8 || bitmap_ids[i] == 0x7f40 ? 0x2901 : 0x2900;', 'bitmap_sites'),
    ('decal_alpha_test', 'mu_combat.c', 'q->alpha_test = d->gl.gl_alpha_test;', 'q->alpha_test = 0;', 'decal_states'),
    ('decal_depth_mask', 'mu_combat.c', 'q->depth_mask = d->gl.gl_depth_mask;', 'q->depth_mask = 0;', 'decal_states'),
    ('decal_state_op', 'mu_combat.c', 'mu_sfx_render_state(&d.gl, op->routine, op->argument);',
     'mu_sfx_render_state(&d.gl, op->routine == MU_SFX_RENDER_BLEND_ALPHA ? MU_SFX_RENDER_BLEND_ADD : op->routine, '
     'op->argument);', 'decal_states'),
]


def check_anchors():
    """Every mutant anchor must occur exactly once in its file."""
    bad = []
    for name, file, old, *_ in PT_MUTANTS:
        if (ROOT/'reconstructed/particles'/file).read_text().count(old) != 1:
            bad.append(name)
    for name, old, new in STATE_MUTANTS:
        if (ROOT/'reconstructed/combat/bow_fx.inc').read_text().count(old) != 1:
            bad.append(name)
    for name, file, old, *_ in NATIVE_MUTANTS:
        if (ROOT/'native/core'/file).read_text().count(old) != 1:
            bad.append(name)
    return bad


# ---------------------------------------------------------------- Fire06 particle families

def pt_family(text, data, lib, name, kinds, cases, report, seed='render-effects-016-'):
    saved = pt.KINDS, pt.OWNED_KINDS
    pt.KINDS, pt.OWNED_KINDS = kinds, set()
    try:
        r = pt.Report()
        dict(pt.FAMILIES)[name](pt.PtMachine(text, data), lib, random.Random(seed + name), cases * len(kinds), r,
                                defaultdict(int))
    finally:
        pt.KINDS, pt.OWNED_KINDS = saved
    report.families['fire06_' + name] = r.families[name]
    report.coverage['fire06_' + name] = r.coverage.get(name, {})


# ---------------------------------------------------------------- the wrappers' GL state

class GLState(C.Structure):
    _fields_ = [('blend', C.c_int32), ('cull', C.c_uint8), ('depth_mask', C.c_uint8), ('alpha_test', C.c_uint8),
                ('texture', C.c_uint8), ('fog_flag', C.c_uint8), ('gl_blend', C.c_uint8), ('gl_cull', C.c_uint8),
                ('gl_depth_mask', C.c_uint8), ('gl_alpha_test', C.c_uint8), ('gl_texture', C.c_uint8),
                ('gl_fog', C.c_uint8), ('gl_src', C.c_uint32), ('gl_dst', C.c_uint32)]


FIELDS = [f for f, _ in GLState._fields_]


def bind_state(lib):
    lib.mu_sfx_render_state.argtypes = [C.POINTER(GLState), C.c_int32, C.c_int32]
    lib.mu_sfx_render_state.restype = C.c_int
    return lib


def wrapper_machine(text, data):
    m = cm.Machine(text, data)
    gfx.allow_functions(m, text, ADD, ALPHA, OFF, *HELPERS)
    return m


def client_state(m, state, ops):
    """The caches and GL state the client's wrappers leave, from state (a dict of GLState's fields)."""
    m.reset()
    m.put32(CACHE['blend'], state['blend'])
    for key in ('cull', 'depth_mask', 'alpha_test', 'texture', 'fog_flag'):
        m.write(CACHE[key], bytes([state[key]]))
    for routine, argument in ops:
        m.call(routine, args=(argument,) if routine == ALPHA else ())
    out = dict(state)
    for name, args in m.calls:
        if name in ('glEnable', 'glDisable') and args[0] in CAPS:
            out[CAPS[args[0]]] = int(name == 'glEnable')
        elif name == 'glBlendFunc':
            out['gl_src'], out['gl_dst'] = args
        elif name == 'glDepthMask':
            out['gl_depth_mask'] = int(args[0] != 0)
        else:
            raise cm.CaseError(f'unexpected call {name} {args}')
    out['blend'] = struct.unpack('<i', struct.pack('<I', m.u32(CACHE['blend'])))[0]
    for key in ('cull', 'depth_mask', 'alpha_test', 'texture', 'fog_flag'):
        out[key] = m.read(CACHE[key], 1)[0]
    return out


def native_state(lib, state, ops):
    s = GLState(**state)
    for routine, argument in ops:
        if not lib.mu_sfx_render_state(C.byref(s), routine, argument):
            return None
    return {f: getattr(s, f) for f in FIELDS}


def random_state(rng, consistent=False):
    blend = rng.choice([0, 2, 3, 1, 8, 5])
    cache = {k: rng.choice([0, 1, 1, 2, 0xff]) for k in ('cull', 'depth_mask', 'alpha_test', 'texture')}
    state = dict(blend=blend, fog_flag=rng.choice([0, 1, 1, 2]), **cache)
    if consistent:   # the client's invariant: the GL state is what the caches say
        for k in ('cull', 'depth_mask', 'alpha_test', 'texture'):
            state[k] = int(state[k] != 0)
            state['gl_' + k] = state[k]
        state.update(gl_blend=int(blend != 0), gl_fog=int(bool(state['fog_flag']) and rng.random() < 0.5))
        state['gl_src'], state['gl_dst'] = {2: (0x302, 0x303), 3: (1, 1)}.get(blend, (0x306, 0))
    else:
        state.update({k: rng.choice([0, 1]) for k in ('gl_blend', 'gl_cull', 'gl_depth_mask', 'gl_alpha_test',
                                                       'gl_texture', 'gl_fog')})
        state['gl_src'], state['gl_dst'] = rng.choice([(1, 1), (0x302, 0x303), (0, 0x300), (0x306, 0)])
    return state


def random_ops(rng):
    ops = []
    for _ in range(rng.randrange(1, 5)):
        routine = rng.choice([ADD, ALPHA, ALPHA, OFF])
        ops.append((routine, rng.choice([1, 1, 0, 2, 0x100, 0x101]) if routine == ALPHA else 0))
    return ops


def family_render_state(m, lib, rng, cases, report):
    for n in range(cases):
        state, ops = random_state(rng), random_ops(rng)
        error = None
        try:
            client = client_state(m, state, ops)
        except cm.CaseError as e:
            client, error = None, str(e)
        mine = native_state(lib, state, ops)
        equal = error is None and mine == client
        report.add('render_state', equal, {'case': n, 'state': state, 'ops': [[hex(a), b] for a, b in ops],
                                           'client': client, 'mine': mine, 'error': error})
        report.cover('render_state', '/'.join({ADD: 'add', ALPHA: 'alpha%d' % (b & 0xff != 0), OFF: 'off'}[a]
                                              for a, b in ops[-2:]) + (' fog' if state['fog_flag'] else ''))


# ---------------------------------------------------------------- the native decal quads

def build_host(directory, combat=None, particles=None):
    """effects16_host.c against the native libraries; combat / particles: mutated copies of mu_combat.c /
    mu_particles.c (compiled in place of the library's)."""
    import test_render_effects16 as t
    native = ROOT/'native'
    if combat is None and particles is None:
        return t.build_host(directory)
    subprocess.run(['make', '-s', '-C', str(native), 'build/libmunative.a', 'build/libmusession_world.a'],
                   check=True, capture_output=True)
    directory = Path(directory)
    flags = ['clang', '-std=c11', '-O1', '-ffp-contract=off', '-I', str(native/'build/gen'), '-I',
             str(native/'session'), '-iquote', str(native/'core')]
    source = (native/'tests/effects16_host.c').read_text()
    if combat is not None:
        source = source.replace('#include "../core/mu_combat.c"', f'#include "{combat}"')
    else:
        source = source.replace('#include "../core/mu_combat.c"', f'#include "{native/"core/mu_combat.c"}"')
    (directory/'host.c').write_text(source)
    objects = [directory/'host.o']
    subprocess.run(flags + ['-c', str(directory/'host.c'), '-o', str(objects[0])], check=True, capture_output=True)
    if particles is not None:
        objects.append(directory/'particles.o')
        subprocess.run(flags + ['-c', str(particles), '-o', str(objects[1])], check=True, capture_output=True)
    command = ['clang++', *map(str, objects), str(native/'build/libmunative.a'), str(native/'build/libmusession_world.a'),
               '-lm', '-o', str(directory/'host')]
    if sys.platform == 'darwin':
        command += ['-L/opt/homebrew/opt/cryptopp/lib', '-lcryptopp', '-L/opt/homebrew/opt/jpeg-turbo/lib', '-ljpeg',
                    '-framework', 'CoreText', '-framework', 'CoreGraphics', '-framework', 'CoreFoundation']
    else:
        command += ['-lcryptopp', '-ljpeg']
    subprocess.run(command, check=True, capture_output=True)
    return directory/'host'


def quad_tuple(texture, gl):
    if not gl['gl_blend']:
        blend = (0, 1, 0)
    elif (gl['gl_src'], gl['gl_dst']) == (1, 1):
        blend = (1, 0, 0)
    else:
        blend = (0, gl['gl_src'], gl['gl_dst'])
    return [texture, *blend, gl['gl_alpha_test'], gl['gl_depth_mask']]


def family_decal_states(m, host, rng, report):
    effects = json.loads(subprocess.run([str(host), 'decals'], capture_output=True, text=True, check=True).stdout)
    for e in effects['effects']:
        state = random_state(rng, consistent=True)
        expected, done = [], []
        for routine, argument, texture in e['ops']:
            if routine == DECAL:
                gl = client_state(m, state, done) if done else state
                q = quad_tuple(texture, gl)
                if not expected or expected[-1] != q:
                    expected.append(q)
            else:
                done.append((routine, argument))
        # one case per effect: the state of each call's quads (consecutive equal states merged, as the host)
        report.add('decal_states', e['quads'] == expected, {'effect': [hex(e['type']), e['subtype'], e['lifetime']],
                                                            'expected': expected, 'mine': e['quads']})
        report.cover('decal_states', f"{e['type']:#x}/{e['subtype']} life {e['lifetime']}")


# ---------------------------------------------------------------- LoadBitmap call sites

def decode_site(text, data, site):
    """(index, filter, wrap, path) pushed for the LoadBitmap call at site: push wrap; push filter; push index;
    push path; call 0x0185baac (each push imm32)."""
    def at(a):
        return text[a - am.TEXT_BASE]
    if at(site) != 0xe8 or site + 5 + struct.unpack_from('<i', text, site + 1 - am.TEXT_BASE)[0] != LOAD_BITMAP:
        return None
    words = []
    for k in range(4):
        a = site - 5 * (k + 1)
        if at(a) != 0x68:
            return None
        words.append(struct.unpack_from('<I', text, a + 1 - am.TEXT_BASE)[0])
    path, index, filt, wrap = words
    raw = data[path - am.DATA_BASE:path - am.DATA_BASE + 128]
    return index, filt, wrap, raw.split(b'\0')[0].decode('latin1')


def family_bitmap_sites(text, data, host, report):
    table = json.loads(subprocess.run([str(host), 'table'], capture_output=True, text=True, check=True).stdout)
    rows = {row[0]: row for row in table['bitmaps']}
    for index, site in SITES.items():
        row, client = rows.get(index), decode_site(text, data, site)
        mine = None if row is None else (row[0], row[3], row[4], f'{row[1]}\\{row[2]}'.lower())
        equal = client is not None and mine is not None and mine == (*client[:3], client[3].lower())
        report.add('bitmap_sites', equal, {'index': hex(index), 'site': hex(site), 'client': client, 'mine': mine})
        report.cover('bitmap_sites', f'filter {client[1]:#x} wrap {client[2]:#x}' if client else 'undecoded')
    client = decode_site(text, data, FIRE06_SITE)
    slot, filt, wrap = table['fire06']
    equal = client == (0x7f40, filt, wrap, FIRE06_PATH) and slot >= 0 and table['fire06_kinds'] == [0, 1, 1, 1, 0]
    report.add('bitmap_sites', equal, {'index': '0x7f40', 'site': hex(FIRE06_SITE), 'client': client,
                                       'mine': table['fire06'], 'kinds': table['fire06_kinds']})
    report.cover('bitmap_sites', 'Fire06 world particle slot')
    extra = sorted(set(rows) - set(SITES))
    report.add('bitmap_sites', not extra, {'rows without a site': [hex(x) for x in extra]})


# ---------------------------------------------------------------- mutants

def compile_state_mutant(directory, name, old, new):
    base = ROOT/'reconstructed'/'combat'
    work = Path(directory)/name
    work.mkdir()
    for f in ('skill_fx.c', 'skill_fx.h', 'pet_fx.inc', 'arrow_fx.inc'):
        shutil.copy(base/f, work/f)
    source = (base/'bow_fx.inc').read_text()
    if source.count(old) != 1:
        raise ValueError(f'{name}: expected exactly one mutation site')
    (work/'bow_fx.inc').write_text(source.replace(old, new))
    others = ['combat.c', '../objects/world_warp.c', '../joints/joints.c', '../record-math/record_math.c',
              '../movement/client_movement.c']
    out = Path(directory)/(name + '.' + fx.SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-fno-fast-math', '-shared', '-I',
                    str(base), str(work/'skill_fx.c'), *[str(base/p) for p in others], '-lm', '-o', str(out)],
                   check=True, capture_output=True)
    return bind_state(C.CDLL(str(out)))


def native_mutant_host(directory, name, file, old, new):
    work = Path(directory)/name
    work.mkdir()
    source = (ROOT/'native/core'/file).read_text()
    if source.count(old) != 1:
        raise ValueError(f'{name}: expected exactly one mutation site')
    mutated = work/file
    mutated.write_text(source.replace(old, new))
    return build_host(work, combat=mutated if file == 'mu_combat.c' else None,
                      particles=mutated if file == 'mu_particles.c' else None)


# ---------------------------------------------------------------- main

def run_families(text, data, plib, slib, wm, host, cases, report, seed='render-effects-016-', only=None):
    for name in ('create', 'move', 'render'):
        if not only or only == 'fire06_' + name:
            pt_family(text, data, plib, name, FIRE06_KINDS, cases, report, seed)
    if not only or only == 'render_state':
        family_render_state(wm, slib, random.Random(seed + 'state'), cases * 10, report)
    if not only or only == 'decal_states':
        family_decal_states(wm, host, random.Random(seed + 'decals'), report)
    if not only or only == 'bitmap_sites':
        family_bitmap_sites(text, data, host, report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=20, help='cases per Fire06 kind and family (x10 wrapper sequences)')
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
    plib = pt.load_library(ROOT/f'reconstructed/particles/libclient_particles.{fx.SUFFIX}')
    slib = bind_state(C.CDLL(str(ROOT/f'reconstructed/combat/libcombat.{fx.SUFFIX}')))
    wm = wrapper_machine(text, data)
    report = pt.Report()
    mutants = []
    with tempfile.TemporaryDirectory(prefix='effects16-') as tmp:
        host = build_host(tmp)
        run_families(text, data, plib, slib, wm, host, a.cases, report)
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
                pt_family(text, data, ml, family, [kind], max(40, a.cases), rr, 'render-effects-016-mutant-')
                record(name, 'fire06_' + family, rr)
            for name, old, new in STATE_MUTANTS:
                ml = compile_state_mutant(tmp, name, old, new)
                rr = pt.Report()
                family_render_state(wm, ml, random.Random('render-effects-016-mutant-state'), max(200, a.cases * 10),
                                    rr)
                record(name, 'render_state', rr)
            for name, file, old, new, family in NATIVE_MUTANTS:
                mh = native_mutant_host(tmp, name, file, old, new)
                rr = pt.Report()
                if family == 'decal_states':
                    family_decal_states(wm, mh, random.Random('render-effects-016-mutant-decals'), rr)
                else:
                    family_bitmap_sites(text, data, mh, rr)
                record(name, family, rr)
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
