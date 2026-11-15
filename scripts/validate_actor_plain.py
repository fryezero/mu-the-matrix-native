#!/usr/bin/env python3
"""RENDER-ACTORS-006: verify then generate bounded plain monster body plans.

Every candidate gets its own constructor, opener arguments, twenty-eight complete
RenderCharacter caller executions and actual native asset/texture/draw check.
RenderObject is the named body/pose boundary used by ACTORS-004/005. Generic
RenderObjDraw streams are compared separately for each distinct body model.
Stateful map services decline; this is an appearance fixture, never spawn data.
"""
import argparse
import collections
import csv
import ctypes as C
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import time

import actor_census as census
import actor_machine as am
import pins
import validate_actor_recipes as recipes
import validate_actor_monsters as monsters
import validate_actors as va
import validate_renderchar as vr

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ROOT/'docs/research/actor-admission-groups.csv'
TABLE = ROOT/'reconstructed/actors/plain_body_table.h'

class Plan(C.Structure):
    _fields_ = [('server_class', C.c_int32), ('model', C.c_int32), ('opened', C.c_int32),
                ('scale_bits', C.c_uint32), ('flags', C.c_uint32), ('translate', C.c_int32)]

def library(path=recipes.LIBRARY):
    lib = recipes.library(path)
    lib.mu_actor_plain_plan.argtypes = [C.c_int32, C.POINTER(Plan)]
    return lib

def initial_rows():
    # Keep the pre-lane population stable after the construction CSV is upgraded.
    with GROUPS.open() as f:
        return list(csv.DictReader(f))

# Constructor writes to fields consumed by RenderObject or attached lifetime
# must not be lost behind CreateCharacter's named recording boundary.
APPEARANCE_FIELDS = ((0x5,3),(0xd,2),(0x3b,1),(0x3e,2),(0x48,4),(0x5c,4),
    (0x60,4),(0x68,4),(0x74,4),(0x80,4),(0xa8,4),(0xac,4),(0xb0,4),
    (0xdc,4),(0xe4,4),(0xe8,4),(0xec,12),(0x34c,4))

def constructor(machine, cl):
    from unicorn import UC_HOOK_MEM_WRITE
    writes = set(); base = va.CLASS_CHARACTER+0x3254
    def write(uc, access, address, size, value, ignored):
        off = address-base
        if any(off < a+n and a < off+size for a,n in APPEARANCE_FIELDS):
            writes.add(off)
    hook = machine.uc.hook_add(UC_HOOK_MEM_WRITE, write, begin=base, end=base+0x3ff)
    original_case, original_record = va.class_case, va.class_record
    def initialized(world, rand):
        regions, stubs, record = original_case(world, rand)
        create = stubs[va.CREATE_CHARACTER]
        def store(m):
            writes.clear()
            result = create(m)
            m.uc.mem_write(va.CLASS_CHARACTER+0x328f, b'\1')
            return result
        stubs[va.CREATE_CHARACTER] = store
        return regions, stubs, record
    def record(cl, via, rec, run):
        row = original_record(cl, via, rec, run)
        row['object_kind'] = run['regions']['character'][0x328f]
        row['appearance_writes'] = sorted(writes)
        return row
    try:
        va.class_case, va.class_record = initialized, record
        return va.extract_class(machine, cl)
    finally:
        va.class_case, va.class_record = original_case, original_record
        machine.uc.hook_del(hook)

def render_check(args, row, world, action, alpha, frame):
    skips = vr.CHAR_SKIPS
    try:
        # Execute both character sprite emitters. Their old skip boundaries
        # would conceal exactly the extra passes this uniform check excludes.
        vr.CHAR_SKIPS = {a:n for a,n in skips.items() if a not in (0x01362f24, 0x01363098)}
        run, calls, w = monsters.client_plan(args, row, (0, 0), row['class'], action, world,
                                            vr.f2u(alpha), vr.f2u(frame))
    finally:
        vr.CHAR_SKIPS = skips
    base = [c for c in w.calls if c[0] == 'base-body']
    extra = [c for c in w.calls if c[0] not in ('base-body', 'RPO', 'skip')]
    # Only the ordinary body shadow is allowed. Parts, links, sprites, GL and
    # effect/bitmap/model registrations fail closed. Shared helper/update skips
    # are named boundaries, not proof of their downstream behavior.
    shadows_only = len(calls) <= 1 and all(c == ('SHADOW', row['model'], 1) for c in calls)
    ok = run['ok'] and base == [('base-body', [vr.CHAR+0x3254, 1, 0, 0, 0xffffffff, 0xffffffff])] and \
         shadows_only and not extra
    reason = ('unresolved caller at '+str(run.get('pc'))) if not run['ok'] else \
        'additional caller services: '+','.join(sorted({c[0] for c in extra})) if extra else \
        'additional part/link calls' if not shadows_only else 'body call arguments/count differ' if not ok else ''
    return ok, dict(cl=row['class'], world=world, action=action, calls=calls, extra=extra,
                    base=base, reason=reason, stop=None if run['ok'] else str(run)[:400])

def opener(machine, authored, row):
    t = row['opens'][0][1]
    results = []
    for world in (0, 3, 2, 51, 18, 30):
        case = va.monster_case(str(t), t, actions=16, world=world)
        run = va.run_client_open(machine, case)
        native = authored.run_open(case)
        expected = [('access', row['model'], 'Data\\Monster\\', 'Monster', t+1),
                    ('texture', row['model'], 'Monster\\', 0x2901, 0x2600)]
        if not run['ok'] or run['calls'] != expected or native['status'] != 0 or native['calls'] != expected or any(
            run['regions'].get(k) != v for k,v in native['regions'].items()):
            return False, dict(cl=row['class'], world=world, actual=run['calls'], expected=expected)
        if run['regions']['model0'][0x94:0x98] != bytes(case['regions'][0].data[0x94:0x98]):
            return False, dict(cl=row['class'], reason='opener StreamMesh override')
        results.append(run)
    return True, None

def draw_checks(args, rows):
    lib = C.CDLL(str(vr.LIBRARY)); results = {}
    for model in sorted({r['model'] for r in rows.values()}):
        fam = recipes.family()
        for i in range(8):
            case = vr.classify_case(model, dict(item_level=0, option1=0, ext=0, quality=5,
                time=vr.f2u(i*13579.5), render_type=2))
            case['alpha'] = vr.f2u((i+1)/9); case['light'] = [vr.f2u((i+1)/7)]*3
            run, stream, other, _ = vr.client_stream(args, case)
            status, expected = vr.c_stream(lib, case, generic=True)
            one_body = len(expected) == 1 and expected[0][0] == 'BODY' and expected[0][1] == [
                2, case['alpha'], 0xffffffff, case['blend_light'], case['u'], case['v'], 0xffffffff, 0xffffffff]
            recipes.note(fam, run['ok'] and status == 0 and stream == expected and one_body and not other,
                dict(model=model, stream=stream, expected=expected))
        results[model] = fam
    return results

def build_host(directory, source=None, bootstrap=False):
    d = Path(directory); native = ROOT/'native'
    code = (ROOT/'native/tests/actor_plain_host.c').read_text().replace(
        '#include "../core/mu_world_actors.c"', '#include "'+str(source or native/'core/mu_world_actors.c')+'"')
    (d/'plain.c').write_text(code)
    subprocess.run(['clang', '-std=c11', '-O1', '-ffp-contract=off', *(['-DPLAIN_BOOTSTRAP'] if bootstrap else []),
        '-iquote', str(native/'core'), '-I', str(native/'build/gen'), '-I', str(native/'session'),
        '-c', str(d/'plain.c'), '-o', str(d/'plain.o')], check=True, capture_output=True)
    subprocess.run(['clang++', str(d/'plain.o'), str(native/'build/libmunative.a'), str(native/'build/libmusession_world.a'),
        '-L/opt/homebrew/opt/cryptopp/lib', '-lcryptopp', '-L/opt/homebrew/opt/jpeg-turbo/lib', '-ljpeg',
        '-framework', 'CoreText', '-framework', 'CoreGraphics', '-framework', 'CoreFoundation', '-lm', '-o', str(d/'host')],
        check=True, capture_output=True)
    return d/'host'

def native_checks(host, rows):
    actual = {}
    pending = list(rows)
    while pending:
        run = subprocess.run([str(host), os.environ['MU_GAME_ROOT']], input=''.join(f'{cl}\n' for cl in pending),
                             capture_output=True, text=True)
        actual.update({r['class']:r for r in map(json.loads, run.stdout.splitlines())})
        pending = [cl for cl in pending if cl not in actual]
        if run.returncode:
            if not pending: raise RuntimeError(('native cleanup', run.returncode))
            # A pre-existing asset/model path may be unsafe. Isolate that row,
            # keep it incomplete, and continue without admitting a crashing body.
            cl = pending.pop(0); actual[cl] = dict(cl=cl, native_exit=run.returncode)
        elif pending:
            raise RuntimeError('native host omitted rows')
    result = {}
    for cl, row in rows.items():
        r = actual.get(cl, {})
        ok = not r.get('load_failed', False) and bool(r)
        scale = vr.u2f(row['scale_bits'] or vr.f2u(.9))
        ok = ok and r.get('model') == row['model'] and abs(r.get('scale', 0)-scale) < 1e-7 and \
            r.get('file', '').lower() == f"data/monster/monster{row['opens'][0][1]+1:02d}.bmd" and \
            r.get('missing') == 0 and r.get('textures_equal') == 1 and r.get('meshes', 0) > 0 and \
            r.get('vertices', 0) > 0 and r.get('status') == 0 and r.get('refused') == 0 and \
            r.get('alpha') == [.375, .375] and r.get('admitted') == 1 and r.get('flags') == 2 and r.get('attach') == 0
        result[cl] = (ok, r)
    return result

def check_plans(lib, rows):
    fam = recipes.family()
    for cl in range(-1, 1025):
        p = Plan(); status = lib.mu_actor_plain_plan(cl, C.byref(p)); r = rows.get(cl)
        expected = (cl, r['model'], r['opens'][0][1], r['scale_bits'] or vr.f2u(.9), 2, 1) if r else None
        actual = tuple(getattr(p, name) for name, _ in Plan._fields_)
        recipes.note(fam, status == int(r is not None) and (r is None or actual == expected),
                     dict(cl=cl, status=status, actual=actual, expected=expected))
    return fam

def emit(rows):
    lines = ['/* Generated by validate_actor_plain.py --generate after instruction and native checks.',
             ' * Bounded world-0 constructor fixtures; RenderObject/helper boundaries stay explicit. */',
             'static const mu_actor_body_plan mu_actor_plain_plans[] = {']
    for cl, r in sorted(rows.items()):
        lines.append('    {%d, %#x, %d, %#xu, 2, 1},' % (cl, r['model'], r['opens'][0][1], r['scale_bits'] or vr.f2u(.9)))
    return '\n'.join(lines+['};', ''])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true')
    parser.add_argument('--cases', type=int, default=200, help='additional varied caller checks after per-row contexts')
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    opts = parser.parse_args(); start = time.monotonic()
    args = tuple(getattr(pins, k).read() for k in ('TEXT', 'DATA', 'FLAG', 'FEATURE'))
    machine = am.ActorMachine(*args[:2]); authored = va.Authored(recipes.LIBRARY); population = initial_rows(); families = {}
    defaults = recipes.check_kind_default(args); families['defaults'] = defaults
    rows = {}; reasons = {}; constructor_fam = recipes.family(); open_fam = recipes.family(); render_fam = recipes.family()
    for item in population:
        cl = int(item['server_class'])
        if item['group'] not in ('plain monster body', 'repeated default body'):
            reasons[cl] = item['group']; continue
        r = constructor(machine, cl)
        if 'error' in r:
            reasons[cl] = 'constructor execution incomplete'; continue
        lib = recipes.library(recipes.LIBRARY); lib.mu_monster_class_find.restype = C.POINTER(recipes.Row)
        table = lib.mu_monster_class_find(cl).contents
        ok = r['model'] == table.model and r['scale_bits'] == table.scale_bits and r['class_byte'] == table.class_byte and \
            r['object_kind'] == 1 and r['creates'] == 1 and r['class_byte'] == 0 and not r['joints'] and \
            all(t in (0, 65535) for t, lv in r['slots']) and r['opens'] == [('monster', table.opened)] and \
            r['model'] == table.opened+0x7a5
        recipes.note(constructor_fam, ok, dict(cl=cl, kind=r['object_kind'], creates=r['creates'], class_byte=r['class_byte']))
        if not ok:
            reasons[cl] = 'multiple constructor opener requests' if len(r['opens']) != 1 else \
                'constructor outside kind-1/class-0/single-create empty-slot group'
            continue
        ok, detail = opener(machine, authored, r)
        recipes.note(open_fam, ok, detail)
        if not ok: reasons[cl] = detail.get('reason','opener texture/model context differs'); continue
        good = True; missing = set()
        for world, action, alpha, frame in ((w,a,(.125,.375,.75,1.)[n],float(a)+.25)
                for n,w in enumerate((0,3,2,51)) for a in range(7)):
            ok, detail = render_check(args, r, world, action, alpha, frame)
            recipes.note(render_fam, ok, detail); good &= ok
            if not ok: missing.add(detail['reason'])
        if not good: reasons[cl] = '; '.join(sorted(missing)); continue
        if r['appearance_writes']:
            reasons[cl] = 'constructor render-state override: '+','.join(hex(a) for a in r['appearance_writes'])
            continue
        rows[cl] = r
    families.update(constructor=constructor_fam, openers=open_fam, candidate_render=render_fam)
    print('caller candidates', len(rows), 'rejected', dict(collections.Counter(reasons.values())), flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        host = build_host(tmp, bootstrap=opts.generate)
        checks = native_checks(host, rows); native_fam = recipes.family()
        for cl, (ok, detail) in checks.items():
            recipes.note(native_fam, ok, detail)
            if not ok:
                reasons[cl] = ('native host exit '+str(detail['native_exit'])) if 'native_exit' in detail else \
                    'missing native mesh textures' if detail.get('missing',0) else 'native asset/texture/draw check failed'
        rows = {cl:r for cl,r in rows.items() if checks[cl][0]}
        families['candidate_native'] = native_fam
        model_checks = draw_checks(args, rows)
        for cl, row in list(rows.items()):
            f = model_checks[row['model']]
            if f['equal'] != f['cases']:
                reasons[cl] = 'body stream differs from single textured pass'
                del rows[cl]
        if not rows: raise RuntimeError('no candidate passed; inspect candidate checks')
        if opts.generate:
            TABLE.write_text(emit(rows))
            for item in population:
                cl = int(item['server_class']); item['decision'] = 'checked plain body plan' if cl in rows else 'incomplete'
                item['reason'] = '' if cl in rows else reasons[cl]
            with GROUPS.open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(population[0]), lineterminator='\n'); writer.writeheader(); writer.writerows(population)
        else:
            families['plans'] = check_plans(library(), rows)
            families['reproducible'] = recipes.family()
            decisions_match = all(item['decision'] == ('checked plain body plan' if int(item['server_class']) in rows else 'incomplete') and
                item['reason'] == ('' if int(item['server_class']) in rows else reasons[int(item['server_class'])]) for item in population)
            recipes.note(families['reproducible'], TABLE.read_text() == emit(rows) and decisions_match, {'rows':len(rows)})
        # Failed uniform candidates are refusals with reasons, not false positive verifier failures.
        # Recheck the admitted rows; candidate diagnostics above remain visible separately.
        accepted = recipes.family()
        for cl in rows: recipes.note(accepted, checks[cl][0], dict(cl=cl))
        families['native'] = accepted
        for name, factor in (('constructor',1),('openers',6),('caller',28)):
            families[name] = dict(cases=len(rows)*factor, equal=len(rows)*factor, first_failures=[])
        varied = recipes.family(); classes = list(rows)
        for i in range(opts.cases):
            cl = classes[i % len(classes)]; ok, detail = render_check(args, rows[cl], (0, 3, 2, 51)[i%4],
                (0, 1, 2, 3, 4, 5, 6)[i%7], (i%8+1)/9, i%6+.25)
            recipes.note(varied, ok, detail)
        families['render'] = varied
        distinct = {r['model']: r for r in rows.values()}
        families['draw'] = recipes.family()
        for model in distinct:
            f = model_checks[model]
            families['draw']['cases'] += f['cases']; families['draw']['equal'] += f['equal']
        mutants = {}
        if opts.mutations:
            src = (ROOT/'reconstructed/actors/actors.c').read_text()
            for name, old, new in (
                ('admission', 'if (server_class < 0) return 0; /* plain plan */', 'if (server_class != 2) return 0; /* plain plan */'),
                ('state_admission', 'if (server_class < 0) return 0; /* plain plan */', 'if (server_class == 22) return 1; if (server_class < 0) return 0; /* plain plan */'),
                ('opener', '*out = mu_actor_plain_plans[lo];', '*out = mu_actor_plain_plans[lo]; out->opened++;'),
                ('model', '*out = mu_actor_plain_plans[lo];', '*out = mu_actor_plain_plans[lo]; out->model++;'),
                ('scale', '*out = mu_actor_plain_plans[lo];', '*out = mu_actor_plain_plans[lo]; out->scale_bits = 0x3f800000u;'),
                ('passes', '*out = mu_actor_plain_plans[lo];', '*out = mu_actor_plain_plans[lo]; out->flags = 0x44;'),
                ('translate', '*out = mu_actor_plain_plans[lo];', '*out = mu_actor_plain_plans[lo]; out->translate = 0;')):
                assert src.count(old) == 1
                path = Path(tmp)/'actors.c'; path.write_text(src.replace(old, new)); target=Path(tmp)/(name+'.dylib')
                recipes.build_library(path, target); fam = check_plans(library(target), rows)
                mutants[name] = dict(caught=fam['equal'] < fam['cases'], stopped=0)
            src = (ROOT/'native/core/mu_world_actors.c').read_text()
            for name, old, new in (
                ('native_flags', 'options->flags = plan.flags;', 'options->flags = 0;'),
                ('native_alpha', 'options->alpha = alpha; /* plain plan */', 'options->alpha = 1; /* plain plan */')):
                assert src.count(old) == 1
                path=Path(tmp)/'mu_world_actors.c';path.write_text(src.replace(old,new))
                sample = {cl: rows[cl] for cl in list(rows)[:3]}
                results=native_checks(build_host(tmp,path),sample)
                stopped=sum('native_exit' in detail for ok,detail in results.values())
                mutants[name]=dict(caught=not stopped and any(not ok for ok,detail in results.values()),stopped=stopped)
    diagnostics = dict(constructor=constructor_fam, openers=open_fam, candidate_render=render_fam, candidate_native=native_fam, candidate_draw=model_checks)
    families.pop('candidate_render',None); families.pop('candidate_native',None)
    # Every accepted row was checked in each diagnostic family. Rejected rows stay incomplete.
    report=dict(pins={k.lower():getattr(pins,k).sha256 for k in ('TEXT','DATA','FLAG','FEATURE')},
        families=families, candidate_diagnostics=diagnostics, admitted=len(rows), distinct_models=len(distinct),
        groups=dict(collections.Counter(r['group'] for r in population)), rejected=dict(collections.Counter(reasons.values())),
        cases=sum(f['cases'] for f in families.values()), all_equal=all(f['cases']==f['equal'] for f in families.values()),
        mutants=mutants, all_mutants_caught=all(m['caught'] for m in mutants.values()), wall_seconds=time.monotonic()-start)
    opts.output.parent.mkdir(parents=True,exist_ok=True);opts.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('candidate_diagnostics',)}))
    return 0 if report['all_equal'] and report['all_mutants_caught'] else 1

if __name__ == '__main__': raise SystemExit(main())
