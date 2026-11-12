#!/usr/bin/env python3
"""RENDER-ACTORS-004: five NPC composite recipes and original part draw plans.

The original constructor and OpenNpc execute with the existing named loader
services. RenderCharacter executes from entry. RenderObject is a named base
body/pose recorder; world processors decline in the authored fixture. Part
calls and generic RenderObjDraw streams are compared, not original pixels.
"""
import argparse
import ctypes as C
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import time

import actor_census as census
import actor_machine as am
import pins
import validate_actor_recipes as recipes
import validate_actors as va
import validate_renderchar as vr

ROOT = Path(__file__).resolve().parents[1]
CLASSES = census.COMPOSITE_NPCS


def library(path=recipes.LIBRARY):
    lib = recipes.library(path)
    lib.mu_actor_npc_recipe.argtypes = [C.c_int32, C.POINTER(recipes.Row)]
    lib.mu_actor_npc_part_file.argtypes = [C.c_int32]
    lib.mu_actor_npc_part_file.restype = C.c_char_p
    return lib


def originals():
    args = (pins.TEXT.read(), pins.DATA.read(), pins.FLAG.read(), pins.FEATURE.read())
    machine = am.ActorMachine(*args[:2])
    rows = {cl: va.extract_class(machine, cl) for cl in CLASSES}
    for cl in CLASSES:
        regions, stubs, record = va.class_case(0, 0)
        create = stubs[va.CREATE_CHARACTER]
        def initialized(m):
            result = create(m)
            m.uc.mem_write(va.CLASS_CHARACTER + 0x328f, b'\1')
            return result
        stubs[va.CREATE_CHARACTER] = initialized
        run = machine.execute(va.CREATE_GENERIC, [cl, 10, 20, 1000+cl, 0], regions, stubs,
                              frame=(0x1dd4+0xc, {-0x10:0}))
        if not run['ok']: raise RuntimeError(run)
        rows[cl]['object_kind'] = run['regions']['character'][0x328f]
    return args, rows, machine


def check_recipes(lib, rows):
    fam = recipes.family()
    for cl in range(-1, 1025):
        row = recipes.Row()
        status = lib.mu_actor_npc_recipe(cl, C.byref(row))
        if cl not in CLASSES:
            recipes.note(fam, status == 0, {'class': cl, 'status': status})
            continue
        expected = rows[cl]
        recipes.note(fam, status == 1 and expected['object_kind'] == 1 and row.kind == 2 and row.model == expected['model'] and
                     row.scale_bits == expected['scale_bits'] and row.class_byte == expected['class_byte'] and
                     [[s.type, s.level] for s in row.slots] == [list(s) for s in expected['slots']], {'class': cl})
    return fam


def check_openers(lib, machine):
    fam = recipes.family()
    for index in (0x9fe, 0x9ff, 0xa00):
        row = va.extract_npc(machine, index)
        assert 'error' not in row
        for model, directory, name, number in row['extra']:
            expected = (directory + name + ('' if number == -1 else f'{number:02d}') + '.bmd').replace('\\', '/')
            actual = lib.mu_actor_npc_part_file(model)
            recipes.note(fam, actual is not None and actual.decode() == expected,
                         {'model': model, 'expected': expected, 'actual': actual.decode() if actual else None})
    for model in (-1, 0, 0xa0c, 0xa13, 0xa14, 0xa25, 65535):
        recipes.note(fam, lib.mu_actor_npc_part_file(model) is None, {'model': model})
    return fam


def check_render(lib, args, rows, count):
    fam = recipes.family(); rng = random.Random(20261111)
    original_world, original_record = vr.World, vr.character_record
    try:
        for i in range(count):
            cl = CLASSES[i % 5]; row = rows[cl]; world_id = (0, 3, 2, 51)[i // 5 % 4]
            def world(*args):
                w = original_world(*args); m = w.m
                m.ensure(0x01cf15fc, 4); m.w32(0x01cf15fc, world_id)
                m.stub(0x009dc2f0, lambda m: 0, 0)
                # Four stateful map services from the existing constructor
                # model are explicit declining fixtures, not recovered state.
                m.ensure(0x2f000000, 0x200)
                m.w32(0x2f000000, 0x2f000100); m.w32(0x2f000154, 0x00401000)
                m.stub(0x00401000, lambda m: 0, 12)
                m.stub(0x00db747f, lambda m: 0x2f000000, 0)
                m.stub(0x00a9c672, lambda m: 0, 12); m.stub(0x00ea3cae, lambda m: 0, 12)
                m.stub(0x016d4fe4, lambda m: w.calls.append(('base-body', m.arg(0))) or 0, 0)
                w.add_model(row['model'], vr.MODEL + 0x4000, bones=60, meshes=0, actions=16,
                            actions_at=vr.ACTIONS)
                return w
            def record(**kw):
                raw = original_record(**kw)
                struct.pack_into('<I', raw, 0x32b0, row['model'])
                struct.pack_into('<h', raw, 0x146, cl)
                raw[0x328f] = row['object_kind']
                return raw
            vr.World, vr.character_record = world, record
            slots = [None if t in (0, 65535) else dict(type=t, level=lv, option=0, ext=0, kind=0,
                        action=0, frame=0, prior=0, speed=0) for t, lv in row['slots']]
            alpha = vr.f2u(rng.uniform(.01, 1))
            ch = {'class':0, 'action':(0, 1, 2)[i // 20 % 3], 'safe':0, 'frame':vr.f2u(rng.uniform(0, 6)),
                  'alpha':alpha, 'select':0, 'speeds':[vr.f2u(.25)] * 390, 'slots':slots}
            run, calls, w = vr.character_client(args, ch)
            native = recipes.Row(); lib.mu_actor_npc_recipe(cl, C.byref(native))
            expected = [('PART', k, native.slots[k].type, 0, 0, 0, 1, 0, 2)
                        for k in range(5, -1, -1) if native.slots[k].type not in (0, 65535)]
            rpo = [c for c in w.calls if c[0] == 'RPO']
            recipes.note(fam, run['ok'] and [c for c in calls if c[0] == 'PART'] == expected and all(c[1][4] == alpha for c in rpo),
                         {'class':cl, 'world':world_id, 'actual':calls, 'expected':expected,
                          'run':None if run['ok'] else run})
    finally:
        vr.World, vr.character_record = original_world, original_record
    return fam


def check_draw(args, rows):
    fam = recipes.family(); lib = C.CDLL(str(vr.LIBRARY))
    types = sorted({t for r in rows.values() for t, _ in r['slots'] if t not in (0, 65535)})
    for t in types:
        for i in range(8):
            case = vr.classify_case(t, dict(item_level=0, option1=0, ext=0, quality=5,
                         time=vr.f2u(i * 13579.5), render_type=2))
            case['alpha'] = vr.f2u((i+1) / 9)
            case['light'] = [vr.f2u((i+1) / 7)] * 3
            run, stream, _, _ = vr.client_stream(args, case)
            status, expected = vr.c_stream(lib, case, generic=True)
            recipes.note(fam, run['ok'] and status == 0 and stream == expected,
                         {'model':t, 'stream':stream, 'expected':expected})
    return fam


def build_host(directory, source=None):
    # Reuse the established host linker, but supply this lane's own host.
    directory = Path(directory)
    code = (ROOT/'native/tests/actor_composite_host.c').read_text().replace(
        '#include "../core/mu_world_actors.c"', '#include "' + str(source or ROOT/'native/core/mu_world_actors.c') + '"')
    (directory/'composite.c').write_text(code)
    native = ROOT/'native'
    cmd = ['clang', '-std=c11', '-O1', '-ffp-contract=off', '-iquote', str(native/'core'),
           '-I', str(native/'build/gen'), '-I', str(native/'session'), '-c', str(directory/'composite.c'),
           '-o', str(directory/'composite.o')]
    subprocess.run(cmd, check=True, capture_output=True)
    subprocess.run(['clang++', str(directory/'composite.o'), str(native/'build/libmunative.a'),
                    str(native/'build/libmusession_world.a'), '-L/opt/homebrew/opt/cryptopp/lib', '-lcryptopp',
                    '-L/opt/homebrew/opt/jpeg-turbo/lib', '-ljpeg', '-framework', 'CoreText',
                    '-framework', 'CoreGraphics', '-framework', 'CoreFoundation', '-lm', '-o', str(directory/'host')],
                   check=True, capture_output=True)
    return directory/'host'


def check_native(host, root, rows):
    fam = recipes.family(); lib = library()
    for cl in CLASSES:
        for world_id in (0, 3):
            run = subprocess.run([str(host), root, str(cl), str(world_id)], capture_output=True, text=True)
            if run.returncode:
                recipes.note(fam, False, {'class':cl, 'exit':run.returncode, 'error':run.stderr}); continue
            value = json.loads(run.stdout); expected = rows[cl]
            ok = value['base_model'] == expected['model'] and value['base_meshes'] == 0 and value['height'] > 1 and \
                 abs(value['scale'] - .9) < 1e-7 and value['initial'] == 0 and value['frame'] > 0 and value['frame'] == value['actor_frame'] and \
                 value['alpha'] == [.375, .375] and value['refused'] == [1, 1]
            for slot, loaded, model, missing, vertices, file in value['slots']:
                t = expected['slots'][slot][0]
                ok &= bool(loaded) == (t not in (0, 65535))
                if loaded:
                    ok &= model == t and missing == 0 and vertices > 0 and file == lib.mu_actor_npc_part_file(t).decode()
            recipes.note(fam, ok, value)
    return fam


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=240)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    opts = parser.parse_args(); start = time.monotonic()
    args, rows, machine = originals(); lib = library()
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        host = build_host(directory)
        families = dict(kind_default=recipes.check_kind_default(args), recipes=check_recipes(lib, rows), openers=check_openers(lib, machine),
                        render=check_render(lib, args, rows, opts.cases), draw=check_draw(args, rows),
                        native=check_native(host, os.environ['MU_GAME_ROOT'], rows))
        mutants = {}
        if opts.mutations:
            source = (ROOT/'reconstructed/actors/actors.c').read_text()
            for name, old, new in (
                ('npc_admission', 'case 230: case 248: case 250: case 253: case 255: break;', 'case 250: break;'),
                ('npc_kind', 'row->kind != MU_CLASS_NPC', 'row->kind != MU_CLASS_PLAYER_MODEL'),
                ('npc_file', 'Data/Npc/ManHead01.bmd', 'Data/Npc/ManHead02.bmd')):
                assert source.count(old) == 1
                path = directory/'actors.c'; path.write_text(source.replace(old, new))
                changed = library(build_library(path, directory/(name+'.dylib')))
                checks = [check_recipes(changed, rows), check_openers(changed, machine)]
                mutants[name] = {'caught':any(f['equal'] < f['cases'] for f in checks), 'stopped':0}
            source = (ROOT/'native/core/mu_world_actors.c').read_text()
            for name, old, new in (
                ('npc_load', '!player && load_npc_parts', 'player && load_npc_parts'),
                ('npc_scale', 'a->player->params.scale = a->actor.spec.scale;', 'a->player->params.scale = 1.0f;'),
                ('npc_slot', 'for (int k = 1; k < MU_CHARACTER_PART_SLOTS; ++k)', 'for (int k = 2; k < MU_CHARACTER_PART_SLOTS; ++k)'),
                ('npc_tick', 'if (a->player && !mu_actor_npc_recipe(a->server_class, NULL))', 'if (a->player)'),
                ('npc_frame', 'mu_actor_frame(&a->actor),', '0.0f,'),
                ('npc_alpha', 'options.alpha = alpha;', 'options.alpha = 1.0f;'),
                ('npc_draw', 'return mu_scene_draw_model(&part->model, &options, backend, stats);', 'return 0;')):
                assert source.count(old) == 1, (name, source.count(old))
                path = directory/'mu_world_actors.c'; path.write_text(source.replace(old, new))
                checks = check_native(build_host(directory, path), os.environ['MU_GAME_ROOT'], rows)
                mutants[name] = {'caught':checks['equal'] < checks['cases'], 'stopped':0}
    report = dict(pins=dict(text=pins.TEXT.sha256, data=pins.DATA.sha256, flag=pins.FLAG.sha256, feature=pins.FEATURE.sha256),
                  families=families, cases=sum(f['cases'] for f in families.values()),
                  all_equal=all(f['equal'] == f['cases'] for f in families.values()), mutants=mutants,
                  all_mutants_caught=all(m['caught'] for m in mutants.values()), wall_seconds=time.monotonic()-start)
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(report, indent=2)+'\n'); print(json.dumps(report))
    return 0 if report['all_equal'] and report['all_mutants_caught'] else 1


def build_library(source, path):
    recipes.build_library(source, path)
    return path


if __name__ == '__main__':
    raise SystemExit(main())
