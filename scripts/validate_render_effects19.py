#!/usr/bin/env python3
"""RENDER-EFFECTS-019 original-instruction families and compiled production mutants
(docs/research/client-render-effects-019.md).

Map-object records (reconstructed/objects/map_effects.c, which the native map-object update uses):

* map_update: 0x0129f671(dt) on a map OBJECT (+0x318 = 0, so every bone comes from the shared pose buffer
  0x06fce398) whose +0x3d0 std::list holds records as the table attaches them (timed 0), run in Unicorn through
  validate_render_effects18's machine (the list helpers, the bone matrix 0x0129fd4f, the bone position 0x012a0030,
  the world matrix 0x0129faee, the matrix helpers and the sector predicate 0x012a0d29 as client code). The OBJECT
  sits in a synthetic sector list of one to five objects (its +0x350/+0x354 links as CreateObject leaves them); the
  native side derives the predicate from the same list (mu_map_effects_in_sector over a mu_obj_world) and builds
  each external matrix from the OBJECT image (mu_map_effect_matrix). Compared: every scale and node update (dt, the
  16 matrix words, the OBJECT) in order. Each case also checks the native refusals: a bone >= 0 with no pose or
  beyond the pose answers MU_MAP_EFFECT_UNPOSED, following a bone below -1 MU_MAP_EFFECT_UNDEFINED.
* map_records (private, opt-in: --lang-dir naming a directory with mapeffects.tsv): every decoded table entry's
  bone and follow byte (758 entries, the 19 unfollowed among them), alone in its sector and in a list.

Test Area 121's particle kinds (reconstructed/particles/test_area_kinds.inc):

* ta_pt_create / ta_pt_move / ta_pt_render: 0x801e/7, 0x801c/9 and 0x801b/5 through validate_particles' families
  (CreateParticle 0x015ae7b0, MoveParticles' record body, RenderParticles' record body), records drawn with
  WATERFALL4 0x801d or WATERFALL5 0x801e, lifetimes around 0x801e's light gates (8, 20).

No client bytes or decoded data are written by this tool.
"""
import argparse
from collections import defaultdict
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actor_machine as am  # noqa: E402
import pins  # noqa: E402
import validate_particles as pt  # noqa: E402
import validate_render_effects11 as r11  # noqa: E402
import validate_render_effects18 as r18  # noqa: E402
import validate_skill_fx as fx  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
f32 = fx.f32
bits = r18.bits
SECTORS, OBJ_SIZE = 256, 0x3d8
OK, UNPOSED, UNDEFINED = 1, 0, -1
TA_PT = [(0x801e, 7), (0x801c, 9), (0x801b, 5)]

BODIES = {'update': (0x0129f671, 0x0129f9c6), 'bone_source': (0x0129f12c, 0x0129f18a),
          'bone_matrix': (0x0129fd4f, 0x012a0030), 'bone_position': (0x012a0030, 0x012a011e),
          'in_sector': (0x012a0d29, 0x012a0d5c),
          'create_801e_7': (0x015f236c, 0x015f24fe), 'create_801c_prefix': (0x015f4466, 0x015f44dc),
          'create_801c_9': (0x015f496e, 0x015f4a0a), 'create_801c_jitter': (0x015f5079, 0x015f5156),
          'create_801b_prefix': (0x015f27cb, 0x015f2e74), 'create_801b_5': (0x015f30e0, 0x015f3341),
          'move_801e_7': (0x016684c6, 0x016686c4), 'move_801e_gates': (0x0166886e, 0x016689f8),
          'move_801c_9': (0x0166b810, 0x0166b929), 'move_801b_5': (0x01668bc8, 0x01668de1)}


# ---------------------------------------------------------------- the C side (map_effects.c + muun_effects.c)
class ObjWorld(C.Structure):
    _fields_ = [('objects', C.c_void_p), ('count', C.c_int32), ('head', C.c_int32 * SECTORS),
                ('next', C.POINTER(C.c_int32)), ('block_visible', C.c_uint8 * SECTORS)]


def build_map(folder, source_text=None):
    """map_effects.c (or a mutated copy in folder) with muun_effects.c, headers from reconstructed/objects."""
    folder = Path(folder)
    source = ROOT/'reconstructed/objects'
    unit = source/'map_effects.c'
    if source_text is not None:
        unit = folder/'map_effects.c'
        unit.write_text(source_text)
    out = folder/('libmapeffects19.' + SUFFIX)
    subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-shared', '-Wall', '-Wextra', '-Werror', '-Wconversion',
                    '-ffp-contract=off', '-fno-fast-math', '-I', str(source), str(unit), str(source/'muun_effects.c'),
                    '-lm', '-o', str(out)], check=True, capture_output=True)
    lib = C.CDLL(str(out))
    lib.mu_map_effects_in_sector.argtypes = [C.POINTER(ObjWorld), C.c_int32]
    lib.mu_map_effects_in_sector.restype = C.c_int
    lib.mu_map_effect_matrix.argtypes = [C.POINTER(C.c_uint32), C.c_char_p, C.c_int, C.c_void_p, C.c_int32,
                                         C.c_int32, C.c_int]
    lib.mu_map_effect_matrix.restype = C.c_int
    return lib


# ---------------------------------------------------------------- map_update
def sector_list(rng):
    """One to five objects in one sector, the OBJECT at a random place; other sectors hold other objects, and the
    object indices are shuffled (so a next index can be 0)."""
    n = rng.choice([1, 1, 2, 3, 5])
    at = rng.randrange(n)
    others = rng.choice([0, 3, 7])
    indices = list(range(n + others))
    rng.shuffle(indices)
    members, rest = indices[:n], indices[n:]
    sector = rng.randrange(SECTORS)
    return {'n': n, 'at': at, 'members': members, 'rest': rest, 'sector': sector}


def links(lst):
    """+0x350 (previous) and +0x354 (next) as CreateObject leaves them: OBJECT pointers, 0 at the ends."""
    def address(k):
        return r18.OBJECTS + 0x400 * (1 + lst['members'][k])
    at, n = lst['at'], lst['n']
    return (address(at - 1) if at > 0 else 0, address(at + 1) if at < n - 1 else 0)


def c_world(lst):
    total = lst['n'] + len(lst['rest'])
    nxt = (C.c_int32 * total)(*([-1] * total))
    w = ObjWorld()
    for s in range(SECTORS):
        w.head[s] = -1
    w.count = total
    m = lst['members']
    w.head[lst['sector']] = m[0]
    for k in range(len(m) - 1):
        nxt[m[k]] = m[k + 1]
    rest = lst['rest']
    for k, index in enumerate(rest):   # the others: alone or in pairs in other sectors
        s = (lst['sector'] + 1 + k // 2) % SECTORS
        if w.head[s] < 0:
            w.head[s] = index
        else:
            nxt[w.head[s]] = index
    w.next = nxt
    return w, nxt


def random_map_case(rng, record=None, sector_state=None):
    pose_bones = rng.choice([30, 40, 52, r18.SHARED_BONES - 1, rng.randrange(1, r18.SHARED_BONES)])
    records = []
    for k in range(1 if record else rng.choice([1, 1, 2, 3, 5])):
        if record:
            bone, follow = record
            pose_bones = max(pose_bones, bone + 1)
        else:
            follow = rng.choice([0, 0, 1, 1, 2, 0xff])
            bone = rng.choice([0, 1, 29, 7, 20, -1, rng.randrange(0, pose_bones), pose_bones - 1])
            if not follow and rng.random() < 0.15:
                bone = rng.choice([-2, -7])   # not following, below -1: the scale alone
        records.append({'handle': k, 'bone': min(bone, pose_bones - 1), 'follow': follow, 'timed': 0,
                        'template': bits(f32(rng.choice([150.0, 40.0, 55.0, 70.0, rng.uniform(1.0, 600.0)]))),
                        'lifetime': 0})
    lst = sector_list(rng)
    if sector_state is not None:
        while (lst['n'] > 1) != sector_state:
            lst = sector_list(rng)
    return {'records': records, 'model_bones': rng.choice([-1, pose_bones, rng.randrange(0, 64)]), 'own': False,
            'sector': links(lst), 'list': lst, 'pose_bones': pose_bones,
            'bones': r18.random_bones(rng, 2), 'shared': r18.random_bones(rng, max(r18.SHARED_BONES, pose_bones + 1)),
            'position': [bits(f32(rng.uniform(0.0, 25600.0))) for _ in range(2)] + [bits(f32(rng.uniform(-50.0, 800.0)))],
            'angle': [bits(f32(rng.choice([0.0, 90.0, -45.0, rng.uniform(-720.0, 720.0)]))) for _ in range(3)],
            'scale': bits(f32(rng.choice([1.0, 1.14, 1.02, 0.5, rng.uniform(0.01, 4.0)]))),
            'dt': bits(f32(rng.choice([0.1, 0.1, 0.0, rng.uniform(0.0, 0.5)]))),
            'type': rng.randrange(0, 300)}


def image(case):
    img = bytearray(OBJ_SIZE)
    struct.pack_into('<i', img, 0x5c, case['type'])
    struct.pack_into('<I', img, 0xa0, case['scale'])
    struct.pack_into('<6I', img, 0x158, *case['position'], *case['angle'])
    struct.pack_into('<II', img, 0x350, *case['sector'])
    return bytes(img)


def run_c_map(lib, case):
    w, keep = c_world(case['list'])
    obj = case['list']['members'][case['list']['at']]
    in_sector = lib.mu_map_effects_in_sector(C.byref(w), obj)
    shared = (C.c_float * len(case['shared']))(*case['shared'])
    pose = C.cast(shared, C.c_void_p).value
    img = image(case)
    calls, refusals = [], []
    scale = am.from_bits(case['scale'])
    for rec in case['records']:
        calls.append(('scale', rec['handle'], bits(f32(am.from_bits(rec['template']) * scale))))
        out = (C.c_uint32 * 16)()
        status = lib.mu_map_effect_matrix(out, img, in_sector, pose, case['pose_bones'], rec['bone'], rec['follow'])
        if status == OK:
            calls.append(('update', rec['handle'], case['dt'], tuple(out), True))
        expect = UNDEFINED if rec['follow'] and rec['bone'] < -1 else OK
        if status != expect:
            refusals.append(('status', rec['bone'], rec['follow'], status))
        if rec['bone'] >= 0:   # without the pose, or beyond it: refused
            for p, n in ((None, case['pose_bones']), (pose, rec['bone'])):
                s = lib.mu_map_effect_matrix(out, img, in_sector, p, n, rec['bone'], rec['follow'])
                if s != UNPOSED:
                    refusals.append(('unposed', rec['bone'], n, s))
    return calls, refusals, in_sector


def compare_map(lib, machine, case, family, report, n):
    client, _, r = r18.run_client_update(machine, case)
    mine, refusals, in_sector = run_c_map(lib, case)
    ok = r['ok'] and len(client) == len(mine) and all(r18.same_call(a, b) for a, b in zip(client, mine)) \
        and not refusals and in_sector == int(any(case['sector']))
    detail = None
    if not ok:
        first = next((k for k, (a, b) in enumerate(zip(client, mine)) if not r18.same_call(a, b)),
                     min(len(client), len(mine)))
        detail = {'case': n, 'stopped': str(r.get('stopped')), 'error': str(r.get('error')), 'at': first,
                  'client': [repr(c) for c in client[first:first + 1]], 'native': [repr(c) for c in mine[first:first + 1]],
                  'refusals': refusals, 'in_sector': [in_sector, case['sector']]}
    report.add(family, ok, detail)
    for rec in case['records']:
        path = ('follow ' if rec['follow'] else 'place ') + (
            'world' if rec['bone'] == -1 else 'scale only' if rec['bone'] < -1 else 'shared bone')
        report.cover(family, path + (' sector' if any(case['sector']) else ' alone'))
    report.cover(family, f"list {case['list']['n']} at {min(case['list']['at'], 2)}")


def family_map(lib, machine, rng, cases, report):
    for n in range(cases):
        compare_map(lib, machine, random_map_case(rng), 'map_update', report, n)


def load_map_records(lang_dir):
    """mapeffects.tsv (RENDER-EFFECTS-008's export): world, type, index, path, x..rz, scale, bone, follow, ..."""
    rows = []
    for line in (Path(lang_dir)/'mapeffects.tsv').read_text(encoding='ascii').splitlines():
        if not line or line.startswith('#'):
            continue
        col = line.split('\t')
        rows.append((int(col[0]), int(col[1]), int(col[11]), int(col[12])))
    return rows


def family_map_records(lib, machine, rows, report):
    rng = random.Random('render-effects-019-records')
    for n, (_, _, bone, follow) in enumerate(rows):
        for alone in (True, False):
            compare_map(lib, machine, random_map_case(rng, (bone, follow), sector_state=not alone), 'map_records',
                        report, n)
    return {'entries': len(rows), 'unfollowed': sum(1 for r in rows if not r[3]),
            'unfollowed_bones': sorted({r[2] for r in rows if not r[3]}),
            'unfollowed_worlds': sorted({r[0] for r in rows if not r[3]})}


# ---------------------------------------------------------------- Test Area's particle kinds
def random_ta_particle(rng, kind):
    p = r11._random_particle(rng, kind)   # validate_particles' record
    if kind[0] == 0x801e:
        p.tex_type = rng.choice([0x801e, 0x801d])
    p.lifetime = rng.choice([30, 40, 22, 21, 20, 19, 9, 8, 7, 2, 1, 0, -1, rng.randrange(-3, 45)])
    p.gravity = f32(rng.choice([2.0, 3.0, 0.0, rf(rng)]))
    return p


def rf(rng):
    return f32(rng.uniform(-10.0, 10.0))


def pt_compare(text, data, lib, name, kinds, cases):
    pt.KINDS, pt.OWNED_KINDS, pt.random_particle, pt.Case = kinds, set(), random_ta_particle, r11.OwnerCase
    pt.globals_region = r11.globals_region
    m = pt.PtMachine(text, data)
    report = pt.Report()
    dict(pt.FAMILIES)[name](m, lib, random.Random('render-effects-019-pt-' + name), cases, report, defaultdict(int))
    return report.families[name], report.coverage.get(name, {})


# ---------------------------------------------------------------- mutants
MAP_MUTANTS = [
    ('in_sector_next', 'if (w->next[object] >= 0)', 'if (w->next[object] > 0)'),
    ('in_sector_alone', '        if (w->head[s] == object)\n            return 0;',
     '        if (w->head[s] == object)\n            return 1;'),
    ('unposed_bound', 'bone >= pose_bones', 'bone > pose_bones'),
    ('scale_field', 'o.scale = mu_obj_f32(object, MU_OBJF_SCALE);', 'o.scale = 1.0f;'),
    ('angle_order', 'MU_OBJF_ANGLE + 4u * (uint32_t)k', 'MU_OBJF_ANGLE + 4u * (uint32_t)(2 - k)'),
    ('position_order', 'MU_OBJF_POSITION + 4u * (uint32_t)k', 'MU_OBJF_POSITION + 4u * (uint32_t)(2 - k)'),
    ('follow_byte', '(uint8_t)(follow != 0)', '(uint8_t)(follow == 1)'),
    ('in_sector_forced', 'o.in_sector = in_sector;', 'o.in_sector = 1;'),
    ('undefined_status', '? MU_MAP_EFFECT_OK : MU_MAP_EFFECT_UNDEFINED', '? MU_MAP_EFFECT_OK : MU_MAP_EFFECT_UNPOSED'),
]
PT_MUTANTS = [
    # (name, old, new, family, kind)
    ('tex_pick', '% 2 == 0 ? 0x801d : 0x801e', '% 2 == 0 ? 0x801e : 0x801d', 'create', (0x801e, 7)),
    ('fall_size', '(float)(mu_pt_rand(h) % 50) * 0.05f', '(float)(mu_pt_rand(h) % 50) * 0.04f', 'create', (0x801e, 7)),
    ('fall_drift', '(float)-(mu_pt_rand(h) % 2 + 3)', '(float)-(mu_pt_rand(h) % 2 + 2)', 'create', (0x801e, 7)),
    ('mist_rise', '(float)(mu_pt_rand(h) % 5 + 2)', '(float)(mu_pt_rand(h) % 5 + 3)', 'create', (0x801c, 9)),
    ('mist_kind', '(type == 0x801c && subtype == 9)', '(type == 0x801c && subtype == 8)', 'create', (0x801c, 9)),
    ('spray_life', 'p->lifetime = 40;', 'p->lifetime = 41;', 'create', (0x801b, 5)),
    ('spray_gravity', 'p->gravity = (float)(mu_pt_rand(h) % 2 + 2);', 'p->gravity = (float)(mu_pt_rand(h) % 2 + 1);',
     'create', (0x801b, 5)),
    ('spray_scene', 'h->scene_state == 5 ?', 'h->scene_state == 6 ?', 'create', (0x801b, 5)),
    ('spray_z', '(float)(mu_pt_rand(h) % 40) - 20.0f) + p->position[2]',
     '(float)(mu_pt_rand(h) % 40) - 10.0f) + p->position[2]', 'create', (0x801b, 5)),
    ('fall_dim_gate', 'if (p->lifetime < 8) {', 'if (p->lifetime <= 8) {', 'move', (0x801e, 7)),
    ('fall_bright_gate', '} else if (p->lifetime > 20) {', '} else if (p->lifetime >= 20) {', 'move', (0x801e, 7)),
    ('fall_turn', 'p->rotation = p->rotation + 1.0f;', 'p->rotation = p->rotation + 1.1f;', 'move', (0x801e, 7)),
    ('fall_advance', 'p->position[k] = p->position[k] + p->velocity[k];',
     'p->position[k] = p->position[k] - p->velocity[k];', 'move', (0x801e, 7)),
    ('mist_fall', 'p->velocity[2] = p->velocity[2] - 2.5f;', 'p->velocity[2] = p->velocity[2] - 2.0f;', 'move',
     (0x801c, 9)),
    ('spray_grow', 'p->scale = p->scale + 0.03f;', 'p->scale = p->scale + 0.05f;', 'move', (0x801b, 5)),
    ('spray_lift', '(p->gravity + p->velocity[2]) + p->position[2]', 'p->velocity[2] + p->position[2]', 'move',
     (0x801b, 5)),
]


class Report(r18.Report):
    pass


def run(cases, mutations, lang_dir=None):
    text = am.load_pinned(pins.TEXT.default_str(), am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(pins.DATA.default_str(), am.DATA_BYTES, am.DATA_SHA256, 'data')
    result = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256, 'families': {}, 'coverage': {},
              'mutants': {}}
    machine = fx.FxMachine(text, data)
    report = Report()
    with tempfile.TemporaryDirectory(prefix='render-effects19-') as tmp:
        lib = build_map(tmp)
        family_map(lib, machine, random.Random('render-effects-019-map'), cases * 4, report)
        if lang_dir and (Path(lang_dir)/'mapeffects.tsv').is_file():
            result['records'] = family_map_records(lib, machine, load_map_records(lang_dir), report)
    result['families'].update(report.families)
    result['coverage'].update({k: dict(c) for k, c in report.coverage.items()})
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/particles')], check=True)
    plib = pt.load_library(ROOT/'reconstructed'/('particles/libclient_particles.' + SUFFIX))
    for name in ('create', 'move', 'render'):
        f, cov = pt_compare(text, data, plib, name, TA_PT, cases * len(TA_PT))
        result['families']['ta_pt_' + name], result['coverage']['ta_pt_' + name] = f, cov
    if mutations:
        machine = fx.FxMachine(text, data)
        source = (ROOT/'reconstructed/objects/map_effects.c').read_text()
        with tempfile.TemporaryDirectory(prefix='render-effects19-mut-') as tmp:
            for name, old, new in MAP_MUTANTS:
                if source.count(old) != 1:
                    raise ValueError(f'{name}: expected exactly one mutation site')
                folder = Path(tmp)/name
                folder.mkdir()
                mlib = build_map(folder, source.replace(old, new))
                rep = Report()
                family_map(mlib, machine, random.Random('render-effects-019-map'), max(40, cases * 4), rep)
                f = rep.families['map_update']
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
            for name, old, new, family, kind in PT_MUTANTS:
                mlib = r11.compile_pt_mutant(tmp, name, 'test_area_kinds.inc', old, new)
                f, _ = pt_compare(text, data, mlib, family, [kind], max(40, cases))
                result['mutants'][name] = {'cases': f['cases'], 'caught': f['cases'] - f['equal']}
    result['bodies'] = {name: {'start': hex(a), 'end': hex(b),
                               'sha256': hashlib.sha256(text[a - am.TEXT_BASE:b - am.TEXT_BASE]).hexdigest()}
                        for name, (a, b) in BODIES.items()}
    result['instruction_cases'] = sum(f['cases'] for f in result['families'].values())
    result['all_equal'] = all(f['cases'] == f['equal'] for f in result['families'].values())
    result['all_mutants_caught'] = all(m['caught'] > 0 for m in result['mutants'].values())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--cases', type=int, default=20, help='cases per family unit')
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--lang-dir', type=Path,
                        help='lang directory with mapeffects.tsv: adds the private family map_records')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.cases < 1:
        parser.error('--cases must be positive')
    result = run(args.cases, args.mutations, args.lang_dir)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2, default=str))
    summary = {name: (f['cases'], f['equal']) for name, f in result['families'].items()}
    print(json.dumps({'summary': summary, 'instruction_cases': result['instruction_cases'],
                      'records': result.get('records'), 'mutants': result['mutants'],
                      'all_equal': result['all_equal'], 'all_mutants_caught': result['all_mutants_caught']}, indent=1))
    if not result['all_equal']:
        for name, f in result['families'].items():
            for failure in f['first_failures'][:2]:
                print(name, str(failure)[:1500])
    raise SystemExit(not (result['all_equal'] and result['all_mutants_caught']))
